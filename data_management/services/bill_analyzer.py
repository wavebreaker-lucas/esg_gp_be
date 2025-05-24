import os
import json
import logging
import requests
import re
import time
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from data_management.models import ESGMetricEvidence, BaseESGMetric
from typing import Callable, Dict, Any, List
from tempfile import NamedTemporaryFile
from copy import deepcopy

logger = logging.getLogger(__name__)

class UtilityBillAnalyzer:
    """
    A service to analyze utility bills using Azure Content Understanding API.
    Uses custom analyzers for different metrics to extract consumption data.
    """
    
    def __init__(self, endpoint=None, api_version=None, subscription_key=None):
        """
        Initialize with Azure Content Understanding API credentials.
        
        Args:
            endpoint: Azure Content Understanding API endpoint URL
            api_version: API version to use
            subscription_key: Subscription key for the API
        """
        # Use provided values or fall back to settings
        self.endpoint = endpoint or settings.AZURE_CONTENT_UNDERSTANDING.get('ENDPOINT')
        self.api_version = api_version or settings.AZURE_CONTENT_UNDERSTANDING.get('API_VERSION')
        self.subscription_key = subscription_key or settings.AZURE_CONTENT_UNDERSTANDING.get('KEY')
        self.default_analyzer_id = "multi-period-analyzer"  # Default analyzer ID matching settings
        
        if not all([self.endpoint, self.api_version, self.subscription_key]):
            logger.warning("Azure Content Understanding API credentials not fully configured")
        
    def test_process_evidence(self, evidence):
        """
        Test OCR processing on an evidence file without saving results to the database.
        This is useful for development and testing purposes.
        
        Args:
            evidence: An ESGMetricEvidence object to process
            
        Returns:
            tuple: (success: bool, result: dict) where success indicates if OCR processing succeeded
                  and result contains either the extracted data or an error message
        """
        # Create a copy of the evidence object to prevent modifying the original
        evidence_copy = deepcopy(evidence)
        
        # Override the save method to prevent database writes
        original_save = evidence_copy.save
        evidence_copy.save = lambda *args, **kwargs: None
        
        try:
            # Run the regular process_evidence method with our no-op save
            return self.process_evidence(evidence_copy)
        finally:
            # Restore the original save method
            evidence_copy.save = original_save
        
    def process_evidence(self, evidence):
        """
        Process an evidence file with OCR and extract relevant utility data.
        
        Args:
            evidence: An ESGMetricEvidence object to process
            
        Returns:
            tuple: (success: bool, result: dict) where success indicates if OCR processing succeeded
                  and result contains either the extracted data or an error message
        """
        try:
            # Prepare file for processing - handle both local files and Azure Blob Storage
            temp_file = None
            file_path = None
            
            try:
                # Always use a temporary file for compatibility with all storage backends
                with evidence.file.open('rb') as fsrc:
                    temp_file = NamedTemporaryFile(delete=False, suffix=os.path.splitext(evidence.filename)[1])
                    temp_file.write(fsrc.read())
                    temp_file.close()
                    file_path = temp_file.name
                    logger.info(f"Downloaded file to temporary file: {file_path}")
                
                # Determine analyzer ID
                analyzer_id = self.default_analyzer_id
                
                # Check evidence.intended_metric instead of submission.metric
                if evidence.intended_metric and evidence.intended_metric.ocr_analyzer_id:
                    analyzer_id = evidence.intended_metric.ocr_analyzer_id
                    logger.info(f"Using metric-specific analyzer: {analyzer_id}")
                elif evidence.intended_metric_id:
                    try:
                        metric = BaseESGMetric.objects.get(id=evidence.intended_metric_id)
                        if metric.ocr_analyzer_id:
                            analyzer_id = metric.ocr_analyzer_id
                            logger.info(f"Using standalone intended metric analyzer: {analyzer_id}")
                    except BaseESGMetric.DoesNotExist:
                        logger.warning(f"Intended metric {evidence.intended_metric_id} not found, using default analyzer")
                
                # Create Azure Content Understanding client
                client = AzureContentUnderstandingClient(
                    self.endpoint,
                    self.api_version,
                    subscription_key=self.subscription_key
                )
                
                # Begin analysis with the appropriate analyzer
                try:
                    metric_name = evidence.intended_metric.name if evidence.intended_metric else "standalone file"
                    logger.info(f"Using analyzer ID: {analyzer_id} for: {metric_name}")
                    response = client.begin_analyze(analyzer_id, file_path)
                    logger.info(f"Analysis started for evidence {evidence.id}, operation URL: {response.headers.get('operation-location')}")
                    
                    # Poll until completion
                    result = client.poll_result(
                        response,
                        timeout_seconds=60 * 5,  # 5 minute timeout
                        polling_interval_seconds=2,
                    )
                except Exception as e:
                    logger.exception(f"Error during OCR processing: {str(e)}")
                    evidence.is_processed_by_ocr = True  # Mark as processed even if failed
                    evidence.save(update_fields=['is_processed_by_ocr'])  # FIXED: Only update this field
                    return False, {
                        "error": f"OCR processing failed: {str(e)}"
                    }
                
                if result.get("status") != "Succeeded" or "result" not in result:
                    evidence.is_processed_by_ocr = True
                    evidence.ocr_data = result  # Store the raw result anyway
                    evidence.save(update_fields=['is_processed_by_ocr', 'ocr_data'])  # FIXED: Only update these fields
                    return False, {
                        "error": "OCR processing did not succeed"
                    }
                
                # Extract data from result
                try:
                    fields = result["result"]["contents"][0]["fields"]
                    
                    # Store the complete OCR data, but preserve any existing metadata
                    existing_metadata = evidence.ocr_data or {}
                    if isinstance(existing_metadata, dict) and 'intended_metric_id' in existing_metadata:
                        # Keep the intended_metric_id in the result
                        result['intended_metric_id'] = existing_metadata['intended_metric_id']
                    
                    evidence.ocr_data = result
                    evidence.is_processed_by_ocr = True
                    
                    # Extract consumption data - simplified now that we use custom analyzers
                    extracted_data = self._extract_data_from_analyzer(fields)
                    
                    if not extracted_data:
                        evidence.save(update_fields=['is_processed_by_ocr', 'ocr_data'])  # FIXED: Only update these fields
                        return False, {
                            "error": "Could not extract relevant data from document"
                        }
                    
                    # Track fields to update
                    fields_to_update = ['is_processed_by_ocr', 'ocr_data']  # FIXED: track fields to update
                    
                    # Update the evidence record with extracted data
                    # For simplicity, we'll use the first period if multiple periods were found
                    if "periods" in extracted_data and extracted_data["periods"]:
                        # Store all periods in ocr_data for reference
                        evidence.ocr_data['additional_periods'] = []
                        
                        # Sort periods by date, most recent first
                        periods = sorted(
                            extracted_data["periods"],
                            key=lambda p: p.get("period") or datetime.min,
                            reverse=True
                        )
                        
                        # Use the most recent period as the primary
                        first_period = periods[0]
                        evidence.extracted_value = first_period.get("consumption")
                        fields_to_update.append('extracted_value')  # FIXED: track field
                        
                        evidence.ocr_period = first_period.get("period")  # Store OCR period in new field
                        fields_to_update.append('ocr_period')  # FIXED: track field
                        
                        # Store all other periods in additional_periods
                        if len(periods) > 1:
                            # Format additional periods for storage
                            for period in periods[1:]:
                                # Format the date as MM/YYYY if it's a datetime object
                                if isinstance(period.get("period"), datetime):
                                    period_date = period["period"].strftime("%m/%Y")
                                else:
                                    # Use the original period_str which should already be in MM/YYYY format
                                    period_date = period.get("period_str", "")
                                
                                evidence.ocr_data['additional_periods'].append({
                                    "period": period_date,
                                    "consumption": period.get("consumption")
                                })
                            # ocr_data is already in fields_to_update
                    else:
                        # Use single period data if available
                        evidence.extracted_value = extracted_data.get("value")
                        fields_to_update.append('extracted_value')  # FIXED: track field
                        
                        evidence.ocr_period = extracted_data.get("period")  # Store OCR period in new field
                        fields_to_update.append('ocr_period')  # FIXED: track field
                    
                    evidence.save(update_fields=fields_to_update)  # FIXED: Only update the tracked fields
                    
                    # Return success with additional periods if available
                    additional_periods = evidence.ocr_data.get('additional_periods', [])
                    
                    return True, {
                        "extracted_value": evidence.extracted_value,
                        "period": evidence.ocr_period,
                        "additional_periods": additional_periods
                    }
                    
                except Exception as e:
                    logger.exception(f"Error extracting data from OCR result: {str(e)}")
                    evidence.is_processed_by_ocr = True
                    evidence.ocr_data = result
                    evidence.save(update_fields=['is_processed_by_ocr', 'ocr_data'])  # FIXED: Only update these fields
                    return False, {
                        "error": f"Error extracting data from OCR result: {str(e)}"
                    }
            finally:
                # Clean up temporary file if we created one
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                        logger.info(f"Deleted temporary file: {temp_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary file {temp_file.name}: {str(e)}")
            
        except Exception as e:
            logger.exception(f"Error processing evidence {evidence.id}: {str(e)}")
            return False, {
                "error": f"Error processing evidence: {str(e)}"
            }
    
    def _extract_data_from_analyzer(self, fields):
        """
        Extract relevant data from the Content Understanding API fields.
        This is a simplified version that works with any analyzer output.
        
        Args:
            fields: Fields from Content Understanding API result
            
        Returns:
            dict: Extracted data including value and period(s)
        """
        result = {
            'periods': []
        }
        
        # Try standard field names first
        # Look for consumption values in various formats
        for consumption_field in ["Consumption", "ElectricityConsumption", "WaterConsumption", "GasConsumption", "FuelAmount", "FuelConsumption"]:
            if consumption_field in fields and "valueNumber" in fields[consumption_field]:
                result['value'] = float(fields[consumption_field]["valueNumber"])
                break
        
        # Look for billing period in various formats
        for period_field in ["BillingPeriod", "Period", "BillingDate"]:
            if period_field in fields and "valueString" in fields[period_field]:
                period_str = fields[period_field]["valueString"]
                result['period_str'] = period_str
                # Try to convert to date
                try:
                    result['period'] = self._parse_date(period_str)
                except ValueError:
                    pass
                break
                    
        # Try to extract multiple billing periods
        if "MultipleBillingPeriods" in fields and "valueString" in fields["MultipleBillingPeriods"]:
            multiple_periods_str = fields["MultipleBillingPeriods"]["valueString"]
            
            # Try to parse as JSON
            try:
                multiple_periods = json.loads(multiple_periods_str)
                if isinstance(multiple_periods, list) and multiple_periods:
                    standardized_data = []
                    for period in multiple_periods:
                        if isinstance(period, dict):
                            # Try different key names for period and consumption
                            period_value = None
                            for key in ["period", "請表日期", "billingPeriod", "date"]:
                                if key in period:
                                    period_value = period[key]
                                    break
                            
                            if not period_value:
                                continue
                            
                            # Convert to MM/YYYY format
                            formatted_period = self._convert_to_month_year_format(period_value)
                            
                            # Try different key names for consumption
                            consumption_value = None
                            for key in ["consumption", "用電度數", "value", "amount"]:
                                if key in period:
                                    consumption_value = self._parse_consumption(period[key])
                                    break
                            
                            if consumption_value is None:
                                continue
                            
                            # Convert period string to date object 
                            period_date = None
                            try:
                                period_date = self._mm_yyyy_to_date(formatted_period)
                            except ValueError:
                                # If we can't parse the date, skip this period
                                continue
                            
                            # Create standardized period object
                            standardized_period = {
                                "period_str": formatted_period,
                                "period": period_date,
                                "consumption": consumption_value
                            }
                            
                            standardized_data.append(standardized_period)
                    
                    if standardized_data:
                        result['periods'] = standardized_data
            except json.JSONDecodeError:
                logger.warning(f"Could not parse multiple billing periods as JSON: {multiple_periods_str}")
                # Try to handle the case where the JSON is a string containing an array
                try:
                    # Use regex to find what looks like a JSON array in the string
                    json_match = re.search(r'\[.*\]', multiple_periods_str)
                    if json_match:
                        potential_json = json_match.group(0)
                        multiple_periods = json.loads(potential_json)
                        
                        if isinstance(multiple_periods, list) and multiple_periods:
                            standardized_data = []
                            for period in multiple_periods:
                                if isinstance(period, dict):
                                    period_value = period.get('period')
                                    consumption_value = period.get('consumption')
                                    
                                    if not period_value or consumption_value is None:
                                        continue
                                    
                                    # Format the period string
                                    formatted_period = self._convert_to_month_year_format(period_value)
                                    
                                    # Parse consumption value if it's a string
                                    if isinstance(consumption_value, str):
                                        consumption_value = self._parse_consumption(consumption_value)
                                    
                                    # Convert period string to date object
                                    try:
                                        period_date = self._mm_yyyy_to_date(formatted_period)
                                    except ValueError:
                                        continue
                                    
                                    standardized_period = {
                                        "period_str": formatted_period,
                                        "period": period_date,
                                        "consumption": consumption_value
                                    }
                                    
                                    standardized_data.append(standardized_period)
                            
                            if standardized_data:
                                result['periods'] = standardized_data
                except Exception as e:
                    logger.warning(f"Failed to parse multiple periods from JSON string: {str(e)}")
        
        return result if 'value' in result or result['periods'] else None
    
    def _parse_date(self, date_str):
        """
        Parse a date string into a datetime.date object
        
        Args:
            date_str: A string representation of a date
            
        Returns:
            datetime.date: The parsed date
        """
        from dateutil.parser import parse
        try:
            return parse(date_str).date()
        except ValueError:
            # If standard parsing fails, try to use our custom format parser
            formatted = self._convert_to_month_year_format(date_str)
            if formatted and "/" in formatted:
                try:
                    return self._mm_yyyy_to_date(formatted)
                except ValueError:
                    pass
            
            # If all else fails, raise
            raise ValueError(f"Could not parse date string: {date_str}")
    
    def _convert_to_month_year_format(self, date_str):
        """Convert various date formats to MM/YYYY format"""
        # Try common date formats
        date_formats = [
            # DD/MM/YYYY format
            r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})',
            # YYYY/MM/DD format
            r'(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})',
            # MM/YYYY format (already in desired format)
            r'(\d{1,2})[/\-.](\d{4})',
            # Text month formats like "Jan 2023" or "January 2023"
            r'([a-zA-Z]{3,9})\s+(\d{4})'
        ]
        
        # If it's already in MM/YYYY format, return as is
        if re.match(r'^\d{1,2}/\d{4}$', date_str):
            return date_str
        
        # Try matching against patterns
        for pattern in date_formats:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()
                
                # DD/MM/YYYY format
                if len(groups) == 3 and len(groups[2]) >= 4:
                    month, year = groups[1], groups[2]
                    return f"{month.zfill(2)}/{year}"
                
                # YYYY/MM/DD format
                elif len(groups) == 3 and len(groups[0]) == 4:
                    year, month = groups[0], groups[1]
                    return f"{month.zfill(2)}/{year}"
                
                # MM/YYYY format
                elif len(groups) == 2 and len(groups[1]) == 4:
                    month, year = groups[0], groups[1]
                    return f"{month.zfill(2)}/{year}"
                
                # Text month like "Jan 2023"
                elif len(groups) == 2 and groups[0].isalpha():
                    month_name, year = groups[0], groups[1]
                    month_names = {
                        "jan": "01", "feb": "02", "mar": "03", "apr": "04", 
                        "may": "05", "jun": "06", "jul": "07", "aug": "08",
                        "sep": "09", "oct": "10", "nov": "11", "dec": "12"
                    }
                    month_abbr = month_name.lower()[:3]
                    if month_abbr in month_names:
                        return f"{month_names[month_abbr]}/{year}"
        
        # If all else fails, return the original string
        return date_str
    
    def _parse_consumption(self, consumption_str):
        """Convert various consumption string formats to a numeric value"""
        if isinstance(consumption_str, (int, float)):
            return consumption_str
        
        # Remove thousand separators and other non-numeric characters except decimal point
        if isinstance(consumption_str, str):
            # Remove commas, spaces, and other separators
            numeric_str = consumption_str.replace(',', '').replace(' ', '')
            
            # Try to extract just the numeric part if there are other characters
            numeric_match = re.search(r'[-+]?\d*\.?\d+', numeric_str)
            if numeric_match:
                numeric_str = numeric_match.group(0)
                
            try:
                return float(numeric_str)
            except ValueError:
                pass
                
        return 0  # Default if parsing fails

    def _mm_yyyy_to_date(self, period_str):
        """
        Convert a MM/YYYY formatted string to a date object representing the last day of that month.
        
        Args:
            period_str: String in MM/YYYY format (e.g. "01/2023")
            
        Returns:
            datetime.date: Date object for the last day of the month
            
        Raises:
            ValueError: If the string cannot be parsed
        """
        if period_str and "/" in period_str:
            try:
                month, year = period_str.split("/")
                # Create date for last day of the month
                import calendar
                last_day = calendar.monthrange(int(year), int(month))[1]
                return datetime(int(year), int(month), last_day).date()
            except (ValueError, IndexError):
                raise ValueError(f"Could not parse MM/YYYY string: {period_str}")
        else:
            raise ValueError(f"String not in MM/YYYY format: {period_str}")


class AzureContentUnderstandingClient:
    """
    Client for interacting with Azure Content Understanding API.
    """
    
    def __init__(
        self,
        endpoint: str,
        api_version: str,
        subscription_key: str | None = None,
        token_provider: Callable[[], str] | None = None,
        x_ms_useragent: str = "esg-platform",
    ) -> None:
        if not subscription_key and token_provider is None:
            raise ValueError(
                "Either subscription key or token provider must be provided"
            )
        if not api_version:
            raise ValueError("API version must be provided")
        if not endpoint:
            raise ValueError("Endpoint must be provided")

        self._endpoint: str = endpoint.rstrip("/")
        self._api_version: str = api_version
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.INFO)
        self._headers: dict[str, str] = self._get_headers(
            subscription_key, token_provider and token_provider(), x_ms_useragent
        )

    def begin_analyze(self, analyzer_id: str, file_location: str):
        """
        Begins the analysis of a file or URL using the specified analyzer.

        Args:
            analyzer_id (str): The ID of the analyzer to use.
            file_location (str): The path to the file or the URL to analyze.

        Returns:
            Response: The response from the analysis request.

        Raises:
            ValueError: If the file location is not a valid path or URL.
            HTTPError: If the HTTP request returned an unsuccessful status code.
        """
        import os
        from pathlib import Path
        
        if Path(file_location).exists():
            with open(file_location, "rb") as file:
                data = file.read()
            headers = {"Content-Type": "application/octet-stream"}
        elif "https://" in file_location or "http://" in file_location:
            data = {"url": file_location}
            headers = {"Content-Type": "application/json"}
        else:
            raise ValueError("File location must be a valid path or URL.")

        headers.update(self._headers)
        url = self._get_analyze_url(self._endpoint, self._api_version, analyzer_id)
        
        self._logger.info(f"Analyzing file {file_location} with analyzer: {analyzer_id}")
        self._logger.info(f"POST request to: {url}")
        
        if isinstance(data, dict):
            response = requests.post(
                url=url,
                headers=headers,
                json=data,
            )
        else:
            response = requests.post(
                url=url,
                headers=headers,
                data=data,
            )

        response.raise_for_status()
        return response

    def poll_result(
        self,
        response: requests.Response,
        timeout_seconds: int = 120,
        polling_interval_seconds: int = 2,
    ) -> dict[str, Any]:
        """
        Polls the result of an asynchronous operation until it completes or times out.
        """
        operation_location = response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError("Operation location not found in response headers.")

        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            self._logger.info(
                f"Waiting for service response (elapsed: {elapsed_time:.2f}s)"
            )
            if elapsed_time > timeout_seconds:
                raise TimeoutError(
                    f"Operation timed out after {timeout_seconds:.2f} seconds."
                )

            response = requests.get(operation_location, headers=self._headers)
            response.raise_for_status()
            result = response.json()
            status = result.get("status", "").lower()
            if status == "succeeded":
                self._logger.info(
                    f"Analysis completed after {elapsed_time:.2f} seconds."
                )
                return result
            elif status == "failed":
                self._logger.error(f"Analysis failed. Reason: {response.json()}")
                raise RuntimeError(f"Analysis failed: {result}")
            else:
                self._logger.info(
                    f"Analysis in progress... (elapsed: {elapsed_time:.2f}s)"
                )
            time.sleep(polling_interval_seconds)

    def _get_analyze_url(self, endpoint: str, api_version: str, analyzer_id: str):
        return f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={api_version}"

    def _get_headers(
        self, subscription_key: str | None, api_token: str | None, x_ms_useragent: str
    ) -> dict[str, str]:
        """Returns the headers for the HTTP requests."""
        headers = (
            {"Ocp-Apim-Subscription-Key": subscription_key}
            if subscription_key
            else {"Authorization": f"Bearer {api_token}"}
        )
        headers["x-ms-useragent"] = x_ms_useragent
        return headers
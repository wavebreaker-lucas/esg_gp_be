import csv
from django.http import HttpResponse
import pytz
from rest_framework.response import Response
from rest_framework import status

class CSVExportMixin:
    """Mixin for CSV export functionality"""
    
    def get_csv_response(self, filename):
        """Returns a configured HttpResponse for CSV download"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response

    def format_datetime_hkt(self, datetime_obj):
        """Formats datetime to HKT timezone"""
        hkt_tz = pytz.timezone('Asia/Hong_Kong')
        return datetime_obj.astimezone(hkt_tz).strftime('%Y-%m-%d %H:%M') + "HKT"

class ErrorHandlingMixin:
    """Mixin for common error handling patterns"""

    def handle_validation_error(self, error):
        return Response(
            {"error": str(error)},
            status=status.HTTP_400_BAD_REQUEST
        )

    def handle_permission_error(self, error):
        return Response(
            {"error": str(error)},
            status=status.HTTP_403_FORBIDDEN
        )

    def handle_not_found_error(self, error):
        return Response(
            {"error": str(error)},
            status=status.HTTP_404_NOT_FOUND
        )

    def handle_unknown_error(self, error):
        return Response(
            {"error": f"An unexpected error occurred: {str(error)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 
import json
from django.core.management.base import BaseCommand, CommandError
from data_management.models import ESGMetricEvidence
from data_management.services.bill_analyzer import UtilityBillAnalyzer

class Command(BaseCommand):
    help = 'Test OCR processing on an evidence file without saving results to the database'

    def add_arguments(self, parser):
        parser.add_argument('evidence_id', type=int, help='ID of the evidence to process')
        parser.add_argument('--save', action='store_true', help='Save results to database')
        parser.add_argument('--format', choices=['pretty', 'json'], default='pretty', help='Output format')

    def handle(self, *args, **options):
        evidence_id = options['evidence_id']
        save_results = options['save']
        output_format = options['format']
        
        try:
            evidence = ESGMetricEvidence.objects.get(id=evidence_id)
        except ESGMetricEvidence.DoesNotExist:
            raise CommandError(f'Evidence with ID {evidence_id} does not exist')
        
        # If evidence doesn't have OCR enabled, enable it temporarily
        was_ocr_enabled = evidence.enable_ocr_processing
        if not was_ocr_enabled:
            self.stdout.write(self.style.WARNING('OCR processing is not enabled for this evidence. Enabling temporarily.'))
            evidence.enable_ocr_processing = True
        
        # Create the analyzer
        analyzer = UtilityBillAnalyzer()
        
        # Process the evidence
        if save_results:
            self.stdout.write(self.style.WARNING('Saving results to database'))
            success, result = analyzer.process_evidence(evidence)
        else:
            self.stdout.write(self.style.WARNING('Testing OCR processing without saving to database'))
            success, result = analyzer.test_process_evidence(evidence)
        
        # Reset the OCR flag if we temporarily enabled it
        if not was_ocr_enabled and not save_results:
            evidence.enable_ocr_processing = False
            
        # Output the results
        if success:
            self.stdout.write(self.style.SUCCESS('OCR processing successful'))
            
            if output_format == 'json':
                self.stdout.write(json.dumps(result, indent=2, default=str))
            else:
                self.stdout.write(f"Extracted Value: {result.get('extracted_value')}")
                self.stdout.write(f"Period: {result.get('period')}")
                
                if 'additional_periods' in result and result['additional_periods']:
                    self.stdout.write("\nAdditional Periods:")
                    for period in result['additional_periods']:
                        self.stdout.write(f"  - Period: {period.get('period')}, Consumption: {period.get('consumption')}")
        else:
            self.stdout.write(self.style.ERROR('OCR processing failed'))
            self.stdout.write(self.style.ERROR(f"Error: {result.get('error')}")) 
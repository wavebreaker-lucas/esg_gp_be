"""
Views for batch submission management
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone

from accounts.models import LayerProfile
from ..models import (
    ESGMetricBatchSubmission, ESGMetricSubmission, ESGMetric,
    TemplateAssignment
)
from ..serializers.esg import (
    BatchSubmissionModelSerializer, ESGMetricSubmissionSerializer,
    ESGMetricBatchSubmissionSerializer
)


class BatchSubmissionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing batch submissions"""
    serializer_class = BatchSubmissionModelSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter batch submissions based on user permissions"""
        queryset = ESGMetricBatchSubmission.objects.all()
        
        # Staff and superusers can see all batches
        user = self.request.user
        if user.is_staff or user.is_superuser or user.is_baker_tilly_admin:
            return queryset
        
        # Other users can only see batches for their layers
        user_layers = LayerProfile.objects.filter(app_users__user=user)
        return queryset.filter(
            layer__in=user_layers
        )
    
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Get all submissions in this batch"""
        batch = self.get_object()
        submissions = batch.submissions.all()
        serializer = ESGMetricSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def submit_batch(self, request):
        """Create a new batch submission with multiple metrics"""
        serializer = ESGMetricBatchSubmissionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get validated data
        validated_data = serializer.validated_data
        assignment_id = validated_data['assignment_id']
        submissions_data = validated_data['submissions']
        name = validated_data.get('name', '')
        notes = validated_data.get('notes', '')
        layer_id = validated_data.get('layer_id')
        
        # Get objects from database
        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id)
            layer = None
            if layer_id:
                layer = LayerProfile.objects.get(id=layer_id)
        except (TemplateAssignment.DoesNotExist, LayerProfile.DoesNotExist) as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        # Create the batch submission
        batch = ESGMetricBatchSubmission.objects.create(
            assignment=assignment,
            name=name,
            notes=notes,
            submitted_by=request.user,
            layer=layer
        )
        
        # Process each submission
        submission_results = []
        
        for sub_data in submissions_data:
            metric_id = sub_data['metric_id']
            
            # Handle updates if an existing submission was found
            if 'update_id' in sub_data:
                try:
                    submission = ESGMetricSubmission.objects.get(id=sub_data['update_id'])
                    
                    # Update fields
                    if 'data' in sub_data:
                        submission.data = sub_data['data']
                    if 'value' in sub_data:
                        submission.value = sub_data['value']
                    if 'text_value' in sub_data:
                        submission.text_value = sub_data['text_value']
                    if 'notes' in sub_data:
                        submission.notes = sub_data['notes']
                    
                    # Link to the batch
                    submission.batch_submission = batch
                    submission.save()
                    
                except ESGMetricSubmission.DoesNotExist:
                    # If submission no longer exists, create a new one
                    sub_data.pop('update_id')
                    submission = self._create_submission(
                        request, assignment, metric_id, sub_data, batch, layer
                    )
            else:
                # Create a new submission
                submission = self._create_submission(
                    request, assignment, metric_id, sub_data, batch, layer
                )
            
            submission_results.append({
                'id': submission.id,
                'metric_id': submission.metric_id,
                'status': 'updated' if 'update_id' in sub_data else 'created'
            })
        
        # Update assignment status
        if assignment.status in ['PENDING', 'IN_PROGRESS']:
            assignment.status = 'IN_PROGRESS'
            assignment.save()
        
        return Response({
            'id': batch.id,
            'name': batch.name,
            'assignment_id': assignment.id,
            'submission_count': len(submission_results),
            'submissions': submission_results
        }, status=status.HTTP_201_CREATED)
    
    def _create_submission(self, request, assignment, metric_id, sub_data, batch, layer):
        """Helper method to create a submission"""
        try:
            metric = ESGMetric.objects.get(id=metric_id)
            
            # Create submission with basic data
            submission_data = {
                'assignment': assignment,
                'metric': metric,
                'batch_submission': batch,
                'submitted_by': request.user,
                'layer': layer,
                'data': sub_data['data']  # JSON data is required
            }
            
            # Add notes if present
            if 'notes' in sub_data:
                submission_data['notes'] = sub_data['notes']
            
            # Set submission layer if specified at submission level
            if 'layer_id' in sub_data and sub_data['layer_id']:
                try:
                    submission_layer = LayerProfile.objects.get(id=sub_data['layer_id'])
                    submission_data['layer'] = submission_layer
                except LayerProfile.DoesNotExist:
                    pass
            
            # Create the submission
            return ESGMetricSubmission.objects.create(**submission_data)
            
        except ESGMetric.DoesNotExist:
            raise ValueError(f"Metric with ID {metric_id} not found") 
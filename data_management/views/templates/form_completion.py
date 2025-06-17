"""
Views for managing form completion and verification status.
"""

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from accounts.permissions import BakerTillyAdmin
from accounts.services import get_accessible_layers
from ...models.templates import FormCompletionStatus, TemplateAssignment, ESGForm
from ...serializers.templates import (
    FormCompletionStatusSerializer,
    FormVerificationSerializer,
    FormSendBackSerializer,
    TemplateVerificationStatusSerializer
)

logger = logging.getLogger(__name__)

class FormCompletionStatusFilter:
    """Custom filter for FormCompletionStatus"""
    def filter_queryset(self, request, queryset, view):
        # Filter by assignment
        assignment_id = request.query_params.get('assignment_id')
        if assignment_id:
            queryset = queryset.filter(assignment_id=assignment_id)
        
        # Filter by layer
        layer_id = request.query_params.get('layer_id')
        if layer_id:
            queryset = queryset.filter(layer_id=layer_id)
        
        # Filter by form ID
        form_id = request.query_params.get('form_id')
        if form_id:
            queryset = queryset.filter(form_selection__form__id=form_id)
        
        # Filter by completion status
        is_completed = request.query_params.get('is_completed')
        if is_completed is not None:
            queryset = queryset.filter(is_completed=is_completed.lower() == 'true')
        
        # Filter by verification status
        is_verified = request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            if status_filter == 'DRAFT':
                queryset = queryset.filter(is_completed=False)
            elif status_filter == 'PENDING_VERIFICATION':
                queryset = queryset.filter(is_completed=True, is_verified=False, revision_required=False)
            elif status_filter == 'REVISION_REQUIRED':
                queryset = queryset.filter(is_completed=True, is_verified=False, revision_required=True)
            elif status_filter == 'VERIFIED':
                queryset = queryset.filter(is_verified=True)
        
        return queryset

class FormCompletionStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing form completion and verification status.
    
    Permissions:
    - Regular users: Can view and complete their own forms
    - Baker Tilly admins: Can verify forms and send them back for changes
    """
    serializer_class = FormCompletionStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['assignment', 'layer', 'form_selection', 'is_completed', 'is_verified']
    ordering_fields = ['completed_at', 'verified_at', 'form_selection__order']
    ordering = ['form_selection__order']
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        user = self.request.user
        
        # Baker Tilly admins can see all form completion statuses
        if getattr(user, 'is_baker_tilly_admin', False) or user.is_staff or user.is_superuser:
            queryset = FormCompletionStatus.objects.all()
        else:
            # Regular users can only see their accessible layers
            accessible_layers = get_accessible_layers(user)
            queryset = FormCompletionStatus.objects.filter(layer__in=accessible_layers)
        
        # Apply custom filtering
        filter_instance = FormCompletionStatusFilter()
        queryset = filter_instance.filter_queryset(self.request, queryset, self)
        
        return queryset.select_related(
            'form_selection__form',
            'assignment__template',
            'layer',
            'completed_by',
            'verified_by'
        )
    
    def perform_create(self, serializer):
        """Override create to set default values"""
        # This shouldn't be called often since FormCompletionStatus is usually auto-created
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """User marks form as complete"""
        form_status = self.get_object()
        
        # Check if user has permission to complete this form
        if not self._can_user_modify_form(request.user, form_status):
            return Response(
                {'error': 'You do not have permission to complete this form'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if form can be completed
        if not form_status.can_complete():
            return Response(
                {'error': 'Form cannot be marked as complete - it may already be verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            form_status.mark_completed(request.user)
            serializer = self.get_serializer(form_status)
            return Response({
                'message': 'Form marked as complete successfully',
                'form_status': serializer.data
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Admin verifies completed form"""
        # Only Baker Tilly admins can verify
        if not (getattr(request.user, 'is_baker_tilly_admin', False) or 
                request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Only Baker Tilly admins can verify forms'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        form_status = self.get_object()
        serializer = FormVerificationSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Check if form can be verified
            if not form_status.can_verify():
                return Response(
                    {'error': 'Form cannot be verified - it must be completed first and not already verified'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                verification_notes = serializer.validated_data.get('verification_notes', '')
                form_status.mark_verified(request.user, verification_notes)
                
                # Return updated form status
                response_serializer = self.get_serializer(form_status)
                return Response({
                    'message': 'Form verified successfully',
                    'form_status': response_serializer.data
                })
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def send_back(self, request, pk=None):
        """Admin sends form back to user for changes"""
        # Only Baker Tilly admins can send forms back
        if not (getattr(request.user, 'is_baker_tilly_admin', False) or 
                request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Only Baker Tilly admins can send forms back'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        form_status = self.get_object()
        serializer = FormSendBackSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                reason = serializer.validated_data.get('reason', '')
                form_status.send_back_for_changes(request.user, reason)
                
                # Return updated form status
                response_serializer = self.get_serializer(form_status)
                return Response({
                    'message': 'Form sent back for changes successfully',
                    'form_status': response_serializer.data
                })
            except Exception as e:
                logger.error(f"Error sending form back: {e}")
                return Response(
                    {'error': 'Failed to send form back for changes'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], url_path='complete-by-ids')
    def complete_by_ids(self, request):
        """
        User-friendly endpoint to complete form using form_id, assignment_id, and optional layer_id
        
        POST /api/form-completion/complete-by-ids/
        {
            "form_id": 3,
            "assignment_id": 1,
            "layer_id": 5  // Optional - defaults to user's layer
        }
        """
        form_id = request.data.get('form_id')
        assignment_id = request.data.get('assignment_id')
        layer_id = request.data.get('layer_id')
        
        # Validate required parameters
        if not form_id or not assignment_id:
            return Response(
                {'error': 'form_id and assignment_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the assignment
            assignment = TemplateAssignment.objects.select_related('template', 'layer').get(pk=assignment_id)
            
            # Get the form
            form = ESGForm.objects.get(pk=form_id)
            
            # Determine target layer
            if layer_id:
                try:
                    from accounts.models import LayerProfile
                    target_layer = LayerProfile.objects.get(pk=layer_id)
                except LayerProfile.DoesNotExist:
                    return Response(
                        {'error': f'Layer with ID {layer_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Use user's layer
                from accounts.models import AppUser
                app_user = AppUser.objects.filter(user=request.user).first()
                if not app_user:
                    return Response(
                        {'error': 'User is not associated with any layer'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                target_layer = app_user.layer
            
            # Check user permissions
            accessible_layers = get_accessible_layers(request.user)
            if target_layer not in accessible_layers:
                return Response(
                    {'error': 'You do not have permission to complete forms for this layer'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get or create TemplateFormSelection
            from ...models.templates import TemplateFormSelection
            form_selection, _ = TemplateFormSelection.objects.get_or_create(
                template=assignment.template,
                form=form,
                defaults={'order': form.order}
            )
            
            # Get or create FormCompletionStatus
            form_status, created = FormCompletionStatus.objects.get_or_create(
                form_selection=form_selection,
                assignment=assignment,
                layer=target_layer,
                defaults={'is_completed': False}
            )
            
            # Check if form can be completed
            if not form_status.can_complete():
                return Response(
                    {'error': 'Form cannot be marked as complete - it may already be verified'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark as completed
            form_status.mark_completed(request.user)
            
            # Return response
            serializer = self.get_serializer(form_status)
            return Response({
                'message': 'Form marked as complete successfully',
                'form_status': serializer.data,
                'created_new_record': created
            })
            
        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ESGForm.DoesNotExist:
            return Response(
                {'error': 'Form not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in complete_by_ids: {e}")
            return Response(
                {'error': 'An unexpected error occurred'},
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='verify-by-ids')
    def verify_by_ids(self, request):
        """
        User-friendly endpoint for admins to verify form using form_id, assignment_id, and optional layer_id
        
        POST /api/form-completion/verify-by-ids/
        {
            "form_id": 3,
            "assignment_id": 1,
            "layer_id": 5,  // Optional - defaults to assignment's layer
            "verification_notes": "Data looks accurate and complete"
        }
        """
        # Only Baker Tilly admins can verify
        if not (getattr(request.user, 'is_baker_tilly_admin', False) or 
                request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Only Baker Tilly admins can verify forms'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        form_id = request.data.get('form_id')
        assignment_id = request.data.get('assignment_id')
        layer_id = request.data.get('layer_id')
        verification_notes = request.data.get('verification_notes', '')
        
        # Validate required parameters
        if not form_id or not assignment_id:
            return Response(
                {'error': 'form_id and assignment_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the assignment
            assignment = TemplateAssignment.objects.select_related('template', 'layer').get(pk=assignment_id)
            
            # Get the form
            form = ESGForm.objects.get(pk=form_id)
            
            # Determine target layer
            if layer_id:
                try:
                    from accounts.models import LayerProfile
                    target_layer = LayerProfile.objects.get(pk=layer_id)
                except LayerProfile.DoesNotExist:
                    return Response(
                        {'error': f'Layer with ID {layer_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Use assignment's layer
                target_layer = assignment.layer
            
            # Get TemplateFormSelection
            from ...models.templates import TemplateFormSelection
            try:
                form_selection = TemplateFormSelection.objects.get(
                    template=assignment.template,
                    form=form
                )
            except TemplateFormSelection.DoesNotExist:
                return Response(
                    {'error': 'Form is not part of this template assignment'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get FormCompletionStatus
            try:
                form_status = FormCompletionStatus.objects.get(
                    form_selection=form_selection,
                    assignment=assignment,
                    layer=target_layer
                )
            except FormCompletionStatus.DoesNotExist:
                return Response(
                    {'error': 'Form completion status not found. Form must be completed first.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if form can be verified
            if not form_status.can_verify():
                return Response(
                    {'error': 'Form cannot be verified - it must be completed first and not already verified'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark as verified
            form_status.mark_verified(request.user, verification_notes)
            
            # Return response
            serializer = self.get_serializer(form_status)
            return Response({
                'message': 'Form verified successfully',
                'form_status': serializer.data
            })
            
        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ESGForm.DoesNotExist:
            return Response(
                {'error': 'Form not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in verify_by_ids: {e}")
            return Response(
                {'error': 'An unexpected error occurred'},
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='send-back-by-ids')
    def send_back_by_ids(self, request):
        """
        User-friendly endpoint for admins to send form back using form_id, assignment_id, and optional layer_id
        
        POST /api/form-completion/send-back-by-ids/
        {
            "form_id": 3,
            "assignment_id": 1,
            "layer_id": 5,  // Optional - defaults to assignment's layer
            "reason": "Please update the energy consumption values for Q3 and Q4."
        }
        """
        # Only Baker Tilly admins can send forms back
        if not (getattr(request.user, 'is_baker_tilly_admin', False) or 
                request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Only Baker Tilly admins can send forms back'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        form_id = request.data.get('form_id')
        assignment_id = request.data.get('assignment_id')
        layer_id = request.data.get('layer_id')
        reason = request.data.get('reason', '')
        
        # Validate required parameters
        if not form_id or not assignment_id:
            return Response(
                {'error': 'form_id and assignment_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the assignment
            assignment = TemplateAssignment.objects.select_related('template', 'layer').get(pk=assignment_id)
            
            # Get the form
            form = ESGForm.objects.get(pk=form_id)
            
            # Determine target layer
            if layer_id:
                try:
                    from accounts.models import LayerProfile
                    target_layer = LayerProfile.objects.get(pk=layer_id)
                except LayerProfile.DoesNotExist:
                    return Response(
                        {'error': f'Layer with ID {layer_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Use assignment's layer
                target_layer = assignment.layer
            
            # Get TemplateFormSelection
            from ...models.templates import TemplateFormSelection
            try:
                form_selection = TemplateFormSelection.objects.get(
                    template=assignment.template,
                    form=form
                )
            except TemplateFormSelection.DoesNotExist:
                return Response(
                    {'error': 'Form is not part of this template assignment'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get FormCompletionStatus
            try:
                form_status = FormCompletionStatus.objects.get(
                    form_selection=form_selection,
                    assignment=assignment,
                    layer=target_layer
                )
            except FormCompletionStatus.DoesNotExist:
                return Response(
                    {'error': 'Form completion status not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Send back for changes
            form_status.send_back_for_changes(request.user, reason)
            
            # Return response
            serializer = self.get_serializer(form_status)
            return Response({
                'message': 'Form sent back for changes successfully',
                'form_status': serializer.data
            })
            
        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ESGForm.DoesNotExist:
            return Response(
                {'error': 'Form not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in send_back_by_ids: {e}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _can_user_modify_form(self, user, form_status):
        """Check if user can modify (complete) this form"""
        # Baker Tilly admins can modify any form
        if getattr(user, 'is_baker_tilly_admin', False) or user.is_staff or user.is_superuser:
            return True
        
        # Regular users can only modify forms for their accessible layers
        accessible_layers = get_accessible_layers(user)
        return form_status.layer in accessible_layers

class TemplateVerificationStatusView(viewsets.GenericViewSet):
    """
    ViewSet for getting template assignment verification overview.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def verification_status(self, request, pk=None):
        """Get verification status overview for a template assignment"""
        try:
            assignment = TemplateAssignment.objects.get(pk=pk)
            
            # Check permissions
            if not self._can_user_access_assignment(request.user, assignment):
                return Response(
                    {'error': 'You do not have permission to view this assignment'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get verification progress
            progress = assignment.verification_progress
            form_statuses = assignment.form_completion_status.all().select_related(
                'form_selection__form', 'completed_by', 'verified_by'
            )
            
            # Calculate percentages
            total_forms = progress['total_forms']
            completion_percentage = (progress['completed_forms'] / total_forms * 100) if total_forms > 0 else 0
            verification_percentage = (progress['verified_forms'] / total_forms * 100) if total_forms > 0 else 0
            
            data = {
                'assignment_id': assignment.id,
                'assignment_name': assignment.template.name,
                'layer_name': assignment.layer.company_name,
                'total_forms': progress['total_forms'],
                'completed_forms': progress['completed_forms'],
                'verified_forms': progress['verified_forms'],
                'pending_verification': progress['pending_verification'],
                'draft_forms': progress['draft_forms'],
                'completion_progress_percentage': round(completion_percentage, 1),
                'verification_progress_percentage': round(verification_percentage, 1),
                'is_fully_completed': assignment.is_fully_completed,
                'is_fully_verified': assignment.is_fully_verified,
                'assignment_status': assignment.get_status_display(),
                'form_statuses': FormCompletionStatusSerializer(form_statuses, many=True).data
            }
            
            return Response(data)
            
        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Template assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _can_user_access_assignment(self, user, assignment):
        """Check if user can access this assignment"""
        # Baker Tilly admins can access any assignment
        if getattr(user, 'is_baker_tilly_admin', False) or user.is_staff or user.is_superuser:
            return True
        
        # Regular users can only access assignments for their accessible layers
        accessible_layers = get_accessible_layers(user)
        return assignment.layer in accessible_layers 
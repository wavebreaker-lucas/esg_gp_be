from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from accounts.permissions import BakerTillyAdmin
from accounts.models import GroupLayer, AppUser, RoleChoices
from ..models import Template, TemplateAssignment
from ..serializers import TemplateSerializer, TemplateAssignmentSerializer

class TemplateViewSet(ModelViewSet):
    """
    ViewSet for managing ESG disclosure templates.
    Only accessible by Baker Tilly admins.
    """
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [BakerTillyAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        return Template.objects.prefetch_related(
            'questions',
            'questions__choices'
        ).all()

class TemplateAssignmentView(APIView):
    """
    View for managing template assignments for client companies.
    Only accessible by Baker Tilly admins.
    """
    permission_classes = [BakerTillyAdmin]
    
    def get(self, request, group_id=None):
        """Get available templates or current assignments"""
        if group_id:
            # Get assignments for specific group
            assignments = TemplateAssignment.objects.filter(company_id=group_id)
            return Response(TemplateAssignmentSerializer(assignments, many=True).data)
        else:
            # Get all available templates
            templates = Template.objects.filter(is_active=True)
            return Response(TemplateSerializer(templates, many=True).data)
    
    def post(self, request, group_id):
        """Assign template to a client company"""
        try:
            with transaction.atomic():
                group = GroupLayer.objects.get(id=group_id)
                template = Template.objects.get(id=request.data['template_id'], is_active=True)
                
                # Get the creator user of the group
                creator = AppUser.objects.get(
                    layer=group,
                    user__role=RoleChoices.CREATOR
                ).user
                
                assignment = TemplateAssignment.objects.create(
                    template=template,
                    company=group,
                    assigned_to=creator,
                    due_date=request.data.get('due_date'),
                    max_possible_score=sum(q.max_score for q in template.questions.all())
                )
                
                return Response({
                    'message': 'Template assigned successfully',
                    'assignment': TemplateAssignmentSerializer(assignment).data
                }, status=status.HTTP_201_CREATED)
                
        except (GroupLayer.DoesNotExist, Template.DoesNotExist) as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, group_id):
        """Remove template assignment"""
        try:
            assignment = TemplateAssignment.objects.get(
                company_id=group_id,
                id=request.data['assignment_id']
            )
            assignment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TemplateAssignment.DoesNotExist:
            return Response({
                'error': 'Assignment not found'
            }, status=status.HTTP_404_NOT_FOUND) 
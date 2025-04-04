"""
Views for managing template assignments.
"""

from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from accounts.permissions import BakerTillyAdmin
from accounts.models import LayerProfile
from ...models import TemplateAssignment
from ...serializers.templates import TemplateAssignmentSerializer


class TemplateAssignmentView(views.APIView):
    """
    API view for managing template assignments to client layers.
    Templates are assigned directly to layers without requiring a specific user.
    Only group layers can have templates assigned to them.
    """
    permission_classes = [IsAuthenticated, BakerTillyAdmin]

    def get(self, request, layer_id):
        """Get all template assignments for a client layer"""
        # Validate that the layer is a group layer
        try:
            layer = LayerProfile.objects.get(id=layer_id)
            if layer.layer_type != 'GROUP':
                return Response(
                    {'error': 'Templates can only be assigned to group layers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except LayerProfile.DoesNotExist:
            return Response(
                {'error': 'Layer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        assignments = TemplateAssignment.objects.filter(
            layer_id=layer_id
        ).select_related('template', 'layer', 'assigned_to')
        
        serializer = TemplateAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, layer_id):
        """Assign a template to a client layer"""
        # Validate that the layer is a group layer
        try:
            layer = LayerProfile.objects.get(id=layer_id)
            if layer.layer_type != 'GROUP':
                return Response(
                    {'error': 'Templates can only be assigned to group layers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except LayerProfile.DoesNotExist:
            return Response(
                {'error': 'Layer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        data = {
            **request.data,
            'layer': layer_id
        }
        serializer = TemplateAssignmentSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, layer_id):
        """Remove a template assignment from a client layer"""
        # Validate that the layer is a group layer
        try:
            layer = LayerProfile.objects.get(id=layer_id)
            if layer.layer_type != 'GROUP':
                return Response(
                    {'error': 'Templates can only be assigned to group layers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except LayerProfile.DoesNotExist:
            return Response(
                {'error': 'Layer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        assignment_id = request.data.get('assignment_id')
        try:
            assignment = TemplateAssignment.objects.get(
                id=assignment_id,
                layer_id=layer_id
            )
            assignment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            ) 
"""
Views for managing ESG form categories.
"""

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import BakerTillyAdmin
from ..models import ESGFormCategory
from ..serializers.templates import ESGFormCategorySerializer


class ESGFormCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ESG form categories with their associated forms.
    Baker Tilly admins can create, update, and delete categories.
    Other users can only view categories.
    """
    queryset = ESGFormCategory.objects.all()
    serializer_class = ESGFormCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Only Baker Tilly admins can create, update, or delete categories.
        All authenticated users can view categories.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), BakerTillyAdmin()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """List all categories with their active forms"""
        categories = self.get_queryset()
        # Prefetch related forms and metrics for performance
        categories = categories.prefetch_related(
            'forms__metrics'
        )
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data) 
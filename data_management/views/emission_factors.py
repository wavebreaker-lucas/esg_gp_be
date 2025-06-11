from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from accounts.permissions import BakerTillyAdmin
from ..models.factors import GHGEmissionFactor
from ..serializers.emission_factors import (
    GHGEmissionFactorSerializer, 
    GHGEmissionFactorListSerializer,
    GHGEmissionFactorBulkCreateSerializer
)


class GHGEmissionFactorViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing GHG Emission Factors.
    
    Provides full CRUD operations for Baker Tilly admins:
    - List all emission factors with filtering and search
    - Retrieve specific emission factor
    - Create new emission factor
    - Update existing emission factor
    - Delete emission factor
    - Bulk create emission factors
    - Get emission factors by category
    """
    
    queryset = GHGEmissionFactor.objects.all().order_by('-year', 'category', 'sub_category')
    serializer_class = GHGEmissionFactorSerializer
    permission_classes = [IsAuthenticated, BakerTillyAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Filtering options
    filterset_fields = {
        'category': ['exact', 'icontains'],
        'sub_category': ['exact', 'icontains'],
        'year': ['exact', 'gte', 'lte'],
        'region': ['exact', 'icontains'],
        'scope': ['exact'],
        'activity_unit': ['exact', 'icontains'],
    }
    
    # Search options
    search_fields = ['name', 'category', 'sub_category', 'source']
    
    # Ordering options
    ordering_fields = ['year', 'category', 'sub_category', 'value', 'name']
    ordering = ['-year', 'category', 'sub_category']
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return GHGEmissionFactorListSerializer
        elif self.action == 'bulk_create':
            return GHGEmissionFactorBulkCreateSerializer
        return GHGEmissionFactorSerializer
    
    def get_queryset(self):
        """Allow filtering by query parameters"""
        queryset = super().get_queryset()
        
        # Additional custom filtering
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)
            
        return queryset
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Bulk create emission factors.
        
        Expects JSON in format:
        {
            "factors": [
                {
                    "name": "Factor Name",
                    "category": "transport",
                    "sub_category": "cars_diesel",
                    "activity_unit": "liters",
                    "value": "2.64",
                    "factor_unit": "kgCO2e/liter",
                    "year": 2025,
                    "region": "ALL",
                    "scope": "1",
                    "source": "Source Name",
                    "source_url": "https://example.com"
                },
                // ... more factors
            ]
        }
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': f'Successfully created/updated {len(result["factors"])} emission factors',
                'factors': GHGEmissionFactorSerializer(result["factors"], many=True).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get all available categories with their subcategories.
        
        Returns a hierarchical structure of categories and subcategories.
        """
        categories = {}
        
        for factor in GHGEmissionFactor.objects.all().order_by('category', 'sub_category'):
            if factor.category not in categories:
                categories[factor.category] = {
                    'name': factor.category,
                    'subcategories': set()
                }
            categories[factor.category]['subcategories'].add(factor.sub_category)
        
        # Convert sets to sorted lists
        for category in categories.values():
            category['subcategories'] = sorted(list(category['subcategories']))
        
        return Response(categories)
    
    @action(detail=False, methods=['get'])
    def search_factors(self, request):
        """
        Advanced search for emission factors.
        
        Query parameters:
        - category: Filter by category
        - sub_category: Filter by subcategory
        - activity_unit: Filter by activity unit
        - year: Filter by year
        - region: Filter by region
        - scope: Filter by scope
        - search: Text search in name, category, subcategory, source
        """
        queryset = self.get_queryset()
        
        # Apply filters
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
            
        sub_category = request.query_params.get('sub_category')
        if sub_category:
            queryset = queryset.filter(sub_category__icontains=sub_category)
            
        activity_unit = request.query_params.get('activity_unit')
        if activity_unit:
            queryset = queryset.filter(activity_unit__icontains=activity_unit)
            
        year = request.query_params.get('year')
        if year:
            try:
                queryset = queryset.filter(year=int(year))
            except ValueError:
                pass
                
        region = request.query_params.get('region')
        if region:
            queryset = queryset.filter(region__icontains=region)
            
        scope = request.query_params.get('scope')
        if scope:
            queryset = queryset.filter(scope__iexact=scope)
            
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(category__icontains=search) |
                Q(sub_category__icontains=search) |
                Q(source__icontains=search)
            )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = GHGEmissionFactorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GHGEmissionFactorListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """
        Bulk delete emission factors by IDs.
        
        Expects JSON: {"ids": [1, 2, 3, ...]}
        """
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            deleted_count, _ = GHGEmissionFactor.objects.filter(id__in=ids).delete()
            return Response({
                'message': f'Successfully deleted {deleted_count} emission factors'
            })
        except Exception as e:
            return Response({
                'error': f'Error deleting factors: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def export_template(self, request):
        """
        Export a CSV template for bulk uploading emission factors.
        
        Returns a CSV template with all the required fields and example data.
        """
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="emission_factors_template.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        header = [
            'name', 'category', 'sub_category', 'activity_unit', 'value', 
            'factor_unit', 'year', 'region', 'scope', 'source', 'source_url'
        ]
        writer.writerow(header)
        
        # Write example rows
        examples = [
            [
                'Diesel - Passenger Car', 'transport', 'transport_cars_diesel', 
                'liters', '2.6460', 'kgCO2e/liter', '2025', 'ALL', '1', 
                'HKEX Reporting Guidance', 'https://example.com'
            ],
            [
                'Electricity - HK Electric', 'electricity', 'hk_hke', 
                'kWh', '0.7100', 'kgCO2e/kWh', '2025', 'ALL', '2', 
                'HK Electric Sustainability Report', 'https://example.com'
            ]
        ]
        
        for example in examples:
            writer.writerow(example)
            
        return response
    
    def perform_create(self, serializer):
        """Override to add logging or additional processing"""
        instance = serializer.save()
        # Could add logging here
        return instance
        
    def perform_update(self, serializer):
        """Override to add logging or additional processing"""
        instance = serializer.save()
        # Could add logging here
        return instance
        
    def perform_destroy(self, instance):
        """Override to add logging or additional processing"""
        # Could add logging here
        instance.delete() 
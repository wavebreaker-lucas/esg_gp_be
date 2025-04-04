from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import BakerTillyAdmin
from ..models import ESGData, BoundaryItem, DataEditLog
from ..serializers import ESGDataSerializer, BoundaryItemSerializer, DataEditLogSerializer

class ESGDataView(APIView):
    """
    View for managing ESG data entries.
    """
    def get(self, request, company_id=None):
        """Get ESG data entries for a company"""
        if company_id:
            data = ESGData.objects.filter(company_id=company_id)
            return Response(ESGDataSerializer(data, many=True).data)
        return Response({'error': 'Company ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        """Create new ESG data entry"""
        serializer = ESGDataSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(submitted_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, data_id):
        """Update ESG data entry"""
        try:
            with transaction.atomic():
                data = ESGData.objects.get(id=data_id)
                
                # Create edit log
                DataEditLog.objects.create(
                    user=request.user,
                    esg_data=data,
                    previous_value=str(data.value),
                    new_value=str(request.data.get('value')),
                    action='UPDATE'
                )
                
                serializer = ESGDataSerializer(data, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except ESGData.DoesNotExist:
            return Response({'error': 'Data not found'}, status=status.HTTP_404_NOT_FOUND)

class ESGVerificationView(APIView):
    """
    View for verifying ESG data entries.
    Only accessible by Baker Tilly admins.
    """
    permission_classes = [BakerTillyAdmin]
    
    def post(self, request, data_id):
        """Verify ESG data entry"""
        try:
            data = ESGData.objects.get(id=data_id)
            data.is_verified = True
            data.verified_by = request.user
            data.verification_date = timezone.now()
            data.save()
            
            return Response(ESGDataSerializer(data).data)
            
        except ESGData.DoesNotExist:
            return Response({'error': 'Data not found'}, status=status.HTTP_404_NOT_FOUND)

class BoundaryItemView(APIView):
    """
    View for managing boundary items.
    """
    def get(self, request):
        """Get all boundary items"""
        items = BoundaryItem.objects.all()
        return Response(BoundaryItemSerializer(items, many=True).data)
    
    def post(self, request):
        """Create new boundary item"""
        serializer = BoundaryItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
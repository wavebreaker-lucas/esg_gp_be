from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from ..permissions import BakerTillyAdmin
from ..models import CustomUser, AppUser, GroupLayer, SubsidiaryLayer, BranchLayer, RoleChoices
from ..serializers.models import GroupLayerSerializer, AppUserSerializer
from data_management.models import Template, TemplateAssignment
from data_management.serializers import TemplateSerializer

class ClientSetupView(APIView):
    """
    View for setting up new clients with initial company structure and users.
    Only accessible by Baker Tilly admins.
    """
    permission_classes = [BakerTillyAdmin]
    
    def get(self, request):
        """Get available templates for client setup"""
        templates = Template.objects.filter(is_active=True)
        return Response(TemplateSerializer(templates, many=True).data)
    
    def post(self, request):
        """Create new client with company structure and initial admin user"""
        try:
            with transaction.atomic():
                # Validate template_id if provided
                template_id = request.data.get('template_id')
                if template_id:
                    try:
                        template = Template.objects.get(id=template_id, is_active=True)
                    except Template.DoesNotExist:
                        return Response({
                            'error': 'Invalid or inactive template ID'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # 1. Create Group Layer
                group_serializer = GroupLayerSerializer(data={
                    'company_name': request.data['company_name'],
                    'company_industry': request.data['industry'],
                    'company_location': request.data.get('location', ''),
                    'shareholding_ratio': 100.00,  # Parent company is 100%
                    'layer_type': 'GROUP'
                })
                group_serializer.is_valid(raise_exception=True)
                group = group_serializer.save()
                
                # 2. Create initial admin user
                admin_user = CustomUser.objects.create_user(
                    email=request.data['admin_email'],
                    password=request.data['admin_password'],
                    role=RoleChoices.CREATOR,
                    must_change_password=True  # Force password change on first login
                )
                
                # 3. Link user to company
                app_user = AppUser.objects.create(
                    user=admin_user,
                    layer=group,
                    name=request.data['admin_name'],
                    title=request.data.get('admin_title', 'ESG Administrator')
                )
                
                # 4. Assign template if provided
                if template_id:
                    template_assignment = TemplateAssignment.objects.create(
                        template=template,
                        company=group,
                        assigned_to=admin_user,
                        max_possible_score=sum(q.max_score for q in template.questions.all())
                    )
                
                response_data = {
                    'message': 'Client setup complete',
                    'group': GroupLayerSerializer(group).data,
                    'admin_user': AppUserSerializer(app_user).data,
                }
                
                if template_id:
                    response_data['template'] = TemplateSerializer(template).data
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class ClientUserManagementView(APIView):
    """
    View for managing users within a client company.
    Only accessible by Baker Tilly admins.
    """
    permission_classes = [BakerTillyAdmin]
    
    def post(self, request, group_id):
        """Add new user to existing client company"""
        try:
            with transaction.atomic():
                group = GroupLayer.objects.get(id=group_id)
                
                # Create user account
                user = CustomUser.objects.create_user(
                    email=request.data['email'],
                    password=request.data['password'],
                    role=request.data['role'],
                    must_change_password=True
                )
                
                # Create app user profile
                app_user = AppUser.objects.create(
                    user=user,
                    layer=group,
                    name=request.data['name'],
                    title=request.data['title']
                )
                
                return Response({
                    'message': 'User added successfully',
                    'user': AppUserSerializer(app_user).data
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, group_id):
        """List all users in a client company"""
        group = GroupLayer.objects.get(id=group_id)
        users = AppUser.objects.filter(layer=group)
        return Response(AppUserSerializer(users, many=True).data)

class ClientStructureView(APIView):
    """
    View for managing client company structure.
    Only accessible by Baker Tilly admins.
    """
    permission_classes = [BakerTillyAdmin]
    
    def post(self, request, group_id):
        """Add subsidiary or branch to existing client"""
        try:
            with transaction.atomic():
                group = GroupLayer.objects.get(id=group_id)
                
                if request.data['layer_type'] == 'SUBSIDIARY':
                    subsidiary = SubsidiaryLayer.objects.create(
                        group_layer=group,
                        company_name=request.data['company_name'],
                        company_industry=request.data['industry'],
                        company_location=request.data.get('location', ''),
                        shareholding_ratio=request.data['shareholding_ratio']
                    )
                    return Response({
                        'message': 'Subsidiary added successfully',
                        'subsidiary_id': subsidiary.id
                    })
                    
                elif request.data['layer_type'] == 'BRANCH':
                    subsidiary = SubsidiaryLayer.objects.get(
                        id=request.data['subsidiary_id']
                    )
                    branch = BranchLayer.objects.create(
                        subsidiary_layer=subsidiary,
                        company_name=request.data['company_name'],
                        company_industry=request.data['industry'],
                        company_location=request.data.get('location', ''),
                        shareholding_ratio=request.data['shareholding_ratio']
                    )
                    return Response({
                        'message': 'Branch added successfully',
                        'branch_id': branch.id
                    })
                    
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, group_id):
        """Get complete structure of a client company"""
        group = GroupLayer.objects.get(id=group_id)
        structure = {
            'group': GroupLayerSerializer(group).data,
            'subsidiaries': []
        }
        
        for subsidiary in group.subsidiarylayer_set.all():
            sub_data = {
                'subsidiary': subsidiary,
                'branches': subsidiary.branchlayer_set.all()
            }
            structure['subsidiaries'].append(sub_data)
            
        return Response(structure) 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Count, Sum
from ..permissions import BakerTillyAdmin
from ..models import CustomUser, AppUser, GroupLayer, SubsidiaryLayer, BranchLayer, RoleChoices
from ..serializers.models import GroupLayerSerializer, AppUserSerializer, SubsidiaryLayerSerializer, BranchLayerSerializer

class ClientSetupView(APIView):
    """
    View for setting up new clients with initial company structure and users.
    Only accessible by Baker Tilly admins.
    """
    permission_classes = [BakerTillyAdmin]
    
    def post(self, request):
        """Create new client with company structure and initial admin user"""
        try:
            with transaction.atomic():
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
                
                # Set the creator to the Baker Tilly admin
                group.created_by_admin = request.user
                group.save()
                
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
                
                return Response({
                    'message': 'Client setup complete',
                    'group': GroupLayerSerializer(group).data,
                    'admin_user': AppUserSerializer(app_user).data
                }, status=status.HTTP_201_CREATED)
                
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
        """List all users in a client company structure (group, subsidiaries, and branches)"""
        try:
            group = GroupLayer.objects.get(id=group_id)
            
            # Get users from group layer
            group_users = AppUser.objects.filter(layer=group)
            
            # Initialize response structure
            response = {
                'group_users': AppUserSerializer(group_users, many=True).data,
                'subsidiary_users': []
            }
            
            # Get users from subsidiaries and their branches
            for subsidiary in group.subsidiarylayer_set.all():
                subsidiary_users = AppUser.objects.filter(layer=subsidiary)
                branch_users = []
                
                # Get users from branches under this subsidiary
                for branch in subsidiary.branchlayer_set.all():
                    branch_users.extend(
                        AppUserSerializer(
                            AppUser.objects.filter(layer=branch), 
                            many=True
                        ).data
                    )
                
                response['subsidiary_users'].append({
                    'subsidiary_id': subsidiary.id,
                    'subsidiary_name': subsidiary.company_name,
                    'users': AppUserSerializer(subsidiary_users, many=True).data,
                    'branch_users': branch_users
                })
            
            return Response(response)
            
        except GroupLayer.DoesNotExist:
            return Response(
                {'error': 'Group layer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
                        shareholding_ratio=request.data['shareholding_ratio'],
                        layer_type='SUBSIDIARY'  # Explicitly set the layer_type
                    )
                    # Set the creator to the Baker Tilly admin
                    subsidiary.created_by_admin = request.user
                    subsidiary.save()
                    
                    # Find the creator user of the parent group 
                    creator_user = AppUser.objects.filter(
                        layer=group,
                        user__role=RoleChoices.CREATOR
                    ).first()
                    
                    if creator_user:
                        # Create an AppUser for the creator in this layer
                        AppUser.objects.create(
                            user=creator_user.user,
                            name=creator_user.name,
                            layer=subsidiary,
                            title=creator_user.title or "Administrator"
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
                        shareholding_ratio=request.data['shareholding_ratio'],
                        layer_type='BRANCH'  # Explicitly set the layer_type
                    )
                    # Set the creator to the Baker Tilly admin
                    branch.created_by_admin = request.user
                    branch.save()
                    
                    # Find the creator user of the parent subsidiary
                    creator_user = AppUser.objects.filter(
                        layer=subsidiary,
                        user__role=RoleChoices.CREATOR
                    ).first()
                    
                    # If no creator found in subsidiary, look in the group
                    if not creator_user:
                        creator_user = AppUser.objects.filter(
                            layer=subsidiary.group_layer,
                            user__role=RoleChoices.CREATOR
                        ).first()
                    
                    if creator_user:
                        # Create an AppUser for the creator in this layer
                        AppUser.objects.create(
                            user=creator_user.user,
                            name=creator_user.name,
                            layer=branch,
                            title=creator_user.title or "Administrator"
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
        try:
            group = GroupLayer.objects.get(id=group_id)
            structure = {
                'group': GroupLayerSerializer(group).data,
                'subsidiaries': []
            }
            
            for subsidiary in group.subsidiarylayer_set.all():
                sub_data = {
                    'subsidiary': SubsidiaryLayerSerializer(subsidiary).data,
                    'branches': BranchLayerSerializer(subsidiary.branchlayer_set.all(), many=True).data
                }
                structure['subsidiaries'].append(sub_data)
                
            return Response(structure)
        except GroupLayer.DoesNotExist:
            return Response(
                {'error': 'Group layer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, group_id):
        """Delete a subsidiary or branch from a client company structure"""
        try:
            with transaction.atomic():
                group = GroupLayer.objects.get(id=group_id)
                
                # Get layer ID and type from request data
                layer_id = request.data.get('layer_id')
                layer_type = request.data.get('layer_type')
                
                if not layer_id:
                    return Response(
                        {'error': 'layer_id is required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if not layer_type:
                    return Response(
                        {'error': 'layer_type is required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
                if layer_type == 'SUBSIDIARY':
                    try:
                        # Ensure the subsidiary belongs to this group
                        subsidiary = SubsidiaryLayer.objects.get(id=layer_id, group_layer=group)
                        
                        # Check if subsidiary has branches
                        if subsidiary.branchlayer_set.exists():
                            return Response(
                                {'error': 'Cannot delete subsidiary with branches. Delete branches first.'}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                            
                        # Delete the subsidiary
                        subsidiary.delete()
                        return Response(
                            {'message': 'Subsidiary deleted successfully'}, 
                            status=status.HTTP_200_OK
                        )
                        
                    except SubsidiaryLayer.DoesNotExist:
                        return Response(
                            {'error': 'Subsidiary not found or does not belong to this group'}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
                        
                elif layer_type == 'BRANCH':
                    try:
                        # Get the subsidiary ID
                        subsidiary_id = request.data.get('subsidiary_id')
                        
                        if not subsidiary_id:
                            return Response(
                                {'error': 'subsidiary_id is required for branch deletion'}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                            
                        # Ensure the subsidiary belongs to this group
                        subsidiary = SubsidiaryLayer.objects.get(id=subsidiary_id, group_layer=group)
                        
                        # Ensure the branch belongs to this subsidiary
                        branch = BranchLayer.objects.get(id=layer_id, subsidiary_layer=subsidiary)
                        
                        # Delete the branch
                        branch.delete()
                        return Response(
                            {'message': 'Branch deleted successfully'}, 
                            status=status.HTTP_200_OK
                        )
                        
                    except SubsidiaryLayer.DoesNotExist:
                        return Response(
                            {'error': 'Subsidiary not found or does not belong to this group'}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
                    except BranchLayer.DoesNotExist:
                        return Response(
                            {'error': 'Branch not found or does not belong to this subsidiary'}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
                        
                else:
                    return Response(
                        {'error': 'Invalid layer_type. Must be SUBSIDIARY or BRANCH.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
        except GroupLayer.DoesNotExist:
            return Response(
                {'error': 'Group layer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ClientStatisticsView(APIView):
    """
    View for getting summary statistics of clients.
    Only accessible by Baker Tilly admins.
    """
    permission_classes = [BakerTillyAdmin]
    
    def get(self, request, group_id=None):
        """Get statistics about subsidiaries, branches, and users"""
        try:
            if group_id:
                # Get statistics for a specific group
                group = GroupLayer.objects.get(id=group_id)
                stats = self._get_group_statistics(group)
                return Response(stats)
            else:
                # Get statistics for all groups
                all_stats = {
                    'total_groups': GroupLayer.objects.count(),
                    'total_subsidiaries': SubsidiaryLayer.objects.count(),
                    'total_branches': BranchLayer.objects.count(),
                    'total_users': AppUser.objects.count(),
                    'groups': []
                }
                
                # Get detailed stats for each group
                for group in GroupLayer.objects.all():
                    group_stats = self._get_group_statistics(group)
                    all_stats['groups'].append(group_stats)
                
                return Response(all_stats)
                
        except GroupLayer.DoesNotExist:
            return Response(
                {'error': 'Group layer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_group_statistics(self, group):
        """Helper method to get statistics for a specific group"""
        subsidiaries = group.subsidiarylayer_set.all()
        
        # Get all subsidiary IDs for this group
        subsidiary_ids = subsidiaries.values_list('id', flat=True)
        
        # Count branches for these subsidiaries
        total_branches = BranchLayer.objects.filter(subsidiary_layer_id__in=subsidiary_ids).count()
        
        # Get user counts by role
        group_users = AppUser.objects.filter(layer=group)
        subsidiary_users = AppUser.objects.filter(layer__in=subsidiary_ids)
        branch_users = AppUser.objects.filter(
            layer__in=BranchLayer.objects.filter(
                subsidiary_layer_id__in=subsidiary_ids
            ).values_list('id', flat=True)
        )
        
        # Count users by role
        def count_users_by_role(queryset):
            return {
                'total': queryset.count(),
                'by_role': {
                    'creator': queryset.filter(user__role=RoleChoices.CREATOR).count(),
                    'management': queryset.filter(user__role=RoleChoices.MANAGEMENT).count(),
                    'operation': queryset.filter(user__role=RoleChoices.OPERATION).count()
                }
            }
        
        return {
            'group_id': group.id,
            'group_name': group.company_name,
            'statistics': {
                'subsidiaries': subsidiaries.count(),
                'branches': total_branches,
                'users': {
                    'group': count_users_by_role(group_users),
                    'subsidiaries': count_users_by_role(subsidiary_users),
                    'branches': count_users_by_role(branch_users),
                    'total': group_users.count() + subsidiary_users.count() + branch_users.count()
                }
            }
        } 
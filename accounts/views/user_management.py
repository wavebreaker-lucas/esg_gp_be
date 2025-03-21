from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response
import json
import csv
import io

from ..models import AppUser, LayerProfile, CustomUser, CSVTemplate, RoleChoices, GroupLayer, BranchLayer
from ..serializers import AppUserSerializer
from ..services import send_email_to_user, generate_otp_code, send_otp_via_email
from ..permissions import CanManageAppUsers
from .mixins import CSVExportMixin, ErrorHandlingMixin

class AppUserViewSet(ModelViewSet, CSVExportMixin, ErrorHandlingMixin):
    """
    ViewSet for managing AppUser instances.
    Provides CRUD operations and additional functionality like CSV import/export.
    """
    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer
    permission_classes = [IsAuthenticated, CanManageAppUsers]
    parser_classes = [MultiPartParser, JSONParser]

    def partial_update(self, request, pk=None):
        """Partially update an AppUser"""
        try:
            app_user = self.get_object()
            serializer = self.get_serializer(app_user, data=request.data, partial=True)
            
            if serializer.is_valid():
                user_data = request.data.get("user", {})
                new_email = user_data.get("email")
                
                if new_email and new_email != app_user.user.email:
                    if CustomUser.objects.exclude(pk=app_user.user.pk).filter(email=new_email).exists():
                        return self.handle_validation_error("Email is already in use by another user.")
                    
                    # Update email and send OTP
                    app_user.user.email = new_email
                    app_user.user.is_active = False
                    app_user.user.otp_code = generate_otp_code()
                    app_user.user.otp_created_at = timezone.now()
                    app_user.user.save()
                    
                    send_otp_via_email(new_email, app_user.user.otp_code)

                serializer.save()
                return Response(serializer.data)
            return self.handle_validation_error(serializer.errors)

        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=True, methods=["post"], url_path="add-user")
    def add_user(self, request, pk=None):
        """Add a new user to a layer"""
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)

            # Check user limit
            non_creator_count = AppUser.objects.filter(layer=layer).exclude(user__role="CREATOR").count()
            if non_creator_count >= 5:
                return self.handle_validation_error("Maximum number of users (5) for this layer has been reached.")

            email = request.data.get("user", {}).get("email")
            role = request.data.get("role", "OPERATION").upper()
            
            if not email:
                return self.handle_validation_error("Email is required to add a user.")

            # Create or get user
            user = self._get_or_create_user(email, role)

            # Create app user
            app_user = AppUser.objects.create(
                user=user,
                name=request.data.get("name", email.split("@")[0]),
                layer=layer,
                title=request.data.get("title", "Member"),
            )

            return Response(
                {
                    "message": "User added successfully to the layer.",
                    "app_user": AppUserSerializer(app_user).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return self.handle_unknown_error(e)

    def _get_or_create_user(self, email, role):
        """Helper method to get or create a user"""
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            password = CustomUser.objects.make_random_password()
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                role=role,
                is_active=True,
                password_updated_at=None
            )
            if not send_email_to_user(email, password):
                raise ValueError(f"Failed to send email to {email}.")
        return user

    @action(detail=True, methods=["post"], url_path="resend-email")
    def resend_email(self, request, pk=None):
        """Resend login credentials email"""
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)

            email = request.data.get("email")
            if not email:
                return self.handle_validation_error("Email is required to resend credentials.")

            try:
                app_user = AppUser.objects.get(layer=layer, user__email=email)
            except AppUser.DoesNotExist:
                return self.handle_not_found_error("User not found in this layer.")

            # Reset password and send email
            user = app_user.user
            new_password = CustomUser.objects.make_random_password()
            user.set_password(new_password)
            user.password_updated_at = None
            user.save()

            if not send_email_to_user(user.email, new_password):
                return self.handle_validation_error("Failed to send email to the user.")

            return Response(
                {"message": "Email with login credentials has been sent successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=True, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request, pk=None):
        """Delete multiple users from a layer"""
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)

            user_ids = request.data.get("ids", [])
            if isinstance(user_ids, str):
                try:
                    user_ids = json.loads(user_ids)
                except json.JSONDecodeError:
                    return self.handle_validation_error("Invalid format. Expected a list or JSON array.")

            if not isinstance(user_ids, list) or not user_ids:
                return self.handle_validation_error("No user IDs provided.")

            users_to_delete = AppUser.objects.filter(layer=layer, id__in=user_ids)
            if not users_to_delete.exists():
                return self.handle_not_found_error("No matching AppUsers found for deletion.")

            creator_users = users_to_delete.filter(user__role=RoleChoices.CREATOR)
            if creator_users.exists():
                return self.handle_permission_error("You can't delete users with CREATOR role.")

            with transaction.atomic():
                custom_user_ids = list(users_to_delete.values_list('user_id', flat=True).distinct())
                count = users_to_delete.count()
                
                users_to_delete.delete()
                
                # Clean up CustomUser if they have no remaining AppUser entries
                for user_id in custom_user_ids:
                    if not AppUser.objects.filter(user_id=user_id).exists():
                        CustomUser.objects.filter(id=user_id).delete()

            return Response(
                {"message": f"Successfully deleted {count} user(s) from layer {layer.id}."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=True, methods=["post"], url_path="import-csv")
    def import_csv(self, request, pk=None):
        """Import users from CSV file"""
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)

            file = request.FILES.get("file")
            if not file:
                return self.handle_validation_error("No file provided.")

            decoded_file = file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded_file)

            with transaction.atomic():
                created_users = []
                for row in reader:
                    email = row.get("email")
                    name = row.get("name")
                    title = row.get("title", "Member")
                    role = row.get("role", "OPERATION")

                    if not email or not name:
                        raise ValueError("Email and name are required fields in the CSV.")

                    user = self._get_or_create_user(email, role)
                    if AppUser.objects.filter(user=user, layer=layer).exists():
                        continue

                    app_user = AppUser.objects.create(
                        user=user,
                        name=name,
                        title=title,
                        layer=layer,
                    )
                    created_users.append(app_user)

            return Response(
                {
                    "message": "Users imported successfully.",
                    "created_users": self.get_serializer(created_users, many=True).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return self.handle_validation_error(str(e))
        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=True, methods=['get'], url_path='export-csv')
    def export_csv(self, request, pk=None):
        """Export users to CSV file"""
        try:
            layer = LayerProfile.objects.get(id=pk)
            app_users = AppUser.objects.filter(layer=layer)

            response = self.get_csv_response(f"{layer.company_name}_User_Accounts.csv")
            writer = csv.writer(response)
            writer.writerow(["email", "name", "title", "role"])

            for app_user in app_users:
                writer.writerow([
                    app_user.user.email,
                    app_user.name,
                    app_user.title,
                    app_user.user.role
                ])

            return response

        except LayerProfile.DoesNotExist:
            return self.handle_not_found_error("Layer not found.")
        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=False, methods=['get'], url_path='download-example')
    def download_app_users_template(self, request):
        """Download CSV template for user imports"""
        try:
            template_type = 'appuser'
            file_name = 'User_Create_Template.csv'
            
            try:
                template = CSVTemplate.objects.get(template_type=template_type, file__icontains=file_name)
            except CSVTemplate.DoesNotExist:
                template = None

            if template and template.file:
                download_url = template.file.url
            else:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['email', 'name', 'title', 'role'])
                csv_content = output.getvalue()
                output.close()
                
                default_storage.save(file_name, ContentFile(csv_content.encode('utf-8')))
                template = CSVTemplate.objects.create(template_type=template_type, file=file_name)
                download_url = template.file.url

            return Response({"download_url": download_url}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=False, methods=["get"], url_path="table")
    def get_user_table(self, request):
        """
        Get a table of users with their layer information.
        Users can only see other users within their group hierarchy.
        
        Query parameters:
        - group_id: Optional. Filter users by group layer (includes users in subsidiaries and branches under this group)
        - subsidiary_id: Optional. Filter users by subsidiary layer (includes users in branches under this subsidiary)
        - branch_id: Optional. Filter users by branch layer
        - role: Optional. Filter users by role (CREATOR, MANAGEMENT, OPERATION)
        """
        try:
            # Get filter parameters
            group_id = request.query_params.get('group_id')
            subsidiary_id = request.query_params.get('subsidiary_id')
            branch_id = request.query_params.get('branch_id')
            role = request.query_params.get('role')

            # Determine user's groups (a user might be in multiple groups via different AppUsers)
            user_groups = set()
            
            # First, handle Baker Tilly admins who can see all groups
            if request.user.is_baker_tilly_admin or request.user.is_superuser:
                # If a specific group is requested, filter by that group
                if group_id:
                    user_groups.add(int(group_id))
                else:
                    # Otherwise, include all groups
                    user_groups = set(GroupLayer.objects.values_list('id', flat=True))
            else:
                # Regular users can only see their own group(s)
                for app_user in request.user.app_users.select_related('layer').all():
                    # Get the group ID depending on layer type
                    if app_user.layer.layer_type == 'GROUP':
                        user_groups.add(app_user.layer.grouplayer.id)
                    elif app_user.layer.layer_type == 'SUBSIDIARY':
                        user_groups.add(app_user.layer.subsidiarylayer.group_layer_id)
                    elif app_user.layer.layer_type == 'BRANCH':
                        user_groups.add(app_user.layer.branchlayer.subsidiary_layer.group_layer_id)
                
                # If group_id is specified, make sure it's one the user has access to
                if group_id and int(group_id) in user_groups:
                    user_groups = {int(group_id)}
            
            # If user has no groups or requested a group they don't have access to
            if not user_groups:
                return Response({'users': [], 'total': 0})
            
            # Build query for users in accessible groups
            users = []
            for group_id in user_groups:
                # Get the group
                group = GroupLayer.objects.get(id=group_id)
                
                # Get all users in the group
                group_users = AppUser.objects.filter(layer=group)
                
                # Get subsidiary layers under this group
                subsidiary_layers = group.subsidiarylayer_set.all()
                subsidiary_ids = subsidiary_layers.values_list('id', flat=True)
                
                # Filter by subsidiary if requested
                if subsidiary_id:
                    subsidiary_layers = subsidiary_layers.filter(id=subsidiary_id)
                    subsidiary_ids = subsidiary_layers.values_list('id', flat=True)
                
                # Get users in subsidiaries
                subsidiary_users = AppUser.objects.filter(layer_id__in=subsidiary_ids)
                
                # Get branch layers under these subsidiaries
                branch_layers = BranchLayer.objects.filter(subsidiary_layer_id__in=subsidiary_ids)
                
                # Filter by branch if requested
                if branch_id:
                    branch_layers = branch_layers.filter(id=branch_id)
                
                # Get users in branches
                branch_users = AppUser.objects.filter(layer_id__in=branch_layers.values_list('id', flat=True))
                
                # Combine all users
                all_users = group_users | subsidiary_users | branch_users
                
                # Filter by role if specified
                if role:
                    all_users = all_users.filter(user__role=role.upper())
                
                # Add to our list
                users.extend(all_users.select_related('user', 'layer').prefetch_related(
                    'layer__grouplayer', 'layer__subsidiarylayer', 'layer__branchlayer'
                ))
            
            # Prepare response data
            user_table = []
            for app_user in users:
                layer = app_user.layer
                layer_info = {
                    'id': layer.id,
                    'name': layer.company_name,
                    'type': layer.layer_type
                }

                # Get parent information
                if hasattr(layer, 'branchlayer'):
                    parent = layer.branchlayer.subsidiary_layer
                    layer_info['parent'] = {
                        'id': parent.id,
                        'name': parent.company_name,
                        'type': 'SUBSIDIARY'
                    }
                    group = parent.group_layer
                    layer_info['group'] = {
                        'id': group.id,
                        'name': group.company_name,
                        'type': 'GROUP'
                    }
                elif hasattr(layer, 'subsidiarylayer'):
                    parent = layer.subsidiarylayer.group_layer
                    layer_info['parent'] = {
                        'id': parent.id,
                        'name': parent.company_name,
                        'type': 'GROUP'
                    }

                user_data = {
                    'id': app_user.id,
                    'name': app_user.name,
                    'email': app_user.user.email,
                    'role': app_user.user.role,
                    'title': app_user.title,
                    'layer': layer_info,
                    'is_active': app_user.user.is_active,
                    'must_change_password': app_user.user.must_change_password
                }
                user_table.append(user_data)

            return Response({
                'users': user_table,
                'total': len(user_table)
            })

        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=False, methods=["get"], url_path="my-groups")
    def get_my_groups(self, request):
        """
        Get all group layers the authenticated user has access to, regardless of which layer
        they're directly associated with. For users at subsidiary or branch levels, this will
        return their parent group information.
        """
        try:
            user = request.user
            app_users = AppUser.objects.filter(user=user).select_related(
                'layer'
            ).prefetch_related(
                'layer__grouplayer',
                'layer__subsidiarylayer',
                'layer__branchlayer'
            )
            
            # Track unique groups to avoid duplicates
            unique_groups = {}
            
            for app_user in app_users:
                layer = app_user.layer
                group_info = None
                
                # Determine the group based on layer type
                if layer.layer_type == 'GROUP' and hasattr(layer, 'grouplayer'):
                    # User is directly in a group
                    group_info = {
                        'id': layer.id,
                        'name': layer.company_name,
                        'direct_access': True,
                        'app_user_id': app_user.id,
                        'role': app_user.user.role
                    }
                elif layer.layer_type == 'SUBSIDIARY' and hasattr(layer, 'subsidiarylayer'):
                    # User is in a subsidiary, get parent group
                    parent = layer.subsidiarylayer.group_layer
                    group_info = {
                        'id': parent.id,
                        'name': parent.company_name,
                        'direct_access': False,
                        'subsidiary_id': layer.id,
                        'subsidiary_name': layer.company_name,
                        'app_user_id': app_user.id,
                        'role': app_user.user.role
                    }
                elif layer.layer_type == 'BRANCH' and hasattr(layer, 'branchlayer'):
                    # User is in a branch, get parent subsidiary and group
                    subsidiary = layer.branchlayer.subsidiary_layer
                    group = subsidiary.group_layer
                    group_info = {
                        'id': group.id,
                        'name': group.company_name,
                        'direct_access': False,
                        'subsidiary_id': subsidiary.id,
                        'subsidiary_name': subsidiary.company_name,
                        'branch_id': layer.id,
                        'branch_name': layer.company_name,
                        'app_user_id': app_user.id,
                        'role': app_user.user.role
                    }
                
                if group_info and group_info['id'] not in unique_groups:
                    unique_groups[group_info['id']] = group_info
                
            return Response({
                'groups': list(unique_groups.values()),
                'total': len(unique_groups)
            })
            
        except Exception as e:
            return self.handle_unknown_error(e)

    # Add other methods (resend_email, bulk_delete, etc.) following the same pattern 
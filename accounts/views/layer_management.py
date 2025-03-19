import uuid
from django.db import transaction
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
import csv, io, json, pytz

from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Count, Prefetch

from ..models import (
    LayerProfile, GroupLayer, SubsidiaryLayer, BranchLayer,
    LayerTypeChoices, RoleChoices, CustomUser, AppUser, CSVTemplate
)
from ..serializers import (
    GroupLayerSerializer, SubsidiaryLayerSerializer,
    BranchLayerSerializer, AppUserSerializer
)
from ..services import (
    get_accessible_layers, is_creator_on_layer, has_permission_to_manage_users,
    get_parent_layer, get_flat_sorted_layers, send_email_to_user
)
from .mixins import CSVExportMixin, ErrorHandlingMixin

class LayerProfileViewSet(ViewSet, CSVExportMixin, ErrorHandlingMixin):
    """
    A ViewSet for managing layers (GroupLayer, SubsidiaryLayer, BranchLayer).
    Provides CRUD operations, bulk operations, and import/export functionality.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def get_queryset(self):
        """
        Get optimized queryset with prefetched relationships and annotations
        """
        base_queryset = get_accessible_layers(self.request.user)
        return base_queryset.prefetch_related(
            Prefetch(
                'app_users',
                queryset=AppUser.objects.select_related('user'),
                to_attr='prefetched_app_users'
            )
        ).annotate(
            user_count=Count('app_users')
        )

    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_cookie)
    def list(self, request):
        """List all accessible layers with optional type filtering"""
        try:
            user = request.user
            layer_type_filter = request.query_params.get("layer_type")
            
            # Create a cache key that includes all query parameters, not just layer_type
            query_params_str = "&".join(f"{k}={v}" for k, v in sorted(request.query_params.items()))
            cache_key = f'layer_list_{user.id}_{query_params_str}'
            
            # Skip cache for force_refresh
            if request.query_params.get('force_refresh'):
                cache.delete(cache_key)
                cached_result = None
            else:
                cached_result = cache.get(cache_key)
                
            if cached_result:
                return Response(cached_result)

            accessible_layers = self.get_queryset()
            
            # Apply any filters from query parameters
            if 'group_id' in request.query_params:
                group_id = request.query_params.get('group_id')
                # Get layers for this group
                group_layers = accessible_layers.filter(id=group_id, layer_type='GROUP')
                
                # Get subsidiaries for this group
                subsidiary_ids = SubsidiaryLayer.objects.filter(
                    group_layer_id=group_id
                ).values_list('id', flat=True)
                subsidiary_layers = accessible_layers.filter(
                    id__in=subsidiary_ids,
                    layer_type='SUBSIDIARY'
                )
                
                # Get branches for subsidiaries of this group
                branch_ids = BranchLayer.objects.filter(
                    subsidiary_layer_id__in=subsidiary_ids
                ).values_list('id', flat=True)
                branch_layers = accessible_layers.filter(
                    id__in=branch_ids, 
                    layer_type='BRANCH'
                )
                
                # Combine all filtered layers
                accessible_layers = (group_layers | subsidiary_layers | branch_layers).distinct()

            if layer_type_filter:
                filter_types = [ft.strip().upper() for ft in layer_type_filter.split(',') if ft.strip()]
                valid_types = {choice.value for choice in LayerTypeChoices}

                invalid_types = [ft for ft in filter_types if ft not in valid_types]
                if invalid_types:
                    return self.handle_validation_error(
                        f"Invalid layer_type(s): {', '.join(invalid_types)}. Must be one of: {', '.join(valid_types)}"
                    )

                filtered_layers = accessible_layers.filter(layer_type__in=filter_types).distinct()
                result = get_flat_sorted_layers(filtered_layers)
            else:
                result = get_flat_sorted_layers(accessible_layers)

            cache.set(cache_key, result, timeout=60 * 5)
            return Response(result)

        except Exception as e:
            return self.handle_unknown_error(e)

    def retrieve(self, request, pk=None):
        """Get a specific layer by ID"""
        try:
            user = request.user
            cache_key = f'layer_detail_{pk}_{user.id}'
            cached_result = cache.get(cache_key)
            
            if cached_result:
                return Response(cached_result)

            accessible_layers = self.get_queryset()

            try:
                layer = accessible_layers.get(id=pk)
            except LayerProfile.DoesNotExist:
                return self.handle_not_found_error("Layer not found or you do not have access to it.")

            if hasattr(layer, "grouplayer"):
                serializer = GroupLayerSerializer(layer.grouplayer)
            elif hasattr(layer, "subsidiarylayer"):
                serializer = SubsidiaryLayerSerializer(layer.subsidiarylayer)
            elif hasattr(layer, "branchlayer"):
                serializer = BranchLayerSerializer(layer.branchlayer)
            else:
                return self.handle_validation_error("Layer type not recognized.")

            cache.set(cache_key, serializer.data, timeout=60 * 5)
            return Response(serializer.data)

        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=True, methods=["get"], url_path="users")
    def get_users(self, request, pk=None):
        """Get all users for a specific layer"""
        try:
            layer = LayerProfile.objects.get(id=pk)

            if not has_permission_to_manage_users(request.user, layer):
                return self.handle_permission_error(
                    "You do not have permission to access users for this layer."
                )

            if layer.layer_type == 'GROUP':
                app_users = layer.app_users.all()
            else:
                app_users = AppUser.objects.filter(layer=layer).exclude(
                    user__role=RoleChoices.CREATOR
                )

            serializer = AppUserSerializer(app_users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except LayerProfile.DoesNotExist:
            return self.handle_not_found_error("Layer not found.")
        except Exception as e:
            return self.handle_unknown_error(e)

    def create(self, request):
        """Create a new layer (Subsidiary or Branch)"""
        try:
            layer_type = request.data.get("layer_type")
            app_users_data = request.data.get("app_users", [])
            
            if not layer_type:
                return self.handle_validation_error("Layer type is required.")

            with transaction.atomic():
                # Create layer based on type
                layer = self._create_layer(request, layer_type)
                
                # Add creator user
                creator_user = self._add_creator_to_layer(request, layer)
                
                # Add additional users
                created_users = self._add_users_to_layer(
                    layer, app_users_data
                )

                # Invalidate relevant caches
                # Clear user-specific layer list caches
                cache_key = f'layer_list_{request.user.id}_None'
                cache.delete(cache_key)
                # Also clear any filtered caches
                cache_key = f'layer_list_{request.user.id}_{layer_type}'
                cache.delete(cache_key)
                
                # If this is a subsidiary or branch, invalidate parent group's cache
                parent_layer_id = None
                if layer_type == "SUBSIDIARY" and request.data.get("group_id"):
                    parent_layer_id = request.data.get("group_id")
                elif layer_type == "BRANCH" and request.data.get("subsidiary_id"):
                    try:
                        subsidiary = SubsidiaryLayer.objects.get(id=request.data.get("subsidiary_id"))
                        parent_layer_id = subsidiary.group_layer.id
                    except SubsidiaryLayer.DoesNotExist:
                        pass
                    
                if parent_layer_id:
                    cache_key = f'layer_detail_{parent_layer_id}_{request.user.id}'
                    cache.delete(cache_key)

                serializer = self._get_layer_serializer(layer)
                return Response(
                    {
                        "layer": serializer.data,
                        "created_users": created_users
                    },
                    status=status.HTTP_201_CREATED
                )

        except ValidationError as e:
            return self.handle_validation_error(e)
        except PermissionDenied as e:
            return self.handle_permission_error(e)
        except Exception as e:
            return self.handle_unknown_error(e)

    def _create_layer(self, request, layer_type):
        """Helper method to create a layer based on type"""
        if layer_type == "SUBSIDIARY":
            return self._create_subsidiary_layer(request)
        elif layer_type == "BRANCH":
            return self._create_branch_layer(request)
        else:
            raise ValidationError(
                "Invalid layer type. Only SUBSIDIARY or BRANCH layers can be created."
            )

    def _create_subsidiary_layer(self, request):
        """Helper method to create a subsidiary layer"""
        serializer = SubsidiaryLayerSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        group_id = request.data.get("group_id")
        if not group_id:
            raise ValidationError("Group ID is required for subsidiary layers.")

        group_layer = GroupLayer.objects.get(id=group_id)
        if not is_creator_on_layer(request.user, group_layer):
            raise PermissionDenied(
                "You do not have permission to create subsidiaries for this group."
            )

        # Create the subsidiary layer
        subsidiary_layer = serializer.save()
        # Set the creator to the current user (could be Baker Tilly admin or client creator)
        subsidiary_layer.created_by_admin = request.user
        subsidiary_layer.save()
        
        return subsidiary_layer

    def _create_branch_layer(self, request):
        """Helper method to create a branch layer"""
        serializer = BranchLayerSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        subsidiary_id = request.data.get("subsidiary_id")
        if not subsidiary_id:
            raise ValidationError("Subsidiary ID is required for branch layers.")

        subsidiary_layer = SubsidiaryLayer.objects.get(id=subsidiary_id)
        if not is_creator_on_layer(request.user, subsidiary_layer):
            raise PermissionDenied(
                "You do not have permission to create branches for this subsidiary."
            )

        # Create the branch layer
        branch_layer = serializer.save()
        # Set the creator to the current user (could be Baker Tilly admin or client creator)
        branch_layer.created_by_admin = request.user
        branch_layer.save()
        
        return branch_layer

    def _get_layer_serializer(self, layer):
        """Helper method to get the appropriate serializer for a layer"""
        if isinstance(layer, SubsidiaryLayer):
            return SubsidiaryLayerSerializer(layer)
        elif isinstance(layer, BranchLayer):
            return BranchLayerSerializer(layer)
        raise ValidationError("Invalid layer type")

    def destroy(self, request, pk=None):
        """Delete a layer"""
        try:
            # First check if user is a Baker Tilly admin
            is_baker_tilly_admin = getattr(request.user, 'is_baker_tilly_admin', False)
            
            if is_baker_tilly_admin:
                # Baker Tilly admins can delete any non-GROUP layer
                try:
                    layer = LayerProfile.objects.get(id=pk)
                except LayerProfile.DoesNotExist:
                    return self.handle_not_found_error("Layer not found.")
            else:
                # For regular users, apply the more restrictive query
                try:
                    layer = LayerProfile.objects.get(id=pk, app_users__user=request.user)
                except LayerProfile.DoesNotExist:
                    return self.handle_not_found_error("Layer not found or you do not have access to it.")

            if layer.layer_type == LayerTypeChoices.GROUP:
                return self.handle_permission_error("Cannot delete a layer with layer_type GROUP.")

            # For regular users, additional permission checks
            if not is_baker_tilly_admin:
                app_user = AppUser.objects.filter(user=request.user, layer=layer).first()
                if not app_user or app_user.user.role != RoleChoices.CREATOR:
                    return self.handle_permission_error("You do not have permission to delete this layer.")

            # Get parent layer for cache invalidation
            parent_layer_id = None
            if hasattr(layer, 'branchlayer'):
                parent_layer_id = layer.branchlayer.subsidiary_layer.group_layer.id
            elif hasattr(layer, 'subsidiarylayer'):
                parent_layer_id = layer.subsidiarylayer.group_layer.id

            # Delete the layer
            layer.delete()
            
            # Invalidate relevant caches
            # Clear user-specific layer list caches
            for app_user in AppUser.objects.filter(user=request.user):
                cache_key = f'layer_list_{request.user.id}_None'
                cache.delete(cache_key)
                # Also clear any filtered caches
                for layer_type in ['GROUP', 'SUBSIDIARY', 'BRANCH']:
                    cache_key = f'layer_list_{request.user.id}_{layer_type}'
                    cache.delete(cache_key)
            
            # If this was a subsidiary or branch, invalidate parent group's cache
            if parent_layer_id:
                cache_key = f'layer_detail_{parent_layer_id}_{request.user.id}'
                cache.delete(cache_key)

            return Response(
                {"message": "Layer deleted successfully."},
                status=status.HTTP_204_NO_CONTENT
            )

        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """Delete multiple layers in bulk"""
        try:
            ids = request.data.get("ids", [])
            if isinstance(ids, str):
                try:
                    ids = json.loads(ids)
                except json.JSONDecodeError:
                    return self.handle_validation_error("Invalid format. Expected a list or JSON array.")

            if not isinstance(ids, list) or not ids:
                return self.handle_validation_error("No layer IDs provided.")

            layers_to_delete = LayerProfile.objects.filter(id__in=ids)
            if not layers_to_delete.exists():
                return self.handle_not_found_error("No matching layers found.")

            # Check for group layers
            group_layers = layers_to_delete.filter(layer_type=LayerTypeChoices.GROUP)
            if group_layers.exists():
                return self.handle_permission_error(
                    f"Cannot delete GROUP layer(s): {list(group_layers.values_list('id', flat=True))}"
                )

            # Check permissions
            unauthorized_layers = []
            for layer in layers_to_delete:
                if not is_creator_on_layer(request.user, layer):
                    unauthorized_layers.append(layer.id)

            if unauthorized_layers:
                return self.handle_permission_error(
                    f"You do not have permission to delete the following layers: {unauthorized_layers}"
                )

            # Collect parent group IDs for cache invalidation
            parent_group_ids = set()
            for layer in layers_to_delete:
                if hasattr(layer, 'branchlayer'):
                    parent_group_ids.add(layer.branchlayer.subsidiary_layer.group_layer.id)
                elif hasattr(layer, 'subsidiarylayer'):
                    parent_group_ids.add(layer.subsidiarylayer.group_layer.id)

            count = layers_to_delete.count()
            layers_to_delete.delete()

            # Invalidate caches
            # Clear user-specific layer list caches
            for app_user in AppUser.objects.filter(user=request.user):
                cache_key = f'layer_list_{request.user.id}_None'
                cache.delete(cache_key)
                # Also clear any filtered caches
                for layer_type in ['GROUP', 'SUBSIDIARY', 'BRANCH']:
                    cache_key = f'layer_list_{request.user.id}_{layer_type}'
                    cache.delete(cache_key)
            
            # Invalidate parent group caches
            for group_id in parent_group_ids:
                cache_key = f'layer_detail_{group_id}_{request.user.id}'
                cache.delete(cache_key)

            return Response(
                {"message": f"Successfully deleted {count} layer(s)."},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return self.handle_unknown_error(e)

    def _add_creator_to_layer(self, request, layer):
        """Helper method to add creator to a new layer"""
        parent_layer = get_parent_layer(layer)
        creator_user = AppUser.objects.filter(
            layer=parent_layer,
            user__role=RoleChoices.CREATOR
        ).first()

        if not creator_user:
            raise ValidationError("Creator could not be determined for this layer.")

        return AppUser.objects.create(
            user=creator_user.user,
            name=request.data.get("name", creator_user.user.email.split("@")[0]),
            layer=layer,
        )

    def _add_users_to_layer(self, layer, app_users_data):
        """Helper method to add users to a layer"""
        from ..serializers import AppUserSerializer
        created_users = []

        for user_data in app_users_data:
            user_info = user_data.get("user", {})
            email = user_info.get("email")
            role = user_data.get("role", "OPERATION").upper()

            if not email:
                raise ValidationError("User email is required.")

            if AppUser.objects.filter(user__email=email, layer=layer).exists():
                raise ValidationError(f"User {email} already exists in this layer.")

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={"role": role, "is_active": True}
            )

            if created:
                password = CustomUser.objects.make_random_password()
                user.set_password(password)
                user.password_updated_at = None
                user.save()
                if not send_email_to_user(email, password):
                    raise ValidationError(f"Failed to send email to {email}.")

            app_user = AppUser.objects.create(
                user=user,
                name=user_data.get("name", email.split("@")[0]),
                layer=layer,
                title=user_data.get("title", "Member"),
            )
            created_users.append(app_user)

        return AppUserSerializer(created_users, many=True).data

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        """Export all layers as a CSV file"""
        try:
            group_layers = GroupLayer.objects.filter(app_users__user=request.user)
            subsidiary_layers = SubsidiaryLayer.objects.filter(app_users__user=request.user)
            branch_layers = BranchLayer.objects.filter(app_users__user=request.user)
            
            hkt_tz = pytz.timezone('Asia/Hong_Kong')
            response = HttpResponse(content_type="text/csv")

            if group_layers.exists():
                group = group_layers.first()
                filename = f"{group.company_name}_Company_Structure.csv"
            else:
                filename = "Company_Structure.csv"
            
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response["Access-Control-Expose-Headers"] = "Content-Disposition"

            writer = csv.writer(response)
            writer.writerow([
                "company_name", "company_industry", "shareholding_ratio", 
                "layer_type", "company_location", "created_at"
            ])

            for group in group_layers:
                group_hkt = group.created_at.astimezone(hkt_tz).strftime('%Y-%m-%d %H:%M') + "HKT"
                writer.writerow([
                    group.company_name,
                    group.company_industry,
                    group.shareholding_ratio,
                    LayerTypeChoices.GROUP,
                    group.company_location,
                    group_hkt,
                ])

                subs_for_group = subsidiary_layers.filter(group_layer=group)
                for subsidiary in subs_for_group:
                    subsidiary_hkt = subsidiary.created_at.astimezone(hkt_tz).strftime('%Y-%m-%d %H:%M') + "HKT"
                    writer.writerow([
                        subsidiary.company_name,
                        subsidiary.company_industry,
                        subsidiary.shareholding_ratio,
                        LayerTypeChoices.SUBSIDIARY,
                        subsidiary.company_location,
                        subsidiary_hkt,
                    ])

                    branches_for_subsidiary = branch_layers.filter(subsidiary_layer=subsidiary)
                    for branch in branches_for_subsidiary:
                        branch_hkt = branch.created_at.astimezone(hkt_tz).strftime('%Y-%m-%d %H:%M') + "HKT"
                        writer.writerow([
                            branch.company_name,
                            branch.company_industry,
                            branch.shareholding_ratio,
                            LayerTypeChoices.BRANCH,
                            branch.company_location,
                            branch_hkt,
                        ])

            return response
        except Exception as e:
            return self.handle_unknown_error(e)

    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        """Import layers from a CSV file"""
        try:
            file = request.FILES.get("file")
            if not file:
                return self.handle_validation_error("No file provided.")

            decoded_file = file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded_file)

            last_group_layer = None
            last_subsidiary_layer = None

            if request.user.is_superuser:
                with transaction.atomic():
                    for row in reader:
                        layer_type = row.get("layer_type")
                        creator_email = row.get("creator_email")

                        if not layer_type:
                            raise ValueError("Layer type is missing in the CSV row.")
                        if not creator_email:
                            raise ValueError("Creator email is missing in the CSV row.")

                        creator_user = CustomUser.objects.filter(email=creator_email).first()
                        if not creator_user:
                            raise ValueError(f"Creator with email {creator_email} not found.")

                        layer = self._create_layer_from_csv(
                            row, layer_type, creator_user, 
                            last_group_layer, last_subsidiary_layer
                        )
                        
                        if layer_type == "SUBSIDIARY":
                            last_subsidiary_layer = layer
                        
                        AppUser.objects.create(
                            user=creator_user,
                            name=request.data.get("name", creator_user.email.split("@")[0]),
                            layer=layer,
                            title="CEO"
                        )
            else:
                last_group_layer = GroupLayer.objects.filter(
                    app_users__user=request.user, 
                    app_users__user__role=RoleChoices.CREATOR
                ).order_by('-id').first()

                if not last_group_layer:
                    return self.handle_validation_error(
                        "No GROUP layer found for this user. Cannot import SUBSIDIARY or BRANCH layers."
                    )

                with transaction.atomic():
                    for row in reader:
                        layer_type = row.get("layer_type")
                        if not layer_type:
                            raise ValueError("Layer type is missing in the CSV row.")

                        layer = self._create_layer_from_csv(
                            row, layer_type, request.user, 
                            last_group_layer, last_subsidiary_layer
                        )
                        
                        if layer_type == "SUBSIDIARY":
                            last_subsidiary_layer = layer

                        AppUser.objects.create(
                            user=request.user,
                            name=request.data.get("name", request.user.email.split("@")[0]),
                            layer=layer,
                            title="CEO"
                        )

            return Response(
                {"message": "Layers imported successfully."}, 
                status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return self.handle_validation_error(str(e))
        except Exception as e:
            return self.handle_unknown_error(e)

    def _create_layer_from_csv(self, row, layer_type, user, last_group_layer, last_subsidiary_layer):
        """Helper method to create a layer from CSV data"""
        if layer_type == "SUBSIDIARY":
            if not last_group_layer:
                last_group_layer = GroupLayer.objects.filter(
                    app_users__user=user,
                    app_users__user__role=RoleChoices.CREATOR
                ).order_by('-id').first()

            if not last_group_layer:
                raise ValueError(f"No GROUP layer found for creator {user.email}.")

            subsidiary = SubsidiaryLayer.objects.create(
                company_name=row["company_name"],
                company_industry=row["company_industry"],
                shareholding_ratio=float(row["shareholding_ratio"]),
                group_layer=last_group_layer,
                layer_type=LayerTypeChoices.SUBSIDIARY,
                company_location=row["company_location"]
            )
            
            # Set the creator
            subsidiary.created_by_admin = user
            subsidiary.save()
            
            return subsidiary

        elif layer_type == "BRANCH":
            if not last_subsidiary_layer:
                raise ValueError("Cannot create BRANCH without a preceding SUBSIDIARY layer.")

            branch = BranchLayer.objects.create(
                company_name=row["company_name"],
                company_industry=row["company_industry"],
                shareholding_ratio=float(row["shareholding_ratio"]),
                subsidiary_layer=last_subsidiary_layer,
                layer_type=LayerTypeChoices.BRANCH,
                company_location=row["company_location"]
            )
            
            # Set the creator
            branch.created_by_admin = user
            branch.save()
            
            return branch
        else:
            raise ValueError(f"Invalid layer type: {layer_type}")

    @action(detail=False, methods=['get'], url_path='download-example')
    def download_example(self, request):
        """Download CSV template for layer import"""
        try:
            template_type = 'superuser' if request.user.is_superuser else 'default'
            
            try:
                template = CSVTemplate.objects.get(template_type=template_type)
            except CSVTemplate.DoesNotExist:
                template = None

            if template and template.file:
                download_url = template.file.url
            else:
                output = io.StringIO()
                writer = csv.writer(output)
                if template_type == 'superuser':
                    writer.writerow([
                        'company_name',
                        'company_industry',
                        'shareholding_ratio',
                        'layer_type',
                        'company_location',
                        'creator_email'
                    ])
                    file_name = 'Company_Structure_Template_For_Superuser.csv'
                else:
                    writer.writerow([
                        'company_name',
                        'company_industry',
                        'shareholding_ratio',
                        'layer_type',
                        'company_location'
                    ])
                    file_name = 'Company_Structure_Template.csv'
                csv_content = output.getvalue()
                output.close()
                default_storage.save(file_name, ContentFile(csv_content.encode('utf-8')))
                template = CSVTemplate.objects.create(template_type=template_type, file=file_name)
                download_url = template.file.url

            return Response({"download_url": download_url}, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_unknown_error(e)

    def partial_update(self, request, pk=None):
        """Partially update a layer"""
        try:
            layer = LayerProfile.objects.get(id=pk, app_users__user=request.user)
        except LayerProfile.DoesNotExist:
            return self.handle_not_found_error("Layer not found or you do not have access to it.")

        try:
            if hasattr(layer, "grouplayer"):
                serializer_class = GroupLayerSerializer
                layer_instance = layer.grouplayer
            elif hasattr(layer, "subsidiarylayer"):
                serializer_class = SubsidiaryLayerSerializer
                layer_instance = layer.subsidiarylayer
            elif hasattr(layer, "branchlayer"):
                serializer_class = BranchLayerSerializer
                layer_instance = layer.branchlayer
            else:
                return self.handle_validation_error("Layer type not recognized.")

            serializer = serializer_class(layer_instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                
                # Invalidate relevant caches
                # Clear layer detail cache
                cache_key = f'layer_detail_{pk}_{request.user.id}'
                cache.delete(cache_key)
                
                # Clear layer list caches
                cache_key = f'layer_list_{request.user.id}_None'
                cache.delete(cache_key)
                
                # Also clear filtered cache for this layer type
                cache_key = f'layer_list_{request.user.id}_{layer.layer_type}'
                cache.delete(cache_key)
                
                # If this is a subsidiary or branch, invalidate parent group's cache
                parent_layer_id = None
                if hasattr(layer, 'branchlayer'):
                    parent_layer_id = layer.branchlayer.subsidiary_layer.group_layer.id
                elif hasattr(layer, 'subsidiarylayer'):
                    parent_layer_id = layer.subsidiarylayer.group_layer.id
                    
                if parent_layer_id:
                    cache_key = f'layer_detail_{parent_layer_id}_{request.user.id}'
                    cache.delete(cache_key)
                
                return Response(serializer.data, status=status.HTTP_200_OK)
            return self.handle_validation_error(serializer.errors)
            
        except Exception as e:
            return self.handle_unknown_error(e)

    # ... Add other methods (create, destroy, etc.) following the same pattern
    # The file is getting long, so I'll continue with the rest in subsequent messages 
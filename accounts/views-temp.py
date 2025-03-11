import csv, json, io, pytz
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError

from .serializers import (
    CustomUserSerializer,
    LayerProfileSerializer,
    GroupLayerSerializer,
    SubsidiaryLayerSerializer,
    BranchLayerSerializer,
    AppUserSerializer
)
from .models import LayerProfile, AppUser, GroupLayer, SubsidiaryLayer, BranchLayer, LayerTypeChoices, RoleChoices, CustomUser, CSVTemplate
from .services import send_email_to_user, has_permission_to_manage_users, get_accessible_layers, is_creator_on_layer, get_parent_layer, generate_otp_code, send_otp_via_email, get_flat_sorted_layers
from .permissions import CanManageAppUsers

class RegisterLayerProfileView(APIView):
    """
    API endpoint for registering a user and a GroupLayer.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        user_data = request.data.get("user")
        group_layer_data = request.data.get("group_layer")

        if not user_data or not group_layer_data:
            return Response(
                {"error": "User data and group layer data are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user_data["is_active"] = False
            user_data["must_change_password"] = False
            user_serializer = CustomUserSerializer(data=user_data)
            if user_serializer.is_valid():
                user = user_serializer.save()
            else:
                return Response(
                    {"error": user_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            group_layer_serializer = GroupLayerSerializer(data=group_layer_data)
            if group_layer_serializer.is_valid():
                group_layer = group_layer_serializer.save()

                AppUser.objects.create(
                    user=user,
                    name=user_data.get("name", user.email.split("@")[0]),
                    layer=group_layer,
                    title=user_data.get("title", "CEO"),
                )
            else:
                return Response(
                    {"error": group_layer_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        otp_code = generate_otp_code()
        user.otp_code = otp_code
        user.otp_created_at = timezone.now()
        user.save()

        send_otp_via_email(user.email, otp_code)
    
        return Response(
            {
                "message": "User and Group Layer created successfully. Check email for OTP.",
                "user": user_serializer.data,
                "group_layer": group_layer_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

class LayerProfileViewSet(ViewSet):
    """
    A ViewSet for managing layers (GroupLayer, SubsidiaryLayer, BranchLayer).
    Provides CRUD operations, bulk operations, and import/export functionality.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    @method_decorator(vary_on_cookie)
    def list(self, request):
        """
        List all layers accessible to the user in a flat list but ordered hierarchically.
        Results are cached for 5 minutes per user.
        """
        user = request.user
        layer_type_filter = request.query_params.get("layer_type")
        
        # Cache key includes user ID and filter for unique caching
        cache_key = f'layer_list_{user.id}_{layer_type_filter}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return Response(cached_result)

        accessible_layers = get_accessible_layers(user)

        if layer_type_filter:
            filter_types = [ft.strip().upper() for ft in layer_type_filter.split(',') if ft.strip()]
            valid_types = {choice.value for choice in LayerTypeChoices}

            invalid_types = [ft for ft in filter_types if ft not in valid_types]
            if invalid_types:
                return Response(
                    {"error": f"Invalid layer_type(s): {', '.join(invalid_types)}. Must be one of: {', '.join(valid_types)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            filtered_layers = accessible_layers.filter(layer_type__in=filter_types).distinct()
            result = get_flat_sorted_layers(filtered_layers)
        else:
            result = get_flat_sorted_layers(accessible_layers)

        # Cache the result
        cache.set(cache_key, result, timeout=60 * 5)
        return Response(result)

    def retrieve(self, request, pk=None):
        """
        Retrieve a specific layer by its ID, with caching for 5 minutes.
        """
        user = request.user
        cache_key = f'layer_detail_{pk}_{user.id}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return Response(cached_result)

        accessible_layers = get_accessible_layers(user)

        try:
            layer = accessible_layers.get(id=pk)
        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found or you do not have access to it."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if hasattr(layer, "grouplayer"):
            serializer = GroupLayerSerializer(layer.grouplayer)
        elif hasattr(layer, "subsidiarylayer"):
            serializer = SubsidiaryLayerSerializer(layer.subsidiarylayer)
        elif hasattr(layer, "branchlayer"):
            serializer = BranchLayerSerializer(layer.branchlayer)
        else:
            return Response(
                {"error": "Layer type not recognized."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cache the result
        cache.set(cache_key, serializer.data, timeout=60 * 5)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="users")
    def get_users(self, request, pk=None):
        """
        Get all users associated with a specific layer by its ID,
        excluding users with the CREATOR role.
        """
        try:
            layer = LayerProfile.objects.get(id=pk)

            if not has_permission_to_manage_users(request.user, layer):
                return Response(
                    {"error": "You do not have permission to access users for this layer."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if layer.layer_type == 'GROUP':
                app_users = layer.app_users.all()
            else:
                app_users = AppUser.objects.filter(layer=layer).exclude(user__role=RoleChoices.CREATOR)

            serializer = AppUserSerializer(app_users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
    
    def create(self, request):
        """
        Create a new layer (SubsidiaryLayer or BranchLayer) based on layer_type.
        """
        try:
            layer_type = request.data.get("layer_type")
            app_users_data = request.data.get("app_users", [])
            
            if not layer_type:
                return Response(
                    {"error": "Layer type is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                creator_user = None

                if layer_type == "SUBSIDIARY":
                    group_id = request.data.get("group_id")
                    if not group_id:
                        return Response(
                            {"error": "Group ID is required for a Subsidiary Layer."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    try:
                        group_layer = GroupLayer.objects.get(id=group_id)
                    except GroupLayer.DoesNotExist:
                        return Response(
                            {"error": "Group Layer not found."},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                    if not is_creator_on_layer(request.user, group_layer):
                        raise PermissionDenied("You do not have permission to create a subsidiary layer for this group layer.")

                    serializer = SubsidiaryLayerSerializer(data=request.data, context={"group_layer": group_layer})

                elif layer_type == "BRANCH":
                    subsidiary_id = request.data.get("subsidiary_id")
                    if not subsidiary_id:
                        return Response(
                            {"error": "Subsidiary ID is required for a Branch Layer."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    try:
                        subsidiary_layer = SubsidiaryLayer.objects.get(id=subsidiary_id)
                    except SubsidiaryLayer.DoesNotExist:
                        return Response(
                            {"error": "Subsidiary Layer not found."},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                    if not is_creator_on_layer(request.user, subsidiary_layer):
                        raise PermissionDenied("You do not have permission to create a branch layer for this subsidiary layer.")

                    serializer = BranchLayerSerializer(data=request.data, context={"subsidiary_layer": subsidiary_layer})

                else:
                    return Response(
                        {"error": "Invalid layer type. Only SUBSIDIARY or BRANCH layers can be created."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                layer = serializer.save()

                # Assign the creator user to the new layer
                parent_layer = get_parent_layer(layer)
                creator_user = AppUser.objects.filter(layer=parent_layer, user__role=RoleChoices.CREATOR).first()
                if not creator_user:
                    raise ValidationError("Creator could not be determined for this layer.")

                AppUser.objects.create(
                    user=creator_user.user,
                    name=request.data.get("name", creator_user.user.email.split("@")[0]),
                    layer=layer,
                )

                # Create additional users if provided
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

                return Response(
                    {
                        "layer": serializer.data,
                        "created_users": AppUserSerializer(created_users, many=True).data
                    },
                    status=status.HTTP_201_CREATED
                )

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """
        Delete a layer only if its layer_type is not GROUP and the user has MANAGEMENT role.
        """
        try:
            layer = LayerProfile.objects.get(id=pk, app_users__user=request.user)

            if layer.layer_type == LayerTypeChoices.GROUP:
                return Response(
                    {"error": "Cannot delete a layer with layer_type GROUP."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            app_user = AppUser.objects.filter(user=request.user, layer=layer).first()
            if not app_user or app_user.role != RoleChoices.CREATOR:
                print(f'app_user:{app_user}')
                return Response(
                    {"error": "You do not have permission to delete this layer."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            layer.delete()
            return Response(
                {"message": "Layer deleted successfully."}, status=status.HTTP_204_NO_CONTENT
            )

        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found or you do not have access to it."},
                status=status.HTTP_404_NOT_FOUND,
            )
    
    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """
        Delete multiple layers in bulk, ensuring the user has the necessary permissions.
        Only a CREATOR can delete layers, and each layer must be validated individually.
        """
        ids = request.data.get("ids", [])
        
        if isinstance(ids, str):
            try:
                ids = json.loads(ids)
            except json.JSONDecodeError:
                raise ValidationError({"ids": "Invalid format. Expected a list or JSON array."})

        if not isinstance(ids, list) or not ids:
            return Response({"error": "No layer IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        layers_to_delete = LayerProfile.objects.filter(id__in=ids)

        if not layers_to_delete.exists():
            return Response({"error": "No matching layers found."}, status=status.HTTP_404_NOT_FOUND)

        group_layers = layers_to_delete.filter(layer_type=LayerTypeChoices.GROUP)
        if group_layers.exists():
            return Response(
                {
                    "error": "Cannot delete GROUP layer(s).",
                    "group_layer_ids": list(group_layers.values_list("id", flat=True)),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        
        unauthorized_layers = []
        for layer in layers_to_delete:
            if not is_creator_on_layer(request.user, layer):
                unauthorized_layers.append(layer.id)

        if unauthorized_layers:
            return Response(
                {"error": f"You do not have permission to delete the following layers: {unauthorized_layers}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        count = layers_to_delete.count()
        layers_to_delete.delete()

        return Response(
            {"message": f"Successfully deleted {count} layer(s)."},
            status=status.HTTP_200_OK,
        )


    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        """
        Export all layers as a CSV file in a format matching the import structure.
        """
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
            "company_name", "company_industry", "shareholding_ratio", "layer_type", "company_location", "created_at"
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
    
    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        """
        Import layers from a CSV file with hierarchical structure.
        """
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded_file)

            last_group_layer = None
            last_subsidary_layer = None

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

                        if layer_type == "SUBSIDIARY":
                            if not last_group_layer:
                                last_group_layer = GroupLayer.objects.filter(
                                    app_users__user=creator_user,
                                    app_users__user__role=RoleChoices.CREATOR
                                ).order_by('-id').first()

                            if not last_group_layer:
                                raise ValueError(f"No GROUP layer found for creator {creator_email}.")

                            last_subsidiary_layer = SubsidiaryLayer.objects.create(
                                company_name=row["company_name"],
                                company_industry=row["company_industry"],
                                shareholding_ratio=float(row["shareholding_ratio"]),
                                group_layer=last_group_layer,
                                layer_type=LayerTypeChoices.SUBSIDIARY,
                                company_location=row["company_location"]
                            )
                            layer = last_subsidiary_layer

                        elif layer_type == "BRANCH":
                            if not last_subsidary_layer:
                                raise ValueError("Cannot create BRANCH without a preceding SUBSIDIARY layer.")

                            layer = BranchLayer.objects.create(
                                company_name=row["company_name"],
                                company_industry=row["company_industry"],
                                shareholding_ratio=float(row["shareholding_ratio"]),
                                subsidary_layer=last_subsidary_layer,
                                layer_type=LayerTypeChoices.BRANCH,
                                company_location=row["company_location"]
                            )
                        else:
                            raise ValueError(f"Invalid layer type: {layer_type}")

                        AppUser.objects.create(
                            user=creator_user,
                            name=request.data.get("name", creator_user.email.split("@")[0]),
                            layer=layer,
                            title="CEO"
                        )

            else:
                last_group_layer = GroupLayer.objects.filter(
                    app_users__user=request.user, app_users__user__role=RoleChoices.CREATOR
                ).order_by('-id').first()

                if not last_group_layer:
                    return Response(
                        {"error": "No GROUP layer found for this user. Cannot import SUBSIDIARY or BRANCH layers."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                with transaction.atomic():
                    for row in reader:
                        layer_type = row.get("layer_type")
                        if not layer_type:
                            raise ValueError("Layer type is missing in the CSV row.")

                        if layer_type == "SUBSIDIARY":
                            last_subsidary_layer = SubsidiaryLayer.objects.create(
                                company_name=row["company_name"],
                                company_industry=row["company_industry"],
                                shareholding_ratio=float(row["shareholding_ratio"]),
                                group_layer=last_group_layer,
                                layer_type=LayerTypeChoices.SUBSIDIARY,
                                company_location=row["company_location"]
                            )
                            layer = last_subsidary_layer

                        elif layer_type == "BRANCH":
                            if not last_subsidary_layer:
                                raise ValueError("Cannot create BRANCH without a preceding SUBSIDIARY layer.")

                            layer = BranchLayer.objects.create(
                                company_name=row["company_name"],
                                company_industry=row["company_industry"],
                                shareholding_ratio=float(row["shareholding_ratio"]),
                                subsidary_layer=last_subsidary_layer,
                                layer_type=LayerTypeChoices.BRANCH,
                                company_location=row["company_location"]
                            )

                        else:
                            raise ValueError(f"Invalid layer type: {layer_type}")

                        AppUser.objects.create(
                            user=request.user,
                            name=request.data.get("name", request.user.email.split("@")[0]),
                            layer=layer,
                            title="CEO"
                        )

            return Response({"message": "Layers imported successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='download-example')
    def download_example(self, request):
        """
        Returns a link for downloading the CSV template.
        If a modified file exists in the CSVTemplate table for the appropriate user type,
        that file is returned. Otherwise, a default template with only the header is created and returned.
        """
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
    
    def partial_update(self, request, pk=None):
        """
        Partially update a specific layer by its ID.
        """
        try:
            layer = LayerProfile.objects.get(id=pk, app_users__user=request.user)
        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found or you do not have access to it."},
                status=status.HTTP_404_NOT_FOUND,
            )

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
            return Response(
                {"error": "Layer type not recognized."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = serializer_class(layer_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AppUserViewSet(ModelViewSet):
    """
    A ViewSet for managing AppUser instances.
    """
    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer
    permission_classes = [IsAuthenticated, CanManageAppUsers]
    parser_classes = [MultiPartParser, JSONParser]
    
    def partial_update(self, request, pk=None):
        try:
            app_user = AppUser.objects.get(id=pk)
            self.check_object_permissions(request, app_user)
        except AppUser.DoesNotExist:
            return Response({"error": "AppUser not found."}, status=404)

        serializer = AppUserSerializer(app_user, data=request.data, partial=True)
        if serializer.is_valid():
            user_data = request.data.get("user", {})
            new_email = user_data.get("email")
            
            if new_email and new_email != app_user.user.email:
                if CustomUser.objects.exclude(pk=app_user.user.pk).filter(email=new_email).exists():
                    return Response({"error": "Email is already in use by another user."}, status=400)
                
                otp_code = generate_otp_code()
                app_user.user.otp_code = otp_code
                app_user.user.otp_created_at = timezone.now()
                app_user.user.is_active = False
                app_user.user.email = new_email
                app_user.user.save()
                
                send_otp_via_email(new_email, otp_code)

            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)
    
    @action(detail=True, methods=["post"], url_path="add-user")
    def add_user(self, request, pk=None):
        """
        Add a new user to the specified layer.
        """
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)
        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        non_creator_count = AppUser.objects.filter(layer=layer).exclude(user__role="CREATOR").count()
        if non_creator_count >= 5:
            return Response(
                {"error": "Maximum number of users (5) for this layer has been reached."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email=request.data.get("user")['email']
        role = request.data.get("role").upper()
        if not email:
            return Response(
                {"error": "Email is required to add a user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = CustomUser.objects.filter(email=email).first()
        if not user:
            password = CustomUser.objects.make_random_password()
            user = CustomUser.objects.create_user(email=email, password=password, role=role, is_active=True, password_updated_at = None)

            if not send_email_to_user(email, password):
                return Response(
                    {"error": "Failed to send email to the user."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        if AppUser.objects.filter(user=user, layer=layer).exists():
            return Response(
                {"error": "User already exists in this layer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app_user = AppUser.objects.create(
            user=user,
            name=request.data.get("name", user.email.split("@")[0]),
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
    
    @action(detail=True, methods=["post"], url_path="resend-email")
    def resend_email(self, request, pk=None):
        """
        Resend login credentials email to a user already added to the specified layer.
        """
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)
        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required to resend credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            app_user = AppUser.objects.get(layer=layer, user__email=email)
        except AppUser.DoesNotExist:
            return Response(
                {"error": "User not found in this layer."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = app_user.user

        new_password = CustomUser.objects.make_random_password()
        user.set_password(new_password)
        user.password_updated_at = None
        user.save()

        if not send_email_to_user(user.email, new_password):
            return Response(
                {"error": "Failed to send email to the user."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Email with login credentials has been sent successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request, pk=None):
        """
        Bulk delete AppUsers for a specific layer.
        The request body should contain a list of user IDs to delete.
        """
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)
        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_ids = request.data.get("ids", [])

        if isinstance(user_ids, str):
            try:
                user_ids = json.loads(user_ids)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid format. Expected a list or JSON array."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not isinstance(user_ids, list) or not user_ids:
            return Response(
                {"error": "No user IDs provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        users_to_delete = AppUser.objects.filter(layer=layer, id__in=user_ids)

        if not users_to_delete.exists():
            return Response(
                {"error": "No matching AppUsers found for deletion."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        creator_users = users_to_delete.filter(user__role=RoleChoices.CREATOR)
        if creator_users.exists():
            return Response(
                {"error": "You can't delete user with CREATOR role."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            custom_user_ids = list(users_to_delete.values_list('user_id', flat=True).distinct())
            count = users_to_delete.count()
            
            users_to_delete.delete()
            
            for user_id in custom_user_ids:
                if not AppUser.objects.filter(user_id=user_id).exists():
                    CustomUser.objects.filter(id=user_id).delete()

        return Response(
            {"message": f"Successfully deleted {count} user(s) from layer {layer.id}."},
            status=status.HTTP_200_OK,
        )
    
    @action(detail=False, methods=['get'], url_path=r'download-example')
    def download_app_users_template(self, request):
        """
        Returns a link for downloading the CSV template for app users for a specific layer.
        If a modified file exists in the CSVTemplate table for the app user template, that file is returned.
        Otherwise, a default template with only the header is created and returned.
        The template header is: email,name,title,role.
        """
        template_type = 'appuser'
        file_name = f'User_Create_Template.csv'
        
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
            # Save the file in storage with the constructed file name
            default_storage.save(file_name, ContentFile(csv_content.encode('utf-8')))
            template = CSVTemplate.objects.create(template_type=template_type, file=file_name)
            download_url = template.file.url

        return Response({"download_url": download_url}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="import-csv")
    def import_csv(self, request, pk=None):
        """
        Import AppUsers from a CSV file for a specific layer.
        The CSV should have columns: email, name, title, role.
        """
        try:
            layer = LayerProfile.objects.get(id=pk)
            self.check_object_permissions(request, layer)
        except LayerProfile.DoesNotExist:
            return Response(
                {"error": "Layer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
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

                    user = CustomUser.objects.filter(email=email).first()
                    if not user:
                        password = CustomUser.objects.make_random_password()
                        user = CustomUser.objects.create_user(email=email, password=password, role=role, password_updated_at = None)

                        if not send_email_to_user(email, password):
                            raise ValueError(f"Failed to send email to {email}.")

                    if AppUser.objects.filter(user=user, layer=layer).exists():
                        continue

                    app_user = AppUser.objects.create(
                        user=user,
                        name=name,
                        title=title,
                        layer=layer,
                    )
                    created_users.append(app_user)

            serializer = AppUserSerializer(created_users, many=True)
            return Response(
                {
                    "message": "Users imported successfully.",
                    "created_users": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred while importing users: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=True, methods=['get'], url_path='export-csv')
    def export_csv(self, request, pk=None):
        """
        Exports AppUsers as a CSV file for a specific layer.
        The CSV file contains the columns: email, name, title, role.
        """
        try:
            layer = LayerProfile.objects.get(id=pk)
        except LayerProfile.DoesNotExist:
            return Response({"error": "Layer not found."}, status=status.HTTP_404_NOT_FOUND)

        app_users = AppUser.objects.filter(layer=layer)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{layer.company_name}_User_Accounts.csv"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"

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


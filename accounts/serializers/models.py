import pytz
from rest_framework import serializers
from django.utils import timezone
from django.db.models import Count
from ..models import CustomUser, AppUser, LayerProfile, GroupLayer, SubsidiaryLayer, BranchLayer, RoleChoices
from ..utils import validate_password

class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomUser model with role validation and password handling
    """
    role = serializers.CharField(required=False)
    is_superuser = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "email", "password", "role", "is_superuser", "must_change_password"]
        extra_kwargs = {
            "email": {"validators": []},  # Custom email validation in update method
            "password": {"write_only": True},  # Password should never be read
        }
        
    def get_is_superuser(self, obj):
        return obj.is_superuser
        
    def validate_role(self, value):
        """Validate and normalize role value"""
        if not value:
            return value
        role_up = value.upper()

        valid_roles = [RoleChoices.CREATOR, RoleChoices.MANAGEMENT, RoleChoices.OPERATION]
        if role_up not in valid_roles:
            raise serializers.ValidationError(f"Role '{value}' is invalid. Must be one of {valid_roles}.")

        return role_up
    
    def validate_password(self, value):
        """Validate password using centralized validation"""
        user = self.instance if self.instance else None
        return validate_password(value, user)

    def create(self, validated_data):
        """Create new user with proper password hashing"""
        password = validated_data.pop("password", None)
        user = CustomUser(**validated_data)

        if password:
            user.set_password(password)
        else:
            raise serializers.ValidationError("Password is required!")

        user.save()
        return user

    def update(self, instance, validated_data):
        """Update user with email uniqueness check"""
        new_email = validated_data.get("email", instance.email)

        if new_email != instance.email:
            if CustomUser.objects.exclude(pk=instance.pk).filter(email=new_email).exists():
                raise serializers.ValidationError(
                    {"email": ["Email is already in use by another user."]}
                )
            instance.email = new_email

        new_password = validated_data.get("password")
        if new_password:
            instance.set_password(new_password)

        new_role = validated_data.get("role")
        if new_role:
            instance.role = new_role

        instance.save()
        return instance

class AppUserSerializer(serializers.ModelSerializer):
    """
    Serializer for AppUser model with nested CustomUser data
    """
    user = CustomUserSerializer()
    role = serializers.CharField(source="user.role", required=False)

    class Meta:
        model = AppUser
        fields = ["id", "user", "name", "title", "role"]

    def update(self, instance, validated_data):
        """Handle nested user data updates"""
        user_data = validated_data.pop("user", None)
        instance = super().update(instance, validated_data)

        if user_data:
            user_serializer = CustomUserSerializer(
                instance=instance.user, 
                data=user_data, 
                partial=True
            )
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        return instance

class LayerProfileSerializer(serializers.ModelSerializer):
    """
    Base serializer for company layer hierarchy with optimized queries
    """
    app_users = serializers.SerializerMethodField()
    user_count = serializers.IntegerField(read_only=True)  # Use annotated value
    created_at = serializers.SerializerMethodField()
    parent_id = serializers.SerializerMethodField()

    class Meta:
        model = LayerProfile
        fields = [
            "id",
            "company_name",
            "company_industry",
            "shareholding_ratio",
            "app_users",
            "user_count",
            "layer_type",
            "company_location",
            "created_at",
            "parent_id"
        ]

    def get_app_users(self, obj):
        """Get users, excluding creators for non-group layers"""
        # Use prefetched data
        if hasattr(obj, 'prefetched_app_users'):
            app_users = obj.prefetched_app_users
            if obj.layer_type != 'GROUP':
                app_users = [au for au in app_users if au.user.role != "CREATOR"]
        else:
            # Fallback to regular querying if not prefetched
            if obj.layer_type == 'GROUP':
                app_users = obj.app_users.all()
            else:
                app_users = obj.app_users.exclude(user__role="CREATOR")
        
        return AppUserSerializer(app_users, many=True).data

    def get_created_at(self, obj):
        """Format creation time in Hong Kong timezone with creator info"""
        hkt_tz = pytz.timezone('Asia/Hong_Kong')
        hkt_time = obj.created_at.astimezone(hkt_tz)
        
        # Use prefetched data if available
        if hasattr(obj, 'prefetched_app_users'):
            creator_app_user = next(
                (au for au in obj.prefetched_app_users if au.user.role == "CREATOR"),
                None
            )
        else:
            creator_app_user = obj.app_users.filter(user__role="CREATOR").first()
            
        creator = creator_app_user.name if creator_app_user else "Unknown"
        return f"{hkt_time.strftime('%Y-%m-%d %H:%M')}HKT by {creator}"

    def get_parent_id(self, obj):
        """Get the ID of the parent layer"""
        try:
            if obj.layer_type == 'SUBSIDIARY' and hasattr(obj, 'subsidiarylayer'):
                return obj.subsidiarylayer.group_layer_id
            elif obj.layer_type == 'BRANCH' and hasattr(obj, 'branchlayer'):
                return obj.branchlayer.subsidiary_layer_id
            return None
        except Exception:
            return None

class GroupLayerSerializer(LayerProfileSerializer):
    """Serializer for top-level company groups"""
    class Meta:
        model = GroupLayer
        fields = LayerProfileSerializer.Meta.fields
        
    def create(self, validated_data):
        return GroupLayer.objects.create(**validated_data)

class SubsidiaryLayerSerializer(LayerProfileSerializer):
    """Serializer for subsidiary companies with group relationship"""
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=GroupLayer.objects.all(), 
        source="group_layer"
    )

    class Meta:
        model = SubsidiaryLayer
        fields = LayerProfileSerializer.Meta.fields + ["group_id"]

    def create(self, validated_data):
        group_layer = validated_data.pop("group_layer")
        subsidiary_layer = SubsidiaryLayer.objects.create(
            group_layer=group_layer, 
            **validated_data
        )
        return subsidiary_layer

class BranchLayerSerializer(LayerProfileSerializer):
    """Serializer for branch offices with subsidiary relationship"""
    subsidiary_id = serializers.PrimaryKeyRelatedField(
        queryset=SubsidiaryLayer.objects.all(),
        source="subsidiary_layer"
    )

    class Meta:
        model = BranchLayer
        fields = LayerProfileSerializer.Meta.fields + ["subsidiary_id"]

    def create(self, validated_data):
        subsidiary_layer = validated_data.pop("subsidiary_layer")
        branch_layer = BranchLayer.objects.create(
            subsidiary_layer=subsidiary_layer, 
            **validated_data
        )
        return branch_layer 
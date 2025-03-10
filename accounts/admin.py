from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, CompanyLayer

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 
                   'is_management', 'is_operation', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('User Role', {'fields': ('is_management', 'is_operation', 'phone_number')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)

class CompanyLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'layer_type', 'parent')
    list_filter = ('layer_type',)
    search_fields = ('name',)

admin.site.register(CompanyLayer, CompanyLayerAdmin)

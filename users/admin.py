from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser

class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'name', 'is_staff', 'is_verified', 'is_active', 'created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser', 'is_verified'),
        }),
    )
    
    search_fields = ['email']

admin.site.register(CustomUser, UserAdmin)
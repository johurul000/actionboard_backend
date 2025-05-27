from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser

class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = [
        'email', 'first_name', 'last_name', 'is_staff', 'is_verified', 'is_active', 'created_at'
    ]
    
    readonly_fields = ['created_at', 'last_login']  # added here

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name', 'country', 'date_of_birth')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at')}),  # keep in display but readonly
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'country', 'date_of_birth',
                'password1', 'password2', 'is_active', 'is_staff', 'is_superuser', 'is_verified'
            ),
        }),
    )
    
    search_fields = ['email', 'first_name', 'last_name']

admin.site.register(CustomUser, UserAdmin)


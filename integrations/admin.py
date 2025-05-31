from django.contrib import admin
from .models import OAuthToken, ZoomProfile

@admin.register(OAuthToken)
class OAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'expires_at')
    list_filter = ('provider',)
    search_fields = ('user__email',)

@admin.register(ZoomProfile)
class ZoomProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'zoom_user_id', 'zoom_email', 'zoom_account_id', 'last_synced_at', 'created_at', 'updated_at')
    search_fields = ('user__email', 'zoom_email', 'zoom_user_id', 'zoom_account_id')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'oauth_token')

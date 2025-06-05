from django.contrib import admin
from .models import OAuthToken, ZoomProfile

@admin.register(OAuthToken)
class OAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'organisation', 'provider', 'expires_at', 'created_at')
    list_filter = ('provider', 'organisation__name')
    search_fields = ('organisation__name', 'provider')
    readonly_fields = ('created_at',)


@admin.register(ZoomProfile)
class ZoomProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'zoom_email', 'organisation', 'zoom_user_id', 'zoom_account_id', 'last_synced_at')
    search_fields = ('zoom_email', 'zoom_user_id', 'organisation__name')
    list_filter = ('organisation__name',)
    readonly_fields = ('created_at', 'updated_at', 'last_synced_at')

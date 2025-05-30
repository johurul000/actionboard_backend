from django.contrib import admin
from .models import OAuthToken

@admin.register(OAuthToken)
class OAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'expires_at')
    list_filter = ('provider',)
    search_fields = ('user__email',)


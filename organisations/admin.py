from django.contrib import admin
from .models import Organisation, OrganisationMembership

@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by')
    search_fields = ('name',)
    list_filter = ('created_by',)

@admin.register(OrganisationMembership)
class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organisation', 'role')
    list_filter = ('organisation', 'role')
    search_fields = ('user__email', 'organisation__name')
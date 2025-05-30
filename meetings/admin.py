from django.contrib import admin
from .models import Meeting, MeetingAttendee

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('topic', 'organisation', 'status')  # corrected spelling
    list_filter = ('organisation', 'status')  # corrected spelling
    search_fields = ('topic', 'organisation__name')  # corrected spelling

@admin.register(MeetingAttendee)
class MeetingAttendeeAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'name', 'email', 'duration')
    list_filter = ('meeting',)
    search_fields = ('name', 'email', 'meeting__title')

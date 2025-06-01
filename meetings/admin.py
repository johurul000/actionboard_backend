from django.contrib import admin
from .models import Meeting, MeetingAttendee, Recording

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('topic', 'start_time', 'end_time', 'status', 'recording_ready')
    search_fields = ('topic', 'meeting_id')
    list_filter = ('status', 'recording_ready')

@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ('recording_id', 'meeting', 'file_type', 'file_size', 'recording_start', 'recording_end')
    search_fields = ('recording_id', 'meeting__topic')
    list_filter = ('file_type', 'recording_type')
    
@admin.register(MeetingAttendee)
class MeetingAttendeeAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'name', 'email', 'duration')
    list_filter = ('meeting',)
    search_fields = ('name', 'email', 'meeting__title')

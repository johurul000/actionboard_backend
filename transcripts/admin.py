from django.contrib import admin
from .models import Transcript, ActionItem

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'language', 'created_at')
    list_filter = ('language',)
    search_fields = ('meeting__title',)

@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'assigned_to', 'content', 'due_date', 'status')
    list_filter = ('status', 'due_date')
    search_fields = ('content', 'assigned_to__email')

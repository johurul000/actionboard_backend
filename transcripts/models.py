from django.db import models

# Create your models here.
class Transcript(models.Model):
    meeting = models.OneToOneField('meetings.Meeting', on_delete=models.CASCADE, related_name='transcript')
    full_transcript = models.TextField()
    summary = models.JSONField(help_text="Structured summary: attendees, decisions, action_items")
    utterances = models.JSONField(blank=True, null=True, help_text="List of utterance blocks with speaker, time, text")
    cohere_insights = models.JSONField(blank=True, null=True, help_text="Insights or output from Cohere AI")
    language = models.CharField(max_length=50, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    speakers_updated = models.BooleanField(default=False)
    speaker_map = models.JSONField(blank=True, null=True, help_text="Mapping of speaker codes to human names")

    def __str__(self):
        return f"Transcript for {self.meeting.topic}"
    
    
class ActionItem(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('done', 'Done'),
    )

    meeting = models.ForeignKey('meetings.Meeting', on_delete=models.CASCADE, related_name='action_items')
    assigned_to = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    content = models.TextField()
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reminder_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content
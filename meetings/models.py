from django.db import models

# Create your models here.
class Meeting(models.Model):
    STATUS_CHOICES = (
        ('uploaded', 'Uploaded'),
        ('transcribed', 'Transcribed'),
        ('summarized', 'Summarized'),
    )

    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='meetings')
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='created_meetings')

    title = models.CharField(max_length=255)
    video_url = models.URLField(blank=True, null=True)  # OR use FileField if uploading
    external_meeting_id = models.CharField(max_length=255, blank=True, null=True)  # Zoom/Meet ID
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class MeetingAttendee(models.Model):
    meeting = models.ForeignKey('meetings.Meeting', on_delete=models.CASCADE, related_name='attendees')
    name = models.CharField(max_length=255)
    email = models.EmailField()
    external_user_id = models.CharField(max_length=255, blank=True, null=True)  # Zoom/Google ID
    join_time = models.DateTimeField()
    leave_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Duration in seconds")

    def __str__(self):
        return f"{self.name} - {self.meeting.title}"
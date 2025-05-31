from django.db import models

# Create your models here.
class Meeting(models.Model):
    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='meetings')
    host = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='hosted_meetings')

    meeting_id = models.CharField(max_length=255, blank=True, null=True)
    topic = models.CharField(max_length=255, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # In minutes

    status = models.CharField(max_length=20, default='active', choices=(
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('deleted', 'Deleted'),
    ))
    
    video_url = models.URLField(max_length=500, blank=True, null=True)
    recording_ready = models.BooleanField(default=False)

    join_url = models.URLField(max_length=500, blank=True, null=True)
    start_url = models.URLField(max_length=800, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.topic} ({self.start_time})"

    
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
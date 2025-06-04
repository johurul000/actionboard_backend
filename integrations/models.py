from django.db import models

# Create your models here.
class OAuthToken(models.Model):
    PROVIDER_CHOICES = (
        ('zoom', 'Zoom'),
        ('google_meet', 'Google Meet'),
        ('teams', 'Microsoft Teams'),
    )

    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='oauth_tokens')

    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)

    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    token_type = models.CharField(max_length=50, default='Bearer')
    scope = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organisation', 'provider')

    def __str__(self):
        return f"{self.organisation.name} - {self.provider}"
    
class ZoomProfile(models.Model):
    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='zoom_profiles')
    oauth_token = models.OneToOneField('integrations.OAuthToken', on_delete=models.CASCADE, related_name='zoom_profile')

    zoom_user_id = models.CharField(max_length=255, unique=True)
    zoom_account_id = models.CharField(max_length=255, blank=True)
    zoom_email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.zoom_email} ({self.organisation.name})"



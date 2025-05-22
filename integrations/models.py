from django.db import models

# Create your models here.
class OAuthToken(models.Model):
    PROVIDER_CHOICES = (
        ('zoom', 'Zoom'),
        ('google_meet', 'Google Meet'),
        ('teams', 'Microsoft Teams'),
    )

    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='oauth_tokens')
    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='oauth_tokens')
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)

    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    token_type = models.CharField(max_length=50, default='Bearer')
    scope = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'organisation', 'provider')
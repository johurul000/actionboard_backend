from django.db import models

# Create your models here.

class Organisation(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='created_organisations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class OrganisationMembership(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )

    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='memberships')
    organisation = models.ForeignKey('organisations.Organisation', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'organisation')
from django.db import models
from django.utils.crypto import get_random_string
import string
import random

# Create your models here.

class Organisation(models.Model):
    name = models.CharField(max_length=255)
    org_id = models.CharField(max_length=8, unique=True, editable=False)
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='created_organisations')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.org_id:
            self.org_id = self.generate_unique_org_id()
        super().save(*args, **kwargs)

    def generate_unique_org_id(self):
        while True:
            org_id = get_random_string(length=8, allowed_chars=string.ascii_uppercase + string.digits)
            if not Organisation.objects.filter(org_id=org_id).exists():
                return org_id
            
    
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
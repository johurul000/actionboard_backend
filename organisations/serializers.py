from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Organisation


class CreateOrganizationSerializer(serializers.Serializer):
    
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'created_at']  
        read_only_fields = ['id', 'created_at']
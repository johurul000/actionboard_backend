from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Organisation



class CreateOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'created_at', 'org_id']  
        read_only_fields = ['id', 'created_at', 'org_id']

    def create(self, validated_data):
        return Organisation.objects.create(**validated_data)
    
class OrganisationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'org_id', 'name']
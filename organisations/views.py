from django.shortcuts import render
from .models import Organisation, OrganisationMembership
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import CreateOrganizationSerializer


class CreateOrganizationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request,*args, **kwargs):
        serializer = CreateOrganizationSerializer(data=request.data)
        if serializer.is_valid():
            organization = serializer.save(created_by=request.user) 
            OrganisationMembership.objects.create(
                user = request.user,
                organization = organization,
                role = 'admin'
                )
            return Response({"message" : "Organization Created.","organization_id": organization.id},  status=status.HTTP_201_CREATED) #Change Output Message               
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
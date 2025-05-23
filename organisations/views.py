from django.shortcuts import render
from .models import Organisation, OrganisationMembership
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import CreateOrganizationSerializer, OrganisationListSerializer


class CreateOrganizationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request,*args, **kwargs):
        serializer = CreateOrganizationSerializer(data=request.data)
        if serializer.is_valid():
            organization = serializer.save(created_by=request.user) 
            OrganisationMembership.objects.create(
                user=request.user,
                organisation=organization,
                role='admin'
            )
            return Response({
                "message" : "Organization Created.",
                "id": organization.id,
                "org_id": organization.org_id,
                "name": organization.name,
                },  status=status.HTTP_201_CREATED)            
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserOrganisationsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        memberships = OrganisationMembership.objects.filter(user=user).select_related('organisation')
        organisations = [membership.organisation for membership in memberships]
        serializer = OrganisationListSerializer(organisations, many=True)
        return Response(serializer.data)
    

class DeleteOrganisationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        org_id = request.data.get('org_id')
        org_pk = request.data.get('id')

        if not org_id and not org_pk:
            return Response({"detail": "Provide either 'org_id' or 'id'."}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the organisation
        try:
            if org_id:
                organisation = Organisation.objects.get(org_id=org_id)
            else:
                organisation = Organisation.objects.get(pk=org_pk)
        except Organisation.DoesNotExist:
            return Response({"detail": "Organisation not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if the user is an admin in that organisation
        try:
            membership = OrganisationMembership.objects.get(user=request.user, organisation=organisation)
            if membership.role != 'admin':
                return Response({"detail": "Only admins can delete the organisation."}, status=status.HTTP_403_FORBIDDEN)
        except OrganisationMembership.DoesNotExist:
            return Response({"detail": "You are not a member of this organisation."}, status=status.HTTP_403_FORBIDDEN)

        # Delete organisation
        organisation.delete()
        return Response({"detail": "Organisation deleted successfully."}, status=status.HTTP_200_OK)
from django.urls import path
from .views import *


urlpatterns = [
    path('create-organization/', CreateOrganizationView.as_view(), name='create-organization'),
    path('my-organisations/', UserOrganisationsListAPIView.as_view(), name='user-organisations-list'),
    path('delete/', DeleteOrganisationAPIView.as_view(), name='delete-organisation'),
]
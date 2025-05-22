from django.urls import path
from .views import *


urlpatterns = [
    path('create-organization/', CreateOrganizationView.as_view(), name='create-organization'),
]
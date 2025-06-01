from django.urls import path
from .views import *


urlpatterns = [
    path('zoom/oauth/start/', ZoomOAuthStartView.as_view()),
    path('zoom/oauth/callback/', ZoomOAuthCallbackView.as_view()),
]

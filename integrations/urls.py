from django.urls import path
from .views import *


urlpatterns = [
    path('zoom/oauth/start/', ZoomOAuthStartView.as_view()),
    path('zoom/oauth/callback/', ZoomOAuthCallbackView.as_view()),
     path('zoom/status/', ZoomConnectionStatusView.as_view(), name='zoom-status'), 
]

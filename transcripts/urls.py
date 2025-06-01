from django.urls import path
from .views import *


urlpatterns = [
    path("zoom/transcribe/<str:meeting_id>/", TranscribeRecordingView.as_view(), name="transcribe-recording"),
    path("zoom/fetch-transcript/<str:meeting_id>/", FetchTranscriptView.as_view(), name="fetch-transcript"),
]


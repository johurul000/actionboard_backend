from django.urls import path
from .views import *


urlpatterns = [
    path("zoom/transcribe/<str:meeting_id>/", TranscribeRecordingView.as_view(), name="transcribe-recording"),
    path("zoom/fetch-transcript/<str:meeting_id>/", FetchTranscriptView.as_view(), name="fetch-transcript"),

    path("zoom/list-speakers/<str:meeting_id>/", ListSpeakersView.as_view(), name="list-speakers"),
    path("zoom/update-speakers/<str:meeting_id>/", UpdateSpeakerNamesView.as_view(), name="update-speakers"),

]


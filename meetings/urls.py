from django.urls import path
from .views import *


urlpatterns = [
    # path('zoom/sync-past-meetings/', ZoomSyncPastMeetingsView.as_view()),
    # path('zoom/meeting-ended/', ZoomMeetingEndedWebhookView.as_view()),
    # path('zoom/recording-complete/', ZoomRecordingCompletedWebhookView.as_view()),
    # path('zoom/meeting-list/', MeetingListView.as_view(), name='meeting-list'),
    path('zoom/create-meetings/<str:org_id>/', CreateZoomMeetingView.as_view(), name='create_zoom_meeting'),
    path('zoom/webhooks/', ZoomWebhookView.as_view(), name='zoom-webhook'),
    path('zoom/list-meetings/<str:org_id>/', MeetingListView.as_view(), name='meeting-list'),

]
from django.shortcuts import render
import requests
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework import generics
from integrations.models import OAuthToken, ZoomProfile
from integrations.zoom_client import ZoomAPIClient
from meetings.models import Meeting
from meetings.serializers import MeetingSerializer
from organisations.models import Organisation
from rest_framework import status
from django.utils import timezone 


# Create your views here.
# class ZoomSyncPastMeetingsView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         org_id = request.data.get("org_id")
#         try:
#             zoom_profile = ZoomProfile.objects.get(user=request.user, organisation__org_id=org_id)
#         except ZoomProfile.DoesNotExist:
#             return Response({"error": "Zoom profile not found"}, status=404)

#         zoom_client = ZoomAPIClient(zoom_profile.oauth_token)

#         page_number = 1
#         max_pages = 2
#         total_synced = 0

#         while page_number <= max_pages:
#             response_data = zoom_client.list_past_meetings(zoom_profile.zoom_user_id, page_number)
#             meetings = response_data.get("meetings", [])

#             for item in meetings:
#                 meeting_id = item["id"]
#                 defaults = {
#                     "topic": item.get("topic"),
#                     "start_time": item.get("start_time"),
#                     "duration": item.get("duration"),
#                     "status": "ended",
#                     "zoom_profile": zoom_profile,
#                     "organisation": zoom_profile.organisation,
#                 }
#                 obj, created = Meeting.objects.update_or_create(
#                     meeting_id=meeting_id,
#                     defaults=defaults,
#                 )
#                 if created:
#                     total_synced += 1

#             if not response_data.get("next_page_token"):
#                 break
#             page_number += 1

#         zoom_profile.last_synced_at = timezone.now()
#         zoom_profile.save(update_fields=["last_synced_at"])

#         return Response({
#             "status": "success", 
#             "total_synced": total_synced,
#             "last_synced_at": zoom_profile.last_synced_at.isoformat(),
#         })





# # Meeting Ended
# class ZoomMeetingEndedWebhookView(APIView):
#     permission_classes = [AllowAny]  # Zoom sends the event

#     def post(self, request):
#         data = request.data
#         meeting_id = data["payload"]["object"]["id"]
#         host_id = data["payload"]["object"]["host_id"]

#         # Find the ZoomProfile
#         zoom_profile = ZoomProfile.objects.filter(zoom_user_id=host_id).first()
#         if not zoom_profile:
#             return Response({"error": "Zoom profile not found"}, status=404)

#         # Save the meeting details
#         Meeting.objects.update_or_create(
#             external_meeting_id=meeting_id,
#             organisation=zoom_profile.organisation,
#             created_by=zoom_profile.user,
#             defaults={
#                 "title": data["payload"]["object"]["topic"],
#                 "date": data["payload"]["object"]["start_time"],
#             }
#         )
#         return Response({"status": "Meeting saved!"})



# # Recording complete
# class ZoomRecordingCompletedWebhookView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         meeting_id = data["payload"]["object"]["id"]
#         host_id = data["payload"]["object"]["host_id"]

#         # Find the ZoomProfile
#         zoom_profile = ZoomProfile.objects.filter(zoom_user_id=host_id).first()
#         if not zoom_profile:
#             return Response({"error": "Zoom profile not found"}, status=404)

#         # Find the recording file URL
#         recording_files = data["payload"]["object"]["recording_files"]
#         video_url = next(
#             (file["play_url"] for file in recording_files if file["file_type"] == "MP4"), None
#         )

#         if video_url:
#             # Update the Meeting with video URL
#             meeting = Meeting.objects.filter(
#                 external_meeting_id=meeting_id,
#                 organisation=zoom_profile.organisation,
#             ).first()

#             if meeting:
#                 meeting.video_url = video_url
#                 meeting.save()

#         return Response({"status": "Recording updated!"})
    


# class MeetingListView(generics.ListAPIView):
#     serializer_class = MeetingSerializer
#     permission_classes = [IsAuthenticated]  

#     def get_queryset(self):
#         user = self.request.user

#         # You can filter by the user's organisation if needed
#         org_id = self.request.query_params.get('org_id')
#         queryset = Meeting.objects.filter(organisation__members=user)

#         if org_id:
#             queryset = queryset.filter(organisation__org_id=org_id)

#         return queryset.order_by('-date') 
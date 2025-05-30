from django.shortcuts import render
import requests
from django.views import View
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
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

class CreateZoomMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, org_id):  # org_id from URL

        topic = request.data.get('topic')
        start_time_str = request.data.get('start_time')  # ISO8601 string
        duration = request.data.get('duration', 30)

        if not topic or not start_time_str:
            return Response({"error": "Missing topic or start_time"}, status=400)

        start_time = parse_datetime(start_time_str)
        if not start_time:
            return Response({"error": "Invalid start_time format"}, status=400)

        # Get organisation by org_id or 404
        organisation = get_object_or_404(Organisation, org_id=org_id)

        # Check OAuth token
        try:
            oauth_token = OAuthToken.objects.get(user=request.user, provider="zoom")
        except OAuthToken.DoesNotExist:
            return Response({"error": "Zoom not connected"}, status=400)

        # Refresh if expired
        if oauth_token.expires_at <= timezone.now():
            if not self.refresh_zoom_token(oauth_token):
                return Response({"error": "Failed to refresh Zoom token"}, status=400)

        zoom_api_url = "https://api.zoom.us/v2/users/me/meetings"
        headers = {
            "Authorization": f"Bearer {oauth_token.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "topic": topic,
            "type": 2,
            "start_time": start_time.isoformat(),
            "duration": duration,
            "timezone": "UTC",
            "settings": {
                "join_before_host": False,
                "waiting_room": True,
            }
        }
        import json

        response = requests.post(zoom_api_url, json=data, headers=headers)
        if response.status_code != 201:
            return Response({"error": "Zoom API error", "details": response.json()}, status=response.status_code)

        zoom_meeting = response.json()
        print(json.dumps(zoom_meeting, indent=2))

        meeting = Meeting.objects.create(
            organisation=organisation,
            host=request.user,
            meeting_id=str(zoom_meeting["id"]),
            topic=zoom_meeting["topic"],
            start_time=parse_datetime(zoom_meeting["start_time"]),
            duration=zoom_meeting.get("duration"),
            join_url=zoom_meeting.get("join_url"),
            start_url=zoom_meeting.get("start_url"),
        )

        return Response({
            "message": "Meeting created successfully",
            "meeting": {
                "id": meeting.id,
                "meeting_id": meeting.meeting_id,
                "topic": meeting.topic,
                "start_time": meeting.start_time,
                "duration": meeting.duration,
                "join_url": meeting.join_url,
                "start_url": meeting.start_url,
            }
        })

    def refresh_zoom_token(self, oauth_token):
        refresh_url = "https://zoom.us/oauth/token"
        auth = (settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": oauth_token.refresh_token
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        resp = requests.post(refresh_url, data=data, headers=headers, auth=auth)
        if resp.status_code != 200:
            return False

        token_data = resp.json()
        oauth_token.access_token = token_data["access_token"]
        oauth_token.refresh_token = token_data["refresh_token"]
        oauth_token.expires_at = timezone.now() + timezone.timedelta(seconds=token_data["expires_in"])
        oauth_token.save()
        return True


@method_decorator(csrf_exempt, name='dispatch')
class ZoomWebhookView(View):

    def post(self, request):
        data = json.loads(request.body)
        event = data.get("event")

        if event == "meeting.ended":
            meeting_id = data["payload"]["object"]["id"]
            meeting = Meeting.objects.filter(meeting_id=str(meeting_id)).first()
            if meeting:
                meeting.status = "ended"
                meeting.end_time = parse_datetime(data["payload"]["object"]["end_time"])
                meeting.save()

        elif event == "recording.completed":
            meeting_id = data["payload"]["object"]["id"]
            recording_files = data["payload"]["object"]["recording_files"]
            meeting = Meeting.objects.filter(meeting_id=str(meeting_id)).first()
            if meeting and recording_files:
                # Example: save first recording URL
                meeting.video_url = recording_files[0]["download_url"]
                meeting.recording_ready = True
                # Update end_time again if you want, usually already set
                meeting.end_time = parse_datetime(data["payload"]["object"]["end_time"])
                meeting.save()

        return JsonResponse({"status": "received"})
    

    def get(self, request, *args, **kwargs):
        return JsonResponse({"error": "GET method not allowed"}, status=405)



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



from django.shortcuts import render
import requests
from django.views import View
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework import generics
from integrations.models import OAuthToken, ZoomProfile
from integrations.zoom_client import ZoomAPIClient
from meetings.models import Meeting, Recording
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
from django.views.generic import ListView

from transcripts.models import Transcript


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
            oauth_token = OAuthToken.objects.get(organisation=organisation, provider="zoom")
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
        print("==== Received webhook data ====")
        print(json.dumps(data, indent=2))  # Pretty-print JSON for readability!

        event = data.get("event")
        print(f"==== Event: {event} ====")

        if event == "meeting.ended":
            meeting_id = data["payload"]["object"]["id"]
            print(f"==== Meeting Ended ID: {meeting_id} ====")

            meeting = Meeting.objects.filter(meeting_id=str(meeting_id)).first()
            if meeting:
                meeting.status = "ended"
                meeting.end_time = parse_datetime(data["payload"]["object"]["end_time"])
                meeting.save()
                print(f"==== Updated Meeting {meeting_id} as ended ====")

        elif event == "recording.completed":
            meeting_id = data["payload"]["object"]["id"]
            recording_files = data["payload"]["object"]["recording_files"]
            meeting = Meeting.objects.filter(meeting_id=str(meeting_id)).first()
            if meeting and recording_files:
                for rec in recording_files:
                    recording_id = rec.get("id")
                    recording, created = Recording.objects.get_or_create(
                        recording_id=recording_id,
                        defaults={
                            "meeting": meeting,
                            "recording_type": rec.get("recording_type"),
                            "file_type": rec.get("file_type"),
                            "file_size": rec.get("file_size"),
                            "play_url": rec.get("play_url"),
                            "download_url": rec.get("download_url"),
                            "recording_start": parse_datetime(rec.get("recording_start")),
                            "recording_end": parse_datetime(rec.get("recording_end")),
                        }
                    )
                    if not created:
                        recording.play_url = rec.get("play_url")
                        recording.download_url = rec.get("download_url")
                        recording.recording_start = parse_datetime(rec.get("recording_start"))
                        recording.recording_end = parse_datetime(rec.get("recording_end"))
                        recording.save()

                    # If this is a transcript file
                    if rec.get("file_type") in ["TIMELINE_TRANSCRIPT", "TRANSCRIPT"]:
                        transcript_url = rec.get("download_url")
                        oauth_token = self.get_zoom_oauth_token_for_meeting(meeting)
                        if not oauth_token:
                            print("Zoom not connected for this meeting's host!")
                            continue

                        headers = {
                            "Authorization": f"Bearer {oauth_token.access_token}"
                        }
                        transcript_response = requests.get(transcript_url, headers=headers)
                        if transcript_response.status_code == 200:
                            full_transcript_text = transcript_response.text
                            Transcript.objects.update_or_create(
                                meeting=meeting,
                                defaults={
                                    "full_transcript": full_transcript_text,
                                    "summary": {},
                                    "language": "en"
                                }
                            )
                        else:
                            print("Failed to download Zoom transcript file.")

                meeting.recording_ready = True
                meeting.save()

        return JsonResponse({"status": "received"})

    def get(self, request, *args, **kwargs):
        return JsonResponse({"error": "GET method not allowed"}, status=405)

    def get_zoom_oauth_token_for_meeting(self, meeting):
        """
        Helper to get a valid Zoom OAuth token for the meeting's host.
        Refreshes if expired.
        """
        organisation = meeting.organisation
        if not organisation:
            return None

        try:
            oauth_token = OAuthToken.objects.get(organisation=organisation, provider="zoom")
        except OAuthToken.DoesNotExist:
            return None

        if oauth_token.expires_at <= timezone.now():
            if not self.refresh_zoom_token(oauth_token):
                return None
        return oauth_token

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


class MeetingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, org_id):
        try:
            # Get the organization
            organisation = get_object_or_404(Organisation, org_id=org_id)
            
            # Get meetings for this organization
            meetings = Meeting.objects.filter(organisation=organisation).prefetch_related('recordings')
            
            # Format meetings data for frontend
            meetings_data = []
            for meeting in meetings:
                # Format recordings
                recordings_data = []
                for rec in meeting.recordings.all():
                    recordings_data.append({
                        'id': rec.recording_id,
                        'play_url': rec.play_url,
                        'download_url': rec.download_url,
                        'file_type': rec.file_type,
                        'recording_start': rec.recording_start,
                        'recording_end': rec.recording_end,
                    })

                # Format meeting data to match frontend expectations
                meetings_data.append({
                    'id': meeting.meeting_id,  # Use meeting_id as the ID
                    'topic': meeting.topic,
                    'start_time': meeting.start_time.isoformat() if meeting.start_time else None,
                    'duration': meeting.duration,
                    'status': meeting.status or 'scheduled',
                    'join_url': meeting.join_url,
                    'agenda': getattr(meeting, 'agenda', ''),  # Add if you have this field
                    'source': 'Zoom',  # Add source field
                    'recordings': recordings_data,
                })

            return Response({
                'meetings': meetings_data,
                'total': len(meetings_data)
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=500)



class MeetingDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        try:
            # Get the meeting by meeting_id
            meeting = get_object_or_404(Meeting, meeting_id=meeting_id)
            
            # Check if user has access to this meeting
            # Since we don't have a members relationship, we'll check if user is the host
            # or you can modify this based on your actual organization access logic
            if meeting.host != request.user:
                # If you have a different way to check organization access, update this
                # For now, we'll allow access if user is authenticated
                # You might want to add organization membership check here
                pass
            
            # Get recordings for this meeting
            recordings_data = []
            if hasattr(meeting, 'recordings'):
                for rec in meeting.recordings.all():
                    recordings_data.append({
                        'id': rec.recording_id,
                        'play_url': rec.play_url,
                        'download_url': rec.download_url,
                        'file_type': rec.file_type,
                        'recording_type': rec.recording_type,
                        'file_size': rec.file_size,
                        'recording_start': rec.recording_start.isoformat() if rec.recording_start else None,
                        'recording_end': rec.recording_end.isoformat() if rec.recording_end else None,
                    })

            # Get transcript if exists
            transcript_data = None
            try:
                transcript = Transcript.objects.get(meeting=meeting)
                transcript_data = {
                    'full_transcript': transcript.full_transcript,
                    'summary': transcript.summary,
                    'language': transcript.language,
                    'created_at': transcript.created_at.isoformat() if hasattr(transcript, 'created_at') else None,
                }
            except Transcript.DoesNotExist:
                pass

            # Calculate meeting status based on times if status is 'active'
            calculated_status = meeting.status
            if meeting.status == 'active' and meeting.start_time:
                from django.utils import timezone
                now = timezone.now()
                
                if meeting.end_time and now > meeting.end_time:
                    calculated_status = 'ended'
                elif now >= meeting.start_time:
                    if meeting.duration:
                        estimated_end = meeting.start_time + timezone.timedelta(minutes=meeting.duration)
                        if now > estimated_end:
                            calculated_status = 'ended'
                        else:
                            calculated_status = 'started'
                    else:
                        calculated_status = 'started'
                else:
                    calculated_status = 'scheduled'

            # Format host data based on your CustomUser model
            host_data = None
            if meeting.host:
                # Create full name from first_name and last_name
                full_name = ""
                if meeting.host.first_name and meeting.host.last_name:
                    full_name = f"{meeting.host.first_name} {meeting.host.last_name}".strip()
                elif meeting.host.first_name:
                    full_name = meeting.host.first_name
                elif meeting.host.last_name:
                    full_name = meeting.host.last_name
                
                host_data = {
                    'id': meeting.host.id,
                    'email': meeting.host.email,
                    'first_name': meeting.host.first_name or '',
                    'last_name': meeting.host.last_name or '',
                    'full_name': full_name,
                    'country': str(meeting.host.country) if meeting.host.country else None,
                }

            # Format organisation data safely
            organisation_data = None
            if meeting.organisation:
                organisation_data = {
                    'id': meeting.organisation.id,
                }
                
                # Add name/org_id fields if they exist
                if hasattr(meeting.organisation, 'name'):
                    organisation_data['name'] = meeting.organisation.name
                if hasattr(meeting.organisation, 'org_id'):
                    organisation_data['org_id'] = meeting.organisation.org_id

            # Format meeting data to match your model
            meeting_data = {
                'id': meeting.id,
                'meeting_id': meeting.meeting_id,
                'topic': meeting.topic,
                'start_time': meeting.start_time.isoformat() if meeting.start_time else None,
                'end_time': meeting.end_time.isoformat() if meeting.end_time else None,
                'duration': meeting.duration,
                'status': calculated_status,  # Use calculated status
                'join_url': meeting.join_url,
                'start_url': meeting.start_url,
                'video_url': meeting.video_url,  # From your model
                'host': host_data,
                'organisation': organisation_data,
                'recording_ready': meeting.recording_ready,
                'recordings': recordings_data,
                'transcript': transcript_data,
                'created_at': meeting.created_at.isoformat(),
                'updated_at': meeting.updated_at.isoformat(),
            }

            return Response(meeting_data)
            
        except Exception as e:
            return Response({
                'error': f'Failed to retrieve meeting details: {str(e)}'
            }, status=500)

# @method_decorator(csrf_exempt, name='dispatch')
# class ZoomWebhookView(View):

#     def post(self, request):
#         data = json.loads(request.body)
#         event = data.get("event")

#         if event == "meeting.ended":
#             meeting_id = data["payload"]["object"]["id"]
#             meeting = Meeting.objects.filter(meeting_id=str(meeting_id)).first()
#             if meeting:
#                 meeting.status = "ended"
#                 meeting.end_time = parse_datetime(data["payload"]["object"]["end_time"])
#                 meeting.save()

#         elif event == "recording.completed":
#             meeting_id = data["payload"]["object"]["id"]
#             recording_files = data["payload"]["object"]["recording_files"]
#             meeting = Meeting.objects.filter(meeting_id=str(meeting_id)).first()
#             if meeting and recording_files:
#                 # Example: save first recording URL
#                 meeting.video_url = recording_files[0]["download_url"]
#                 meeting.recording_ready = True
#                 # Update end_time again if you want, usually already set
#                 meeting.end_time = parse_datetime(data["payload"]["object"]["end_time"])
#                 meeting.save()

#         return JsonResponse({"status": "received"})
    

#     def get(self, request, *args, **kwargs):
#         return JsonResponse({"error": "GET method not allowed"}, status=405)



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



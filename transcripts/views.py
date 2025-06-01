from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from meetings.models import Meeting
import requests
from rest_framework.permissions import IsAuthenticated
from transcripts.assembly_ai import transcribe_recording_with_secure_url
from transcripts.models import Transcript

# Create your views here.
class FetchTranscriptView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = Meeting.objects.filter(meeting_id=meeting_id).first()
        if not meeting:
            return Response({"error": "Meeting not found"}, status=404)
        
        if hasattr(meeting, "transcript"):
            transcript_data = {
                "full_transcript": meeting.transcript.full_transcript,
                "summary": meeting.transcript.summary,
                "language": meeting.transcript.language,
            }
            return Response(transcript_data, status=200)
        else:
            return Response({"transcript": None}, status=200)


class TranscribeRecordingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, meeting_id=meeting_id)

        try:
            transcript_text, summary = transcribe_recording_with_secure_url(
                meeting_id, request.user
            )

            transcript, created = Transcript.objects.get_or_create(
                meeting=meeting,
                defaults={
                    "full_transcript": transcript_text,
                    "summary": summary
                }
            )
            if not created:
                transcript.full_transcript = transcript_text
                transcript.summary = summary
                transcript.save()

            return Response({
                "full_transcript": transcript.full_transcript,
                "summary": transcript.summary
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)




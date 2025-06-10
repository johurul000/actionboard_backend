from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from meetings.models import Meeting
import requests
from rest_framework.permissions import IsAuthenticated
from transcripts.assembly_ai import transcribe_recording_with_secure_url
from transcripts.models import Transcript
import re


# Create your views here.
class FetchTranscriptView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = Meeting.objects.filter(meeting_id=meeting_id).first()
        if not meeting:
            return Response({"error": "Meeting not found"}, status=404)

        if hasattr(meeting, "transcript"):
            transcript = meeting.transcript
            transcript_data = {
                "full_transcript": transcript.full_transcript,
                "summary": transcript.summary,
                "language": transcript.language,
                "utterances": transcript.utterances if transcript.utterances else [],
                "meeting_insights": transcript.cohere_insights if transcript.cohere_insights else {},
                "speakers_updated": transcript.speakers_updated,
            }
            return Response(transcript_data, status=200)

        return Response({"transcript": None}, status=200)


class TranscribeRecordingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, meeting_id=meeting_id)

        try:
            transcript_text, assembly_data = transcribe_recording_with_secure_url(
                meeting_id, request.user
            )

            summary = assembly_data["summary_text"]
            cohere_insights = assembly_data["cohere_insights"]
            utterances = assembly_data["utterances"]

            transcript, created = Transcript.objects.get_or_create(
                meeting=meeting,
                defaults={
                    "full_transcript": transcript_text,
                    "summary": summary,
                    "cohere_insights": cohere_insights,
                    "utterances": utterances,
                    "speakers_updated": False,
                }
            )
            if not created:
                transcript.full_transcript = transcript_text
                transcript.summary = summary
                transcript.cohere_insights = cohere_insights
                transcript.utterances = utterances
                transcript.speakers_updated = False
                transcript.save()

            return Response({
                "full_transcript": transcript.full_transcript,
                "summary": transcript.summary,
                "meeting_insights": transcript.cohere_insights,
                "utterances": transcript.utterances,
                "speakers_updated": transcript.speakers_updated
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)



class ListSpeakersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, meeting_id=meeting_id)

        if not hasattr(meeting, "transcript") or not meeting.transcript.utterances:
            return Response({"speakers": []}, status=200)

        transcript = meeting.transcript
        if transcript.speakers_updated:
            return Response(
                {"message": "Speakers have already been updated."},
                status=400
            )

        speaker_codes = {
            u["speaker"]
            for u in transcript.utterances
            if 'speaker' in u
        }

        return Response({"speakers": sorted(speaker_codes)}, status=200)
    
import json

class UpdateSpeakerNamesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, meeting_id=meeting_id)

        if not hasattr(meeting, "transcript"):
            return Response({"error": "Transcript not found"}, status=404)

        speaker_map = request.data.get("speaker_map", {})
        if not isinstance(speaker_map, dict):
            return Response({"error": "Invalid speaker_map"}, status=400)

        transcript = meeting.transcript

        if getattr(transcript, "speakers_updated", False):
            return Response(
                {"message": "Speakers have already been updated."},
                status=400
            )

        # === Update utterances ===
        updated_utterances = []
        for utterance in transcript.utterances or []:
            old_code = utterance.get("speaker")
            if old_code in speaker_map:
                utterance["speaker"] = speaker_map[old_code]
            updated_utterances.append(utterance)

        # === Update full_transcript ===
        full_transcript = transcript.full_transcript or ""
        for code, name in speaker_map.items():
            pattern = re.compile(rf"Speaker {re.escape(code)}")
            full_transcript = pattern.sub(name, full_transcript)

        # === Update cohere_insights ===
        insights = transcript.cohere_insights or {}

        # Update speaker_summaries
        speaker_summaries = insights.get("speaker_summaries", {})
        updated_summaries = {}
        for key, value in speaker_summaries.items():
            match = re.match(r"Speaker (\w+)", key)
            if match:
                code = match.group(1)
                if code in speaker_map:
                    # Replace speaker mentions inside the summary too
                    updated_value = value
                    for old_code, new_name in speaker_map.items():
                        updated_value = re.sub(rf"\bSpeaker {re.escape(old_code)}\b", new_name, updated_value)
                    updated_summaries[speaker_map[code]] = updated_value
                else:
                    updated_summaries[key] = value
            else:
                updated_summaries[key] = value
        insights["speaker_summaries"] = updated_summaries

        # Update structured_summary
        structured = insights.get("structured_summary", "")
        for code, name in speaker_map.items():
            pattern = re.compile(rf"Speaker {re.escape(code)}")
            structured = pattern.sub(name, structured)
        insights["structured_summary"] = structured

        # === Save all changes ===
        transcript.utterances = updated_utterances
        transcript.full_transcript = full_transcript
        transcript.cohere_insights = insights
        transcript.speaker_map = speaker_map
        transcript.speakers_updated = True
        transcript.save(update_fields=[
            "utterances",
            "full_transcript",
            "cohere_insights",
            "speaker_map",
            "speakers_updated"
        ])

        # === Debug Logs ===
        print("==== DEBUG: Speaker Update ====")
        print("Speaker Map:", json.dumps(speaker_map, indent=2))
        print("Updated full_transcript preview:", full_transcript[:300])
        print("Updated speaker_summaries:", json.dumps(updated_summaries, indent=2))
        print("Updated structured_summary preview:", structured[:300])

        return Response(
            {"message": "Speakers updated successfully.",
             "speakers_updated": transcript.speakers_updated
            }, 
            status=200
        )


class GetSpeakerSummariesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, meeting_id=meeting_id)

        if not hasattr(meeting, "transcript") or not meeting.transcript.cohere_insights:
            return Response({"speaker_summaries": {}}, status=200)

        insights = meeting.transcript.cohere_insights
        summaries = insights.get("speaker_summaries", {})

        return Response({"speaker_summaries": summaries}, status=200)
    

class UpdateSpeakerSummariesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, meeting_id=meeting_id)

        if not hasattr(meeting, "transcript"):
            return Response({"error": "Transcript not found"}, status=404)

        new_summaries = request.data.get("speaker_summaries", {})
        if not isinstance(new_summaries, dict):
            return Response({"error": "Invalid speaker_summaries format"}, status=400)

        transcript = meeting.transcript
        insights = transcript.cohere_insights or {}
        insights["speaker_summaries"] = new_summaries
        transcript.cohere_insights = insights
        transcript.save(update_fields=["cohere_insights"])

        return Response({
            "message": "Speaker summaries updated successfully.",
            "speaker_summaries": new_summaries
        }, status=200)

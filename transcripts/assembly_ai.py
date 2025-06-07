import time
import requests
import os
from integrations.models import OAuthToken
from django.utils import timezone
from rest_framework.response import Response
from django.conf import settings
import assemblyai as aai
import cohere
from collections import defaultdict
import re
from meetings.models import Meeting


ASSEMBLYAI_ENDPOINT = "https://api.assemblyai.com/v2"


headers = {
    "authorization": settings.ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}

aai.settings.api_key = settings.ASSEMBLYAI_API_KEY


def transcribe_recording_with_secure_url(meeting_id, user):
    """
    Downloads fresh Zoom audio recording, uploads to AssemblyAI for transcription,
    and returns (transcript_text, summary).
    """
    meeting = Meeting.objects.get(meeting_id=meeting_id)


    organisation = meeting.organisation
    if not organisation:
        raise Exception("Meeting not linked to an organisation.")

    try:
        oauth_token = OAuthToken.objects.get(
            organisation=organisation,
            provider="zoom"
        )
    except OAuthToken.DoesNotExist:
        raise Exception("Zoom OAuth token not found for this organisation.")

 
    recordings_resp = requests.get(
        f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings",
        headers={"Authorization": f"Bearer {oauth_token.access_token}"}
    )
    recordings_resp.raise_for_status()
    recordings_data = recordings_resp.json()

    audio_file = next(
        (f for f in recordings_data.get('recording_files', [])
         if f['file_type'] == 'M4A'),
        None
    )
    if not audio_file:
        raise Exception("No audio recording found for this meeting.")


    download_url = f"{audio_file['download_url']}?access_token={oauth_token.access_token}"


    local_audio_file = 'audio_file.m4a'
    download_audio_to_file(download_url, local_audio_file)


    assemblyai_audio_url = upload_audio_file_to_assemblyai(local_audio_file)


    transcript_text, summary, utterances = transcribe_with_assembly_ai(assemblyai_audio_url)

    os.remove(local_audio_file)

    cohere_insights = analyze_transcript_with_cohere(
        utterances,
        cohere_api_key=settings.COHERE_API_KEY  
    )
    return transcript_text, {
        "summary_text": summary,
        "utterances": [
            {
                "speaker": u["speaker"],
                "start": round(u["start"] / 1000, 2),
                "end": round(u["end"] / 1000, 2),
                "text": u["text"]
            }
            for u in utterances
        ],
        "cohere_insights": cohere_insights
    }


def analyze_transcript_with_cohere(utterances, cohere_api_key, timeout=300, poll_interval=5):
    """
    Analyzes meeting utterances using Cohere:
    - Generates a structured summary (agenda, minutes, action items)
    - Generates individual speaker summaries
    Returns: dict with structured_summary and speaker_summaries
    """
    co = cohere.Client(cohere_api_key)

    # 1️⃣ Format utterance transcript
    utterance_transcript = "\n".join(
        f"Speaker {u['speaker']} | [{u['start'] / 1000}-{u['end'] / 1000}] {u['text']}"
        for u in utterances
    )

    # 2️⃣ Structured Summary Prompt
    prompt = f"""
        You are an AI assistant that reads meeting transcripts and produces structured summaries.
        Please read the transcript below and return:

        1. Minutes of the Meeting  
        2. Meeting Agenda  
        3. Key Points  
        4. Action Items

        Format your output using section headers.

        Transcript:
        {utterance_transcript}
    """

    structured_summary_response = co.generate(
        model="command-r-plus",
        prompt=prompt,
        max_tokens=1500,
        temperature=0.3
    )
    structured_summary = structured_summary_response.generations[0].text.strip()

    # print("=== UTTERANCE TRANSCRIPT ===")
    # print(utterance_transcript)

    # Extract per-speaker blocks
    pattern = re.compile(r"^(Speaker [A-Z])\s+\|\s+\[\d+\.\d+-\d+\.\d+\]\s+(.*)$", re.MULTILINE)

    speaker_texts = defaultdict(list)
    for match in pattern.finditer(utterance_transcript):
        speaker = match.group(1)
        text = match.group(2).strip()
        speaker_texts[speaker].append(text)
    speaker_texts = {k: " ".join(v) for k, v in speaker_texts.items()}

    # Generate speaker summaries
    speaker_summaries = {}
    for speaker, text in speaker_texts.items():
        indiv_prompt = f"""You are an AI assistant. Summarize the following meeting contributions made by {speaker}.
        Only summarize their individual contributions. Mention tasks, opinions, or explanations they provided.

        Text:
        {text}
        """
        resp = co.generate(
            model="command",
            prompt=indiv_prompt,
            max_tokens=500,
            temperature=0.3
        )
        speaker_summaries[speaker] = resp.generations[0].text.strip()

    # Final output
    return {
        "structured_summary": structured_summary,
        "speaker_summaries": speaker_summaries
    }


def download_audio_to_file(audio_url, output_file):
    with requests.get(audio_url, stream=True) as r:
        r.raise_for_status()
        with open(output_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def upload_audio_file_to_assemblyai(file_path):
    headers = {"authorization": settings.ASSEMBLYAI_API_KEY}
    with open(file_path, 'rb') as f:
        upload_resp = requests.post(
            f"{ASSEMBLYAI_ENDPOINT}/upload",
            headers=headers,
            data=f
        )
    upload_resp.raise_for_status()
    return upload_resp.json().get('upload_url')



def transcribe_with_assembly_ai(audio_url, poll_interval=5, timeout=600):
    """
    Transcribes audio from AssemblyAI using both:
    - REST API: to get diarized utterances
    - SDK: to get transcript text + summary
    Returns: (full_text, summary_text, utterances_list)
    """
    import requests

    # REST API: Start transcription with speaker labels
    headers = {"authorization": settings.ASSEMBLYAI_API_KEY}
    start_resp = requests.post(
        f"{ASSEMBLYAI_ENDPOINT}/transcript",
        headers=headers,
        json={
            "audio_url": audio_url,
            "speaker_labels": True
        }
    )
    start_resp.raise_for_status()
    transcript_id = start_resp.json()['id']

    # Polling loop
    total_wait = 0
    while total_wait < timeout:
        poll_resp = requests.get(
            f"{ASSEMBLYAI_ENDPOINT}/transcript/{transcript_id}",
            headers=headers
        )
        poll_resp.raise_for_status()
        data = poll_resp.json()
        if data['status'] == 'completed':
            diarized_utterances = data.get('utterances', [])
            full_text = data.get('text', '')
            break
        elif data['status'] == 'error':
            raise Exception(f"AssemblyAI transcription error: {data.get('error')}")
        time.sleep(poll_interval)
        total_wait += poll_interval
    else:
        raise TimeoutError("AssemblyAI REST transcription timed out")

    # SDK: Fetch summary separately using same audio_url
    config = aai.TranscriptionConfig(
        summarization=True,
        summary_model=aai.SummarizationModel.informative,
        summary_type=aai.SummarizationType.bullets
    )
    transcriber = aai.Transcriber()
    summary_transcript = transcriber.transcribe(audio_url, config=config)

    # Poll for summary
    total_wait = 0
    while summary_transcript.status not in ['completed', 'error']:
        if total_wait > timeout:
            raise TimeoutError("AssemblyAI SDK transcription timed out")
        time.sleep(poll_interval)
        summary_transcript.refresh()
        total_wait += poll_interval

    if summary_transcript.status == 'error':
        raise Exception(f"AssemblyAI summary transcription error: {summary_transcript.error}")

    return full_text, summary_transcript.summary, diarized_utterances



# def transcribe_with_assembly_ai(audio_url, poll_interval=5, timeout=600):
#     """
#     Transcribe audio URL with AssemblyAI SDK and get both transcript and summary.
#     """
#     # Configure transcription with summarization
#     config = aai.TranscriptionConfig(
#         summarization=True,
#         summary_model=aai.SummarizationModel.informative,  # or 'conversational'
#         summary_type=aai.SummarizationType.bullets          # or 'paragraph', 'headline'
#     )
    
#     transcriber = aai.Transcriber()
    
#     # Start transcription (using public URL)
#     transcript = transcriber.transcribe(audio_url, config=config)
    
#     # Wait for completion (polling)
#     total_wait = 0
#     while transcript.status not in ['completed', 'error']:
#         if total_wait > timeout:
#             raise TimeoutError("AssemblyAI transcription timed out")
#         time.sleep(poll_interval)
#         transcript.refresh()  # refresh the status
#         total_wait += poll_interval
    
#     if transcript.status == 'error':
#         raise Exception(f"AssemblyAI transcription error: {transcript.error}")
    
#     # transcript.text -> full transcript text
#     # transcript.summary -> summary string (bullets or paragraph depending on config)
#     return transcript.text, transcript.summary


# def transcribe_with_assembly_ai(audio_url, poll_interval=5, timeout=600):
#     headers = {
#         "authorization": ASSEMBLYAI_API_KEY
#     }
#     transcript_request = {
#         "audio_url": audio_url,
#         # "auto_chapters": True,
#         # "summary_enabled": True,
#         # "summary_model": "general",
#         # "summary_type": "bullets"
#     }

#     response = requests.post(
#         f"{ASSEMBLYAI_ENDPOINT}/transcript",
#         json=transcript_request,
#         headers=headers
#     )
#     response.raise_for_status()
#     transcript_id = response.json()["id"]

#     total_wait = 0
#     while total_wait < timeout:
#         poll_resp = requests.get(
#             f"{ASSEMBLYAI_ENDPOINT}/transcript/{transcript_id}",
#             headers=headers
#         )
#         poll_resp.raise_for_status()
#         data = poll_resp.json()

#         if data.get("status") == "completed":
#             transcript_text = data.get("text", "")
#             summary_text = data.get("summary", "")  # AssemblyAI text summary
#             summary = {"text": summary_text}       # Wrap in dict for JSONField
#             return transcript_text, summary

#         elif data.get("status") == "error":
#             raise Exception(f"Transcription failed: {data.get('error')}")

#         time.sleep(poll_interval)
#         total_wait += poll_interval

#     raise TimeoutError("Transcription polling timed out.")








def refresh_zoom_token(oauth_token):
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
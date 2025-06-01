import time
import requests
import os
from integrations.models import OAuthToken
from django.utils import timezone
from rest_framework.response import Response
from django.conf import settings
import assemblyai as aai


ASSEMBLYAI_API_KEY = "b9d094c60c6a4aa78fd4d54feadc7d73"
ASSEMBLYAI_ENDPOINT = "https://api.assemblyai.com/v2"

headers = {
    "authorization": settings.ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}

aai.settings.api_key = ASSEMBLYAI_API_KEY

def transcribe_recording_with_secure_url(meeting_id, user):
    """
    Downloads fresh Zoom audio recording, uploads to AssemblyAI for transcription,
    and returns (transcript_text, summary).
    """
    # 1️⃣ Get Zoom OAuth token for the user
    try:
        oauth_token = OAuthToken.objects.get(user=user, provider='zoom')
    except OAuthToken.DoesNotExist:
        raise Exception("Zoom OAuth token not found for user.")

    if oauth_token.expires_at <= timezone.now():
        if not refresh_zoom_token(oauth_token):
            raise Exception("Failed to refresh Zoom token")

    # 2️⃣ Fetch fresh download URL from Zoom API
    recordings_resp = requests.get(
        f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings",
        headers={"Authorization": f"Bearer {oauth_token.access_token}"}
    )
    recordings_resp.raise_for_status()
    recordings_data = recordings_resp.json()

    # 3️⃣ Find the audio recording file
    audio_file = next(
        (f for f in recordings_data.get('recording_files', [])
         if f['file_type'] == 'M4A'),
        None
    )
    if not audio_file:
        raise Exception("No audio recording found for this meeting.")

    # 4️⃣ Construct download URL with access_token
    download_url = f"{audio_file['download_url']}?access_token={oauth_token.access_token}"

    # 5️⃣ Download audio file
    local_audio_file = 'audio_file.m4a'
    download_audio_to_file(download_url, local_audio_file)

    # 6️⃣ Upload to AssemblyAI
    assemblyai_audio_url = upload_audio_file_to_assemblyai(local_audio_file)

    # 7️⃣ Transcribe & summarize
    transcript_text, summary = transcribe_with_assembly_ai(assemblyai_audio_url)

    # 8️⃣ Cleanup
    os.remove(local_audio_file)

    return transcript_text, summary


def download_audio_to_file(audio_url, output_file):
    with requests.get(audio_url, stream=True) as r:
        r.raise_for_status()
        with open(output_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def upload_audio_file_to_assemblyai(file_path):
    headers = {"authorization": ASSEMBLYAI_API_KEY}
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
    Transcribe audio URL with AssemblyAI SDK and get both transcript and summary.
    """
    # Configure transcription with summarization
    config = aai.TranscriptionConfig(
        summarization=True,
        summary_model=aai.SummarizationModel.informative,  # or 'conversational'
        summary_type=aai.SummarizationType.bullets          # or 'paragraph', 'headline'
    )
    
    transcriber = aai.Transcriber()
    
    # Start transcription (using public URL)
    transcript = transcriber.transcribe(audio_url, config=config)
    
    # Wait for completion (polling)
    total_wait = 0
    while transcript.status not in ['completed', 'error']:
        if total_wait > timeout:
            raise TimeoutError("AssemblyAI transcription timed out")
        time.sleep(poll_interval)
        transcript.refresh()  # refresh the status
        total_wait += poll_interval
    
    if transcript.status == 'error':
        raise Exception(f"AssemblyAI transcription error: {transcript.error}")
    
    # transcript.text -> full transcript text
    # transcript.summary -> summary string (bullets or paragraph depending on config)
    return transcript.text, transcript.summary


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
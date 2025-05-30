import requests
from django.utils import timezone
from integrations.models import OAuthToken
from django.conf import settings

class ZoomAPIClient:
    BASE_URL = "https://api.zoom.us/v2"

    def __init__(self, oauth_token: OAuthToken):
        self.oauth_token = oauth_token

    def _refresh_access_token(self):
        """
        Refresh the access token using the refresh token.
        Update the OAuthToken model with new credentials.
        """
        token_url = "https://zoom.us/oauth/token"
        auth = (settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.oauth_token.refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(token_url, data=data, headers=headers, auth=auth)
        if response.status_code != 200:
            raise Exception("Failed to refresh access token")

        token_data = response.json()
        self.oauth_token.access_token = token_data["access_token"]
        self.oauth_token.refresh_token = token_data["refresh_token"]
        self.oauth_token.expires_at = timezone.now() + timezone.timedelta(seconds=token_data["expires_in"])
        self.oauth_token.save()

    def _make_request(self, method, endpoint, params=None, data=None):
        """
        Helper to make a request to Zoom API with automatic token refresh.
        """
        headers = {"Authorization": f"Bearer {self.oauth_token.access_token}"}
        url = f"{self.BASE_URL}{endpoint}"

        response = requests.request(method, url, headers=headers, params=params, json=data)
        if response.status_code == 401:
            # Token expired, refresh and retry once
            self._refresh_access_token()
            headers["Authorization"] = f"Bearer {self.oauth_token.access_token}"
            response = requests.request(method, url, headers=headers, params=params, json=data)

        response.raise_for_status()
        return response.json()

    def list_past_meetings(self, zoom_user_id, page_number=1, page_size=30):
        endpoint = f"/users/{zoom_user_id}/meetings"
        params = {
            "type": "past",
            "page_size": page_size,
            "page_number": page_number
        }
        return self._make_request("GET", endpoint, params=params)

    def get_meeting_details(self, meeting_id):
        endpoint = f"/meetings/{meeting_id}"
        return self._make_request("GET", endpoint)

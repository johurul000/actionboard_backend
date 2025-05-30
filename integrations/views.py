from urllib.parse import urlencode
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect
import requests
from django.utils.crypto import get_random_string
from integrations.models import OAuthToken, ZoomProfile
from organisations.models import Organisation
from users.models import CustomUser

# Create your views here.


class ZoomOAuthStartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        random_state = get_random_string(32)

        state_data = f"{user_id}:{random_state}"  # Removed org_id

        redirect_uri = "http://localhost:8000/api/integrations/zoom/oauth/callback/"
        client_id = settings.ZOOM_CLIENT_ID

        query_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state_data,
        }

        authorize_url = f"https://zoom.us/oauth/authorize?{urlencode(query_params)}"

        return Response({"authorize_url": authorize_url})
    


class ZoomOAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code or not state:
            return self.redirect_with_error("missing_code_or_state")

        try:
            user_id, random_state = state.split(":")
        except ValueError:
            return self.redirect_with_error("invalid_state_format")

        redirect_uri = f"{settings.BACKEND_URL}/api/integrations/zoom/oauth/callback/"
        client_id = settings.ZOOM_CLIENT_ID
        client_secret = settings.ZOOM_CLIENT_SECRET

        token_url = "https://zoom.us/oauth/token"
        auth = (client_id, client_secret)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }

        response = requests.post(token_url, headers=headers, data=data, auth=auth)
        if response.status_code != 200:
            return self.redirect_with_error("token_exchange_failed")

        token_data = response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data["expires_in"]
        expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)

        try:
            user = CustomUser.objects.get(id=int(user_id))
        except CustomUser.DoesNotExist:
            return self.redirect_with_error("invalid_user_id")

        oauth_token, _ = OAuthToken.objects.update_or_create(
            user=user,
            provider="zoom",
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            },
        )

        user_info_url = "https://api.zoom.us/v2/users/me"
        user_info_headers = {
            "Authorization": f"Bearer {access_token}"
        }
        user_info_resp = requests.get(user_info_url, headers=user_info_headers)
        if user_info_resp.status_code != 200:
            return self.redirect_with_error("zoom_user_fetch_failed")

        zoom_user_data = user_info_resp.json()
        zoom_user_id = zoom_user_data["id"]
        zoom_email = zoom_user_data["email"]
        zoom_account_id = zoom_user_data.get("account_id", "")

        ZoomProfile.objects.update_or_create(
            user=user,
            defaults={
                "oauth_token": oauth_token,
                "zoom_user_id": zoom_user_id,
                "zoom_email": zoom_email,
                "zoom_account_id": zoom_account_id,
            },
        )

        return redirect("http://localhost:3000/zoom-integration/success")

    def redirect_with_error(self, reason):
        return redirect(f"http://localhost:3000/zoom-integration/error?reason={reason}")

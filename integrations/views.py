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
from organisations.models import Organisation, OrganisationMembership
from users.models import CustomUser
from django.db.models import Q

# Create your views here.


class ZoomOAuthStartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response({"error": "org_id is required"}, status=400)

        try:
            organisation = Organisation.objects.get(org_id=org_id)
        except Organisation.DoesNotExist:
            return Response({"error": "Invalid organisation"}, status=404)

        if not OrganisationMembership.objects.filter(user=request.user, organisation=organisation).exists():
            return Response({"error": "User not part of this organisation"}, status=403)

        state_data = f"{request.user.id}:{org_id}:{get_random_string(32)}"
        redirect_uri = "https://actionboard-backend-cdqe.onrender.com/api/integrations/zoom/oauth/callback/"

        query_params = {
            "response_type": "code",
            "client_id": settings.ZOOM_CLIENT_ID,
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
            user_id, org_id, _ = state.split(":")
        except ValueError:
            return self.redirect_with_error("invalid_state_format")

        try:
            user = CustomUser.objects.get(id=user_id)
            organisation = Organisation.objects.get(org_id=org_id)
        except (CustomUser.DoesNotExist, Organisation.DoesNotExist):
            return self.redirect_with_error("invalid_user_or_organisation")

        redirect_uri = f"{settings.BACKEND_URL}/api/integrations/zoom/oauth/callback/"
        response = requests.post(
            "https://zoom.us/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET)
        )

        if response.status_code != 200:
            return self.redirect_with_error("token_exchange_failed")

        token_data = response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_at = timezone.now() + timezone.timedelta(seconds=token_data["expires_in"])

        zoom_resp = requests.get(
            "https://api.zoom.us/v2/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if zoom_resp.status_code != 200:
            return self.redirect_with_error("zoom_user_fetch_failed")

        zoom_data = zoom_resp.json()
        zoom_user_id = zoom_data["id"]
        zoom_email = zoom_data["email"]
        zoom_account_id = zoom_data.get("account_id", "")

        # ✅ Disconnect any previous orgs using this Zoom user/account
        # ZoomProfile.objects.filter(
        #     Q(zoom_user_id=zoom_user_id) | Q(zoom_account_id=zoom_account_id)
        # ).delete()

        OAuthToken.objects.filter(
            Q(zoom_profile__zoom_user_id=zoom_user_id) | Q(zoom_profile__zoom_account_id=zoom_account_id),
            provider="zoom"
        ).delete()

        oauth_token, _ = OAuthToken.objects.update_or_create(
            user=user,
            organisation=organisation,
            provider="zoom",
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            },
        )

        zoom_resp = requests.get(
            "https://api.zoom.us/v2/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if zoom_resp.status_code != 200:
            return self.redirect_with_error("zoom_user_fetch_failed")

        zoom_data = zoom_resp.json()

        ZoomProfile.objects.update_or_create(
            user=user,
            organisation=organisation,
            defaults={
                "oauth_token": oauth_token,
                "zoom_user_id": zoom_data["id"],
                "zoom_email": zoom_data["email"],
                "zoom_account_id": zoom_data.get("account_id", ""),
            },
        )

        return redirect(f"{settings.FRONTEND_URL}?zoom_connected=true")

    def redirect_with_error(self, reason):
        return redirect(f"{settings.FRONTEND_URL}/zoom-integration/error?reason={reason}")

class ZoomConnectionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org_id = request.query_params.get("org_id")
        if not org_id:
            return Response({"error": "org_id is required"}, status=400)

        try:
            organisation = Organisation.objects.get(org_id=org_id)
            oauth_token = OAuthToken.objects.get(organisation=organisation, provider="zoom")
            zoom_profile = ZoomProfile.objects.get(organisation=organisation)
        except (Organisation.DoesNotExist, OAuthToken.DoesNotExist, ZoomProfile.DoesNotExist):
            return Response({"is_connected": False})

        is_expired = oauth_token.expires_at < timezone.now() if oauth_token.expires_at else False

        return Response({
            "is_connected": True,
            "user_info": {
                "email": zoom_profile.zoom_email,
                "zoom_user_id": zoom_profile.zoom_user_id,
                "account_id": zoom_profile.zoom_account_id,
            },
            "token_expiry": oauth_token.expires_at.isoformat(),
            "is_token_expired": is_expired,
        })



class ZoomDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        org_id = request.data.get("org_id")
        if not org_id:
            return Response({"error": "org_id is required"}, status=400)

        try:
            organisation = Organisation.objects.get(org_id=org_id)
            zoom_profile = ZoomProfile.objects.get(organisation=organisation)
            oauth_token = zoom_profile.oauth_token
        except (Organisation.DoesNotExist, ZoomProfile.DoesNotExist):
            return Response({"error": "Zoom connection not found"}, status=404)

        try:
            requests.post(
                "https://zoom.us/oauth/revoke",
                data={"token": oauth_token.access_token},
                headers={
                    "Authorization": f"Basic {settings.ZOOM_CLIENT_ID}:{settings.ZOOM_CLIENT_SECRET}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
        except Exception as e:
            print(f"Warning: Could not revoke Zoom token: {e}")

        zoom_profile.delete()
        oauth_token.delete()

        return Response({"success": True, "message": "Zoom disconnected for organisation"})

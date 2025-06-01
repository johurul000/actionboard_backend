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

        state_data = f"{user_id}:{random_state}" 

        redirect_uri = f"{settings.BACKEND_URL}/api/integrations/zoom/oauth/callback/"
        client_id = settings.ZOOM_CLIENT_ID

        query_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state_data,
        }

        authorize_url = f"https://zoom.us/oauth/authorize?{urlencode(query_params)}"

        return Response({"authorize_url": authorize_url})
    

#BY Azizr Rahman
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
        except (CustomUser.DoesNotExist, ValueError):
            return self.redirect_with_error("invalid_user_id")
        
        # Create or update OAuth token
        oauth_token, _ = OAuthToken.objects.update_or_create(
            user=user,
            provider="zoom",
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            },
        )
        
        # Get user info from Zoom
        user_info_url = "https://api.zoom.us/v2/users/me"
        user_info_headers = {"Authorization": f"Bearer {access_token}"}
        
        user_info_resp = requests.get(user_info_url, headers=user_info_headers)
        if user_info_resp.status_code != 200:
            return self.redirect_with_error("zoom_user_fetch_failed")
        
        zoom_user_data = user_info_resp.json()
        zoom_user_id = zoom_user_data["id"]
        zoom_email = zoom_user_data["email"]
        zoom_account_id = zoom_user_data.get("account_id", "")
        
        # Create or update ZoomProfile using oauth_token as lookup
        ZoomProfile.objects.update_or_create(
            oauth_token=oauth_token,  # Use oauth_token as lookup instead of user
            defaults={
                "user": user,  # Move user to defaults
                "zoom_user_id": zoom_user_id,
                "zoom_email": zoom_email,
                "zoom_account_id": zoom_account_id,
            },
        )
        
        return redirect(f"{settings.FRONTEND_URL}?zoom_connected=true")
    
    def redirect_with_error(self, reason):
        return redirect(f"{settings.FRONTEND_URL}/zoom-integration/error?reason={reason}")

#BY Azizr Rahman
class ZoomConnectionStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            oauth_token = OAuthToken.objects.get(user=request.user, provider="zoom")
            zoom_profile = ZoomProfile.objects.get(oauth_token=oauth_token)
            
            is_expired = oauth_token.expires_at < timezone.now() if oauth_token.expires_at else False
            
            return Response({
                "is_connected": True,
                "user_info": {
                    "email": zoom_profile.zoom_email,
                    "zoom_user_id": zoom_profile.zoom_user_id,
                    "account_id": zoom_profile.zoom_account_id,
                    "first_name": zoom_profile.zoom_email.split('@')[0] if zoom_profile.zoom_email else None,
                },
                "token_expiry": oauth_token.expires_at.isoformat() if oauth_token.expires_at else None,
                "is_token_expired": is_expired,
            })
        except (OAuthToken.DoesNotExist, ZoomProfile.DoesNotExist):
            return Response({
                "is_connected": False,
                "user_info": None,
                "token_expiry": None,
                "is_token_expired": False,
            })
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=500)


#BY Azizr Rahman
class ZoomDisconnectView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get the user's Zoom profile
            zoom_profile = ZoomProfile.objects.get(user=request.user)
            oauth_token = zoom_profile.oauth_token
            
            # Optional: Revoke the token with Zoom (recommended)
            try:
                revoke_url = "https://zoom.us/oauth/revoke"
                revoke_data = {
                    "token": oauth_token.access_token
                }
                revoke_headers = {
                    "Authorization": f"Basic {settings.ZOOM_CLIENT_ID}:{settings.ZOOM_CLIENT_SECRET}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                # Try to revoke the token, but don't fail if it doesn't work
                requests.post(revoke_url, data=revoke_data, headers=revoke_headers)
            except Exception as e:
                print(f"Warning: Could not revoke Zoom token: {e}")
            
            # Delete the ZoomProfile and OAuth token
            zoom_profile.delete()  # This will cascade delete the oauth_token due to OneToOneField
            
            return Response({
                "success": True,
                "message": "Successfully disconnected from Zoom"
            })
            
        except ZoomProfile.DoesNotExist:
            return Response({
                "success": False,
                "message": "No Zoom connection found"
            }, status=404)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Error disconnecting from Zoom: {str(e)}"
            }, status=500)

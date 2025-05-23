from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from .models import EmailOTP
from rest_framework_simplejwt.tokens import RefreshToken
import random
from rest_framework import generics
from .serializers import *
from .models import CustomUser
from dj_rest_auth.serializers import JWTSerializer

User = get_user_model()

class SendOTPView(APIView):
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = str(random.randint(100000, 999999))

            EmailOTP.objects.create(email=email, otp=otp)

            send_mail(
                subject='Your OTP Code',
                message=f'Your OTP code is: {otp}',
                from_email=None,
                recipient_list=[email]
            )
            return Response({'message': 'OTP sent successfully'}, status=200)
        return Response(serializer.errors, status=400)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            try:
                otp_obj = EmailOTP.objects.filter(email=email, otp=otp, is_used=False).latest('created_at')
            except EmailOTP.DoesNotExist:
                return Response({'error': 'Invalid OTP'}, status=400)

            if otp_obj.is_expired():
                return Response({'error': 'OTP expired'}, status=400)

            otp_obj.is_used = True
            otp_obj.save()

            user = CustomUser.objects.filter(email=email).first()
            if not user:
                return Response({'error': 'User not found'}, status=404)

            user.is_verified = True
            user.is_active = True
            user.save()

            tokens = get_tokens_for_user(user)

            return Response({
                'message': 'OTP verified. User activated and authenticated.',
                'access': tokens['access'],
                'refresh': tokens['refresh'],
            }, status=200)
        return Response(serializer.errors, status=400)
    

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response({
            "message": "An OTP has been sent to the given email",
            "user": serializer.data
        }, status=status.HTTP_201_CREATED)
    

class SignInView(APIView):
    def post(self, request):
        serializer = SignInSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:3000/"
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        user = self.user  # Set after login
        if user and not user.is_verified:
            user.is_verified = True
            user.save()

        # Generate JWT tokens manually
        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "pk": user.pk,
                "email": user.email,
            },
        }
        return Response(data, status=status.HTTP_200_OK)
    


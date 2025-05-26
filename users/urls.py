from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),

    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('register/', RegisterView.as_view(), name='register'),
    path('signin/', SignInView.as_view(), name='signin'),
    path('dj-rest-auth/google/', GoogleLogin.as_view(), name='google_login'),

    path('forgot-password/request-otp/', ForgotPasswordRequestOTPView.as_view(), name='forgot-password-request-otp'),
    path('forgot-password/verify-otp/', VerifyOTPForForgotPasswordView.as_view(), name='forgot-password-verify-otp'),
    path('forgot-password/reset/', ResetForgotPasswordView.as_view(), name='forgot-password-reset'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
import random
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import CustomUser, EmailOTP
from django.core.mail import send_mail
from django_countries.serializer_fields import CountryField as CountrySerializerField

class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    country = CountrySerializerField(required=False)

    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 
            'country', 'date_of_birth', 'password'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.is_active = False  # user inactive until OTP verified
        user.save()

        # Send OTP
        self.send_otp(user.email)
        return user

    def send_otp(self, email):
        otp = str(random.randint(100000, 999999))
        EmailOTP.objects.create(email=email, otp=otp)

        send_mail(
            subject='Your OTP Code',
            message=f'Your OTP code is: {otp}',
            from_email=None,
            recipient_list=[email],
        )
    

class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data['email']
        password = data['password']

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("User is not active")

        refresh = RefreshToken.for_user(user)

        return {
            "user": {
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "country":  str(user.country),
                "date_of_birth":  user.date_of_birth,
            },
            "token": str(refresh.access_token),
            "refreshToken": str(refresh),
        }

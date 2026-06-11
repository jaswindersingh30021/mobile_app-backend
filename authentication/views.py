from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import status
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPCode
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    ResendOTPSerializer,
    VerifyOTPSerializer,
)
from .utils import create_and_send_otp

User = get_user_model()

TokenSerializer = inline_serializer(
    name='TokenPair',
    fields={
        'access': serializers.CharField(),
        'refresh': serializers.CharField(),
    },
)

AuthUserSerializer = inline_serializer(
    name='AuthUser',
    fields={
        'id': serializers.UUIDField(),
        'name': serializers.CharField(),
        'email': serializers.EmailField(),
        'profile_image': serializers.URLField(allow_null=True, required=False),
    },
)

AuthTokenResponseSerializer = inline_serializer(
    name='AuthTokenResponse',
    fields={
        'success': serializers.BooleanField(),
        'message': serializers.CharField(required=False),
        'tokens': TokenSerializer,
        'user': AuthUserSerializer,
    },
)

SuccessMessageSerializer = inline_serializer(
    name='SuccessMessageResponse',
    fields={
        'success': serializers.BooleanField(),
        'message': serializers.CharField(),
    },
)


def _user_payload(user, request=None):
    profile_image = None
    if user.profile_image:
        profile_image = (
            request.build_absolute_uri(user.profile_image.url)
            if request
            else user.profile_image.url
        )
    return {
        'id': str(user.id),
        'name': user.name,
        'email': user.email,
        'profile_image': profile_image,
    }


def _token_payload(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


@extend_schema(
    tags=['Authentication'],
    summary='Register user and send OTP',
    request=RegisterSerializer,
    responses={
        201: inline_serializer(
            name='RegisterResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'email': serializers.EmailField(),
            },
        ),
        400: inline_serializer(
            name='ErrorResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
            },
        ),
    },
    examples=[
        OpenApiExample(
            'Register request',
            value={
                'name': 'John Doe',
                'email': 'john@example.com',
                'password': 'password123',
            },
            request_only=True,
        )
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': email,
            'name': serializer.validated_data['name'],
            'is_verified': False,
        },
    )

    if user.is_verified:
        return Response(
            {'success': False, 'message': 'User with this email already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.name = serializer.validated_data['name']
    user.username = user.username or email
    user.set_password(serializer.validated_data['password'])
    user.save()

    create_and_send_otp(email)

    return Response(
        {
            'success': True,
            'message': 'OTP sent to your email.',
            'email': email,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@extend_schema(
    tags=['Authentication'],
    summary='Verify OTP and return JWT tokens',
    request=VerifyOTPSerializer,
    responses={200: AuthTokenResponseSerializer},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_view(request):
    serializer = VerifyOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']

    try:
        otp = OTPCode.objects.get(
            email=email,
            code=code,
            is_used=False,
            expires_at__gt=timezone.now(),
        )
    except OTPCode.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Invalid or expired OTP code.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp.is_used = True
    otp.save(update_fields=['is_used'])

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'success': False, 'message': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    user.is_verified = True
    user.save(update_fields=['is_verified', 'updated_at'])

    return Response({
        'success': True,
        'message': 'Email verified successfully.',
        'tokens': _token_payload(user),
        'user': _user_payload(user, request),
    })


@extend_schema(
    tags=['Authentication'],
    summary='Resend OTP to email',
    request=ResendOTPSerializer,
    responses={
        200: inline_serializer(
            name='ResendOTPResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
            },
        )
    },
)
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp_view(request):
    serializer = ResendOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    if not User.objects.filter(email=email).exists():
        return Response(
            {'success': False, 'message': 'No account found with this email.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    create_and_send_otp(email)

    return Response({
        'success': True,
        'message': 'OTP resent to your email.',
    })


@extend_schema(
    tags=['Authentication'],
    summary='Login and return JWT tokens',
    request=LoginSerializer,
    responses={200: AuthTokenResponseSerializer},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    user = authenticate(username=email, password=password)

    if user is None:
        return Response(
            {'success': False, 'message': 'Invalid email or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_verified:
        create_and_send_otp(email)
        return Response(
            {
                'success': False,
                'message': 'Email not verified. A new OTP has been sent.',
                'requires_verification': True,
                'email': email,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    return Response({
        'success': True,
        'tokens': _token_payload(user),
        'user': _user_payload(user, request),
    })


@extend_schema(
    tags=['Authentication'],
    summary='Logout current user',
    description=(
        'JWT access tokens are stateless, so the mobile app should delete its '
        'stored access and refresh tokens after this call. A refresh token may '
        'be sent in the body for future blacklist support.'
    ),
    request=LogoutSerializer,
    responses={200: SuccessMessageSerializer},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return Response({
        'success': True,
        'message': 'Logged out successfully.',
    })


@extend_schema(
    tags=['Authentication'],
    summary='Send forgot password OTP',
    request=ForgotPasswordSerializer,
    responses={200: SuccessMessageSerializer},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_view(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'success': False, 'message': 'No account found with this email.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not user.is_verified:
        return Response(
            {'success': False, 'message': 'Please verify your email first.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    create_and_send_otp(email, purpose='Password Reset')

    return Response({
        'success': True,
        'message': 'Password reset OTP sent to your email.',
    })


@extend_schema(
    tags=['Authentication'],
    summary='Reset password using OTP',
    request=ResetPasswordSerializer,
    responses={200: SuccessMessageSerializer},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_view(request):
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']

    try:
        otp = OTPCode.objects.get(
            email=email,
            code=code,
            is_used=False,
            expires_at__gt=timezone.now(),
        )
    except OTPCode.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Invalid or expired OTP code.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(email=email, is_verified=True)
    except User.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Verified user not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    user.set_password(new_password)
    user.save()

    otp.is_used = True
    otp.save(update_fields=['is_used'])

    return Response({
        'success': True,
        'message': 'Password reset successfully.',
    })

# Create your views here.

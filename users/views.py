from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    AvatarUploadSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


@extend_schema(
    tags=['Users'],
    summary='Get or update current user profile',
    request=UserUpdateSerializer,
    responses={200: UserSerializer},
)
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile_view(request):
    user = request.user

    if request.method == 'GET':
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    serializer = UserUpdateSerializer(user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(UserSerializer(user, context={'request': request}).data)


@extend_schema(
    tags=['Users'],
    summary='Upload current user avatar',
    request=AvatarUploadSerializer,
    responses={
        200: inline_serializer(
            name='AvatarUploadResponse',
            fields={
                'success': serializers.BooleanField(),
                'profile_image_url': serializers.URLField(),
            },
        )
    },
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_avatar_view(request):
    serializer = AvatarUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user
    if user.profile_image:
        user.profile_image.delete(save=False)

    user.profile_image = serializer.validated_data['profile_image']
    user.save()

    return Response({
        'success': True,
        'profile_image_url': request.build_absolute_uri(user.profile_image.url),
    })

# Create your views here.

from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'bio',
            'profile_image_url',
            'is_verified',
            'created_at',
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'created_at']

    @extend_schema_field(OpenApiTypes.URI)
    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return None
        request = self.context.get('request')
        return (
            request.build_absolute_uri(obj.profile_image.url)
            if request
            else obj.profile_image.url
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'phone', 'bio']


class AvatarUploadSerializer(serializers.Serializer):
    profile_image = serializers.ImageField()

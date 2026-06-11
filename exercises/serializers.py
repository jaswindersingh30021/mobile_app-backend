import json

from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from rest_framework import serializers

from .models import Exercise
from .utils import generate_video_thumbnail


def build_absolute_file_url(obj, field_name, request=None):
    file_field = getattr(obj, field_name)
    if not file_field:
        return None
    return request.build_absolute_uri(file_field.url) if request else file_field.url


class ExerciseListSerializer(serializers.ModelSerializer):
    trainer_name = serializers.CharField(source='user.name', read_only=True)
    trainer_image = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    media_type = serializers.CharField(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = [
            'id',
            'title',
            'category',
            'difficulty',
            'duration',
            'media_type',
            'image_url',
            'thumbnail_url',
            'trainer_name',
            'trainer_image',
            'is_bookmarked',
            'created_at',
        ]

    @extend_schema_field(OpenApiTypes.URI)
    def get_image_url(self, obj):
        request = self.context.get('request')
        return build_absolute_file_url(obj, 'image', request)

    @extend_schema_field(OpenApiTypes.URI)
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.video and obj.video_thumbnail:
            return build_absolute_file_url(obj, 'video_thumbnail', request)
        return build_absolute_file_url(obj, 'image', request)

    @extend_schema_field(OpenApiTypes.URI)
    def get_trainer_image(self, obj):
        if not obj.user.profile_image:
            return None
        request = self.context.get('request')
        return (
            request.build_absolute_uri(obj.user.profile_image.url)
            if request
            else obj.user.profile_image.url
        )

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarked_by.filter(user=request.user).exists()
        return False


class ExerciseDetailSerializer(serializers.ModelSerializer):
    trainer_name = serializers.CharField(source='user.name', read_only=True)
    trainer_image = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    media_type = serializers.CharField(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = [
            'id',
            'title',
            'category',
            'difficulty',
            'duration',
            'description',
            'media_type',
            'image_url',
            'thumbnail_url',
            'video_url',
            'muscles',
            'steps',
            'sets',
            'reps',
            'status',
            'trainer_name',
            'trainer_image',
            'is_bookmarked',
            'created_at',
            'updated_at',
        ]

    @extend_schema_field(OpenApiTypes.URI)
    def get_image_url(self, obj):
        request = self.context.get('request')
        return build_absolute_file_url(obj, 'image', request)

    @extend_schema_field(OpenApiTypes.URI)
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.video and obj.video_thumbnail:
            return build_absolute_file_url(obj, 'video_thumbnail', request)
        return build_absolute_file_url(obj, 'image', request)

    @extend_schema_field(OpenApiTypes.URI)
    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video:
            return build_absolute_file_url(obj, 'video', request)
        return obj.video_url

    @extend_schema_field(OpenApiTypes.URI)
    def get_trainer_image(self, obj):
        if not obj.user.profile_image:
            return None
        request = self.context.get('request')
        return (
            request.build_absolute_uri(obj.user.profile_image.url)
            if request
            else obj.user.profile_image.url
        )

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarked_by.filter(user=request.user).exists()
        return False


class ExerciseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            'title',
            'category',
            'difficulty',
            'duration',
            'description',
            'image',
            'video',
            'video_url',
            'muscles',
            'steps',
            'sets',
            'reps',
            'status',
        ]

    def to_internal_value(self, data):
        if hasattr(data, 'lists'):
            mutable = {}
            for key, values in data.lists():
                mutable[key] = values if len(values) > 1 else values[0]
        else:
            mutable = data.copy()

        for field in ('muscles', 'steps'):
            value = mutable.get(field)
            if isinstance(value, str):
                try:
                    mutable[field] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return super().to_internal_value(mutable)

    def validate_muscles(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Muscles must be a list.')
        return value

    def validate_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Steps must be a list.')
        return value

    def validate(self, attrs):
        image = attrs.get('image')
        video = attrs.get('video')

        if self.instance:
            image = image if image is not None else self.instance.image
            video = video if video is not None else self.instance.video

        if image and video:
            raise serializers.ValidationError(
                'Upload either an image or a video, not both.'
            )
        return attrs

    def create(self, validated_data):
        exercise = super().create(validated_data)
        if exercise.video:
            generate_video_thumbnail(exercise)
            if exercise.video_thumbnail:
                exercise.save(update_fields=['video_thumbnail'])
        return exercise

    def update(self, instance, validated_data):
        old_video_name = instance.video.name if instance.video else None
        exercise = super().update(instance, validated_data)
        new_video_name = exercise.video.name if exercise.video else None
        if new_video_name and new_video_name != old_video_name:
            generate_video_thumbnail(exercise)
            if exercise.video_thumbnail:
                exercise.save(update_fields=['video_thumbnail'])
        return exercise

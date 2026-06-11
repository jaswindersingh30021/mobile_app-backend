from rest_framework import serializers

from exercises.serializers import ExerciseListSerializer

from .models import Bookmark


class BookmarkSerializer(serializers.ModelSerializer):
    exercise = ExerciseListSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ['id', 'exercise', 'created_at']

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from exercises.models import Exercise

from .models import Bookmark
from .serializers import BookmarkSerializer


BookmarkToggleResponseSerializer = inline_serializer(
    name='BookmarkToggleResponse',
    fields={
        'success': serializers.BooleanField(),
        'is_bookmarked': serializers.BooleanField(),
        'message': serializers.CharField(),
    },
)

BookmarkListResponseSerializer = inline_serializer(
    name='BookmarkListResponse',
    fields={
        'count': serializers.IntegerField(),
        'results': BookmarkSerializer(many=True),
    },
)


@extend_schema(
    tags=['Bookmarks'],
    summary='Toggle bookmark for an exercise',
    request=None,
    responses={200: BookmarkToggleResponseSerializer},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_bookmark_view(request, exercise_id):
    try:
        exercise = Exercise.objects.get(pk=exercise_id)
    except Exercise.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Exercise not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user,
        exercise=exercise,
    )

    if not created:
        bookmark.delete()
        return Response({
            'success': True,
            'is_bookmarked': False,
            'message': 'Bookmark removed.',
        })

    return Response({
        'success': True,
        'is_bookmarked': True,
        'message': 'Exercise bookmarked.',
    })


@extend_schema(
    tags=['Bookmarks'],
    summary='List current user bookmarked exercises',
    responses={200: BookmarkListResponseSerializer},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bookmark_list_view(request):
    bookmarks = (
        Bookmark.objects
        .filter(user=request.user)
        .select_related('exercise', 'exercise__user')
    )
    serializer = BookmarkSerializer(
        bookmarks,
        many=True,
        context={'request': request},
    )
    return Response({
        'count': bookmarks.count(),
        'results': serializer.data,
    })

# Create your views here.

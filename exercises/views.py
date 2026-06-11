from django.db import models
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import status
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Exercise
from .serializers import (
    ExerciseCreateSerializer,
    ExerciseDetailSerializer,
    ExerciseListSerializer,
)


class ExercisePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


ExerciseListResponseSerializer = inline_serializer(
    name='ExerciseListResponse',
    fields={
        'count': serializers.IntegerField(),
        'next': serializers.URLField(allow_null=True),
        'previous': serializers.URLField(allow_null=True),
        'results': ExerciseListSerializer(many=True),
    },
)

ExerciseDetailListResponseSerializer = inline_serializer(
    name='ExerciseDetailListResponse',
    fields={
        'count': serializers.IntegerField(),
        'results': ExerciseDetailSerializer(many=True),
    },
)


@extend_schema(
    methods=['GET'],
    tags=['Exercises'],
    operation_id='exercise_list',
    summary='List published exercises',
    parameters=[
        OpenApiParameter(
            name='search',
            description='Search by title, category, or trainer name.',
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name='category',
            description='Filter by exercise category.',
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name='difficulty',
            description='Filter by Beginner, Intermediate, or Advanced.',
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name='page',
            description='Page number for paginated results.',
            required=False,
            type=int,
        ),
        OpenApiParameter(
            name='page_size',
            description='Number of exercises per page. Maximum 50.',
            required=False,
            type=int,
        ),
    ],
    responses={200: ExerciseListResponseSerializer},
)
@extend_schema(
    methods=['POST'],
    tags=['Exercises'],
    operation_id='exercise_create',
    summary='Create exercise',
    request=ExerciseCreateSerializer,
    responses={201: ExerciseDetailSerializer},
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def exercise_list_view(request):
    if request.method == 'GET':
        exercises = Exercise.objects.filter(status='Published').select_related('user')

        search = request.query_params.get('search', '').strip()
        if search:
            exercises = exercises.filter(
                models.Q(title__icontains=search)
                | models.Q(category__icontains=search)
                | models.Q(user__name__icontains=search)
            )

        category = request.query_params.get('category', '').strip()
        if category:
            exercises = exercises.filter(category__iexact=category)

        difficulty = request.query_params.get('difficulty', '').strip()
        if difficulty:
            exercises = exercises.filter(difficulty__iexact=difficulty)

        paginator = ExercisePagination()
        page = paginator.paginate_queryset(exercises, request)
        serializer = ExerciseListSerializer(
            page,
            many=True,
            context={'request': request},
        )
        return paginator.get_paginated_response(serializer.data)

    serializer = ExerciseCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    exercise = serializer.save(user=request.user)
    return Response(
        ExerciseDetailSerializer(exercise, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    methods=['GET'],
    tags=['Exercises'],
    operation_id='exercise_retrieve',
    summary='Get exercise detail',
    responses={200: ExerciseDetailSerializer},
)
@extend_schema(
    methods=['PUT'],
    tags=['Exercises'],
    operation_id='exercise_update',
    summary='Update own exercise',
    request=ExerciseCreateSerializer,
    responses={200: ExerciseDetailSerializer},
)
@extend_schema(
    methods=['DELETE'],
    tags=['Exercises'],
    operation_id='exercise_delete',
    summary='Delete own exercise',
    responses={200: inline_serializer(
        name='ExerciseDeleteResponse',
        fields={
            'success': serializers.BooleanField(),
            'message': serializers.CharField(),
        },
    )},
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def exercise_detail_view(request, pk):
    try:
        exercise = Exercise.objects.select_related('user').get(pk=pk)
    except Exercise.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Exercise not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'GET':
        serializer = ExerciseDetailSerializer(
            exercise,
            context={'request': request},
        )
        return Response(serializer.data)

    if exercise.user != request.user:
        return Response(
            {
                'success': False,
                'message': 'You can only modify your own exercises.',
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'PUT':
        serializer = ExerciseCreateSerializer(
            exercise,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        exercise = serializer.save()
        return Response(
            ExerciseDetailSerializer(exercise, context={'request': request}).data
        )

    exercise.delete()
    return Response({
        'success': True,
        'message': 'Exercise deleted successfully.',
    })


@extend_schema(
    tags=['Exercises'],
    summary='List current user exercises',
    responses={200: ExerciseDetailListResponseSerializer},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_exercises_view(request):
    exercises = Exercise.objects.filter(user=request.user).select_related('user')
    serializer = ExerciseDetailSerializer(
        exercises,
        many=True,
        context={'request': request},
    )
    return Response({
        'count': exercises.count(),
        'results': serializer.data,
    })

# Create your views here.

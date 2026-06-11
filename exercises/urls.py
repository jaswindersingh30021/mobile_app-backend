from django.urls import path

from . import views

urlpatterns = [
    path('', views.exercise_list_view, name='exercise-list'),
    path('mine/', views.my_exercises_view, name='my-exercises'),
    path('<uuid:pk>/', views.exercise_detail_view, name='exercise-detail'),
]

from django.urls import path

from . import views

urlpatterns = [
    path('', views.bookmark_list_view, name='bookmark-list'),
    path('<uuid:exercise_id>/toggle/', views.toggle_bookmark_view, name='toggle-bookmark'),
]

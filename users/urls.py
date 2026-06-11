from django.urls import path

from . import views

urlpatterns = [
    path('me/', views.user_profile_view, name='user-profile'),
    path('me/avatar/', views.upload_avatar_view, name='upload-avatar'),
]

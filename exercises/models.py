import uuid

from django.conf import settings
from django.db import models


class Exercise(models.Model):
    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    STATUS_CHOICES = [
        ('Published', 'Published'),
        ('Draft', 'Draft'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exercises',
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='Beginner',
    )
    duration = models.CharField(max_length=50)
    description = models.TextField()
    image = models.ImageField(upload_to='exercises/', blank=True, null=True)
    video = models.FileField(upload_to='exercise_videos/', blank=True, null=True)
    video_thumbnail = models.ImageField(
        upload_to='exercise_thumbnails/',
        blank=True,
        null=True,
    )
    video_url = models.URLField(blank=True, null=True)
    muscles = models.JSONField(default=list, blank=True)
    steps = models.JSONField(default=list, blank=True)
    sets = models.CharField(max_length=50, blank=True, null=True)
    reps = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Published',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def media_type(self):
        if self.video:
            return 'video'
        if self.image:
            return 'image'
        if self.video_url:
            return 'external_video'
        return None

# Create your models here.

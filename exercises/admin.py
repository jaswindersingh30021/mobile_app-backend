from django.contrib import admin

from .models import Exercise


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'difficulty', 'status', 'created_at')
    list_filter = ('category', 'difficulty', 'status', 'created_at')
    search_fields = ('title', 'category', 'user__email', 'user__name')

# Register your models here.

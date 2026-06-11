from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {'fields': ('name', 'phone', 'bio', 'profile_image', 'is_verified')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('name', 'email')}),
    )
    list_display = ('email', 'name', 'is_verified', 'is_staff', 'created_at')
    search_fields = ('email', 'name', 'username')
    ordering = ('email',)

# Register your models here.

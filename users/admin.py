from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        "id",
        "email",
        "username",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-date_joined"]

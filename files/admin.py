from django.contrib import admin
from .models import File, SharedAccess


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "size", "uploaded_at", "is_shared")
    list_filter = ["is_shared", "uploaded_at"]
    search_fields = ["name", "user__username", "user__email"]
    readonly_fields = ["uploaded_at"]
    fields = [
        "user",
        "name",
        "size",
        "s3_key",
        "md5_hash",
        "mime_type",
        "is_shared",
        "uploaded_at",
    ]


@admin.register(SharedAccess)
class SharedAccessAdmin(admin.ModelAdmin):
    list_display = ("file", "shared_with", "permission", "created_at", "expires_at")
    list_filter = ["permission"]
    search_fields = ["file__name", "shared_with__email"]

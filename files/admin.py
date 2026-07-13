from django.contrib import admin
from .models import File


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "size", "uploaded_at"]
    list_filter = ["uploaded_at"]
    search_fields = ["name", "user__username", "user__email"]
    readonly_fields = ["uploaded_at"]
    fields = ["user", "name", "size", "s3_key", "md5_hash", "mime_type", "uploaded_at"]

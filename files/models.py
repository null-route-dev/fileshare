from django.db import models
from django.conf import settings


class File(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files"
    )
    name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    s3_key = models.CharField(max_length=255, unique=True)
    md5_hash = models.CharField(max_length=32, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "files"
        ordering = ["-uploaded_at"]

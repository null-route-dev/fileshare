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
    is_shared = models.BooleanField(default=False)

    class Meta:
        db_table = "files"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name


class SharedAccess(models.Model):
    PERMISSION_CHOICES = (
        ("view", "View"),
        ("edit", "Edit"),
    )

    file = models.ForeignKey(
        File, on_delete=models.CASCADE, related_name="shared_accesses"
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shared_files"
    )
    permission = models.CharField(
        max_length=10, choices=PERMISSION_CHOICES, default="view"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "shared_access"
        unique_together = ("file", "shared_with")

    def __str__(self):
        return f"{self.file.name} -> {self.shared_with.email}"

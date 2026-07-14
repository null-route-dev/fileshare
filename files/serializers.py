from rest_framework import serializers
from .models import File


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ["id", "name", "size", "mime_type", "uploaded_at", "user"]
        read_only_fields = ["id", "size", "mime_type", "uploaded_at", "user"]


class FileCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    name = serializers.CharField(required=False, allow_blank=True)

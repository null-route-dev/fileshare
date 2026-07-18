from rest_framework import serializers
from .models import File, SharedAccess


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ["id", "name", "size", "mime_type", "uploaded_at", "is_shared", "user"]
        read_only_fields = ["id", "size", "mime_type", "uploaded_at", "user"]


class FileCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    name = serializers.CharField(required=False, allow_blank=True)


class SharedAccessSerializer(serializers.ModelSerializer):
    shared_with_email = serializers.EmailField(
        source="shared_with.email", read_only=True
    )
    file_name = serializers.CharField(source="file.name", read_only=True)

    class Meta:
        model = SharedAccess
        fields = [
            "id",
            "file",
            "shared_with",
            "shared_with_email",
            "permission",
            "created_at",
            "expires_at",
            "file_name",
        ]
        read_only_fields = ["id", "created_at"]


class ShareFileSerializer(serializers.Serializer):
    email = serializers.EmailField()
    permission = serializers.ChoiceField(
        choices=SharedAccess.PERMISSION_CHOICES, default="view"
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class TransferOwnershipSerializer(serializers.Serializer):
    new_owner_email = serializers.EmailField()

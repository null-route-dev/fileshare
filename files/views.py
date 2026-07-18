from django.db import models
from django.http import FileResponse
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import File, SharedAccess
from .serializers import (
    FileSerializer,
    FileCreateSerializer,
    SharedAccessSerializer,
    ShareFileSerializer,
    TransferOwnershipSerializer,
)
from .services import FileService, SharingService
from .permissions import IsOwnerOrReadOnly


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        return File.objects.filter(
            models.Q(user=user) | models.Q(shared_accesses__shared_with=user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        serializer = FileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data["file"]
        name = serializer.validated_data.get("name", "")

        file_obj = FileService.create_file(
            user=request.user, uploaded_file=uploaded_file, name=name
        )
        return Response(FileSerializer(file_obj).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        file_obj = self.get_object()
        if file_obj.user != request.user:
            return Response(
                {"error": "Only the owner can delete this file."},
                status=status.HTTP_403_FORBIDDEN,
            )
        FileService.delete_file(file_obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        file_obj = self.get_object()
        if not default_storage.exists(file_obj.s3_key):
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if file_obj.user != request.user:
            try:
                share = SharedAccess.objects.get(
                    file=file_obj, shared_with=request.user
                )
                if share.permission not in ["view", "edit"]:
                    return Response(
                        {"error": "You do not have permission to download this file."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except SharedAccess.DoesNotExist:
                return Response(
                    {"error": "You do not have permission to download this file."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        file_handle = default_storage.open(file_obj.s3_key, "rb")
        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=file_obj.name,
            content_type="application/octet-stream",
        )
        response["Content-Disposition"] = f'attachment; filename="{file_obj.name}"'
        return response

    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        file_obj = self.get_object()
        if file_obj.user != request.user:
            return Response(
                {"error": "Only the owner can share this file."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ShareFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            share = SharingService.share_file(
                file_obj=file_obj,
                owner=request.user,
                email=serializer.validated_data["email"],
                permission=serializer.validated_data["permission"],
                expires_at=serializer.validated_data.get("expires_at"),
            )
            return Response(
                SharedAccessSerializer(share).data, status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {"errors": e.message_dict}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get"], url_path="shares")
    def shares(self, request, pk=None):
        file_obj = self.get_object()
        if file_obj.user != request.user:
            return Response(
                {"error": "Only the owner can view shares."},
                status=status.HTTP_403_FORBIDDEN,
            )

        shares = SharedAccess.objects.filter(file=file_obj)
        serializer = SharedAccessSerializer(shares, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["delete"], url_path="shares/(?P<share_id>[^/.]+)")
    def remove_share(self, request, pk=None, share_id=None):
        file_obj = self.get_object()
        if file_obj.user != request.user:
            return Response(
                {"error": "Only the owner can remove shares."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            share = SharedAccess.objects.get(id=share_id, file=file_obj)
        except SharedAccess.DoesNotExist:
            return Response(
                {"error": "Share record not found."}, status=status.HTTP_404_NOT_FOUND
            )

        share.delete()
        if not SharedAccess.objects.filter(file=file_obj).exists():
            file_obj.is_shared = False
            file_obj.save(update_fields=["is_shared"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="shared-with-me")
    def shared_with_me(self, request):
        files = SharingService.get_shared_files_for_user(request.user)
        serializer = FileSerializer(files, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer_ownership(self, request, pk=None):
        file_obj = self.get_object()
        if file_obj.user != request.user:
            return Response(
                {"error": "Only the owner can transfer ownership."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_file = SharingService.transfer_ownership(
                file_obj=file_obj,
                current_owner=request.user,
                new_owner_email=serializer.validated_data["new_owner_email"],
            )
            return Response(
                FileSerializer(updated_file).data, status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(
                {"errors": e.message_dict}, status=status.HTTP_400_BAD_REQUEST
            )

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse
from django.core.files.storage import default_storage
from .models import File
from .serializers import FileSerializer, FileCreateSerializer
from .services import FileService
from .permissions import IsOwnerOrReadOnly


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = FileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_obj = FileService.create_file(
            user=request.user,
            uploaded_file=serializer.validated_data["file"],
            name=serializer.validated_data.get("name", ""),
        )
        return Response(FileSerializer(file_obj).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        file_obj = self.get_object()
        FileService.delete_file(file_obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        file_obj = self.get_object()
        if not default_storage.exists(file_obj.s3_key):
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )
        file_handle = default_storage.open(file_obj.s3_key, "rb")
        response = FileResponse(file_handle, as_attachment=True, filename=file_obj.name)
        return response

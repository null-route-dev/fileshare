import mimetypes
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from .models import File


class FileService:
    @staticmethod
    def create_file(user, uploaded_file, name=None):
        if not name:
            name = uploaded_file.name
        filename = get_valid_filename(name)
        path = default_storage.save(
            f"files/{filename}", ContentFile(uploaded_file.read())
        )
        size = uploaded_file.size
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        file_obj = File.objects.create(
            user=user,
            name=name,
            size=size,
            s3_key=path,
            mime_type=mime_type,
            md5_hash="",
        )
        return file_obj

    @staticmethod
    def delete_file(file_obj):
        if file_obj.s3_key:
            default_storage.delete(file_obj.s3_key)
        file_obj.delete()

    @staticmethod
    def get_file_path(file_obj):
        return default_storage.path(file_obj.s3_key) if file_obj.s3_key else None

import mimetypes
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from django.core.exceptions import ValidationError
from .models import File, SharedAccess
from users.models import User


class FileService:
    @staticmethod
    def create_file(user, uploaded_file, name=None):
        if not name:
            name = uploaded_file.name
        filename = get_valid_filename(name)
        content = ContentFile(uploaded_file.read())
        path = default_storage.save(f"files/{filename}", content)
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
        if file_obj.s3_key and default_storage.exists(file_obj.s3_key):
            default_storage.delete(file_obj.s3_key)
        file_obj.delete()


class SharingService:
    @staticmethod
    def share_file(file_obj, owner, email, permission, expires_at=None):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError({"email": "User with this email does not exist."})

        if file_obj.user != owner:
            raise ValidationError({"error": "Only the owner can share this file."})

        if user == owner:
            raise ValidationError({"error": "You cannot share a file with yourself."})

        shared_access, created = SharedAccess.objects.get_or_create(
            file=file_obj,
            shared_with=user,
            defaults={"permission": permission, "expires_at": expires_at},
        )
        if not created:
            shared_access.permission = permission
            shared_access.expires_at = expires_at
            shared_access.save()

        file_obj.is_shared = True
        file_obj.save(update_fields=["is_shared"])

        return shared_access

    @staticmethod
    def remove_access(share_id, owner):
        try:
            share = SharedAccess.objects.get(id=share_id)
        except SharedAccess.DoesNotExist:
            raise ValidationError({"error": "Access record not found."})

        if share.file.user != owner:
            raise ValidationError({"error": "Only the owner can remove access."})

        share.delete()
        if not SharedAccess.objects.filter(file=share.file).exists():
            share.file.is_shared = False
            share.file.save(update_fields=["is_shared"])

    @staticmethod
    def get_file_shares(file_obj, owner):
        if file_obj.user != owner:
            raise ValidationError({"error": "Only the owner can view shares."})
        return SharedAccess.objects.filter(file=file_obj)

    @staticmethod
    def get_shared_files_for_user(user):
        return File.objects.filter(shared_accesses__shared_with=user).distinct()

    @staticmethod
    def transfer_ownership(file_obj, current_owner, new_owner_email):
        if file_obj.user != current_owner:
            raise ValidationError({"error": "Only the owner can transfer ownership."})

        try:
            new_owner = User.objects.get(email=new_owner_email)
        except User.DoesNotExist:
            raise ValidationError({"email": "User with this email does not exist."})

        if new_owner == current_owner:
            raise ValidationError({"error": "Cannot transfer to yourself."})

        file_obj.user = new_owner
        file_obj.save(update_fields=["user"])

        SharedAccess.objects.filter(file=file_obj).delete()
        file_obj.is_shared = False
        file_obj.save(update_fields=["is_shared"])

        return file_obj

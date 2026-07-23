import uuid
import time
import io
import mimetypes
import secrets
import logging
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from django.core.cache import cache
from django.core.exceptions import ValidationError
from .models import File, SharedAccess
from users.models import User


logger = logging.getLogger("fileshare")


class FileService:
    @staticmethod
    def create_file(user, uploaded_file, name=None):
        try:
            if not name:
                name = uploaded_file.name
            filename = get_valid_filename(name)
            unique_id = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            s3_key = f"files/{unique_id}_{filename}"

            content = ContentFile(uploaded_file.read())
            path = default_storage.save(s3_key, content)
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

            logger.info(
                f"File created: {file_obj.id} - {file_obj.name} by {user.email}"
            )
            return file_obj

        except Exception as e:
            logger.error(f"Failed to create file for {user.email}: {str(e)}")
            raise

    @staticmethod
    def delete_file(file_obj):
        try:
            if file_obj.s3_key and default_storage.exists(file_obj.s3_key):
                default_storage.delete(file_obj.s3_key)
                logger.info(f"File deleted from storage: {file_obj.s3_key}")
            file_obj.delete()
            logger.info(f"File record deleted: {file_obj.id} - {file_obj.name}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_obj.id}: {str(e)}")
            raise

    @staticmethod
    def generate_preview(file_obj, size=(200, 200)):
        if not file_obj.mime_type.startswith("image/"):
            return None

        if not default_storage.exists(file_obj.s3_key):
            logger.warning(f"Original file not found for preview: {file_obj.s3_key}")
            return None

        try:
            with default_storage.open(file_obj.s3_key, "rb") as f:
                img = Image.open(f)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                preview_io = io.BytesIO()
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")
                img.save(preview_io, format="JPEG", quality=85)
                preview_io.seek(0)
                logger.info(f"Preview generated for file {file_obj.id}")
                return preview_io
        except Exception as e:
            logger.error(f"Failed to generate preview for file {file_obj.id}: {str(e)}")
            return None


class SharingService:
    @staticmethod
    def share_file(file_obj, owner, email, permission, expires_at=None):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"Share attempt failed: user {email} not found")
            raise ValidationError({"email": "User with this email does not exist."})

        if file_obj.user != owner:
            logger.warning(
                f"Share attempt failed: {owner.email} is not owner of file {file_obj.id}"
            )
            raise ValidationError({"error": "Only the owner can share this file."})

        if user == owner:
            logger.warning(
                f"Share attempt failed: {owner.email} tried to share with self"
            )
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
            logger.info(f"Share updated for file {file_obj.id} with {user.email}")
        else:
            logger.info(f"Share created for file {file_obj.id} with {user.email}")

        file_obj.is_shared = True
        file_obj.save(update_fields=["is_shared"])

        return shared_access

    @staticmethod
    def remove_access(share_id, owner):
        try:
            share = SharedAccess.objects.get(id=share_id)
        except SharedAccess.DoesNotExist:
            logger.warning(f"Remove access failed: share {share_id} not found")
            raise ValidationError({"error": "Access record not found."})

        if share.file.user != owner:
            logger.warning(
                f"Remove access failed: {owner.email} is not owner of file {share.file.id}"
            )
            raise ValidationError({"error": "Only the owner can remove access."})

        file_id = share.file.id
        share.delete()
        logger.info(f"Share removed: {share_id} from file {file_id}")

        if not SharedAccess.objects.filter(file_id=file_id).exists():
            File.objects.filter(id=file_id).update(is_shared=False)
            logger.info(f"File {file_id} is no longer shared")

    @staticmethod
    def get_file_shares(file_obj, owner):
        if file_obj.user != owner:
            logger.warning(
                f"View shares failed: {owner.email} is not owner of file {file_obj.id}"
            )
            raise ValidationError({"error": "Only the owner can view shares."})
        return SharedAccess.objects.filter(file=file_obj)

    @staticmethod
    def get_shared_files_for_user(user):
        return File.objects.filter(shared_accesses__shared_with=user).distinct()

    @staticmethod
    def transfer_ownership(file_obj, current_owner, new_owner_email):
        if file_obj.user != current_owner:
            logger.warning(
                f"Transfer failed: {current_owner.email} is not owner of file {file_obj.id}"
            )
            raise ValidationError({"error": "Only the owner can transfer ownership."})

        try:
            new_owner = User.objects.get(email=new_owner_email)
        except User.DoesNotExist:
            logger.warning(f"Transfer failed: new owner {new_owner_email} not found")
            raise ValidationError({"email": "User with this email does not exist."})

        if new_owner == current_owner:
            logger.warning(
                f"Transfer failed: {current_owner.email} tried to transfer to self"
            )
            raise ValidationError({"error": "Cannot transfer to yourself."})

        file_obj.user = new_owner
        file_obj.save(update_fields=["user"])
        logger.info(
            f"Ownership transferred: file {file_obj.id} from {current_owner.email} to {new_owner.email}"
        )

        SharedAccess.objects.filter(file=file_obj).delete()
        file_obj.is_shared = False
        file_obj.save(update_fields=["is_shared"])
        logger.info(f"Shares removed after ownership transfer for file {file_obj.id}")

        return file_obj

    @staticmethod
    def generate_public_link(file_obj, owner, expires_in_seconds=3600):
        if file_obj.user != owner:
            logger.warning(
                f"Public link generation failed: {owner.email} is not owner of file {file_obj.id}"
            )
            raise ValidationError(
                {"error": "Only the owner can generate a public link."}
            )

        token = secrets.token_urlsafe(32)
        cache_key = f"public_link:{token}"
        cache.set(cache_key, file_obj.id, timeout=expires_in_seconds)
        logger.info(
            f"Public link generated for file {file_obj.id} by {owner.email}, expires in {expires_in_seconds}s"
        )
        return token

    @staticmethod
    def get_file_from_public_token(token):
        cache_key = f"public_link:{token}"
        file_id = cache.get(cache_key)
        if not file_id:
            logger.warning(
                f"Public link access failed: token {token} not found or expired"
            )
            raise ValidationError({"error": "Invalid or expired link."})
        cache.delete(cache_key)
        logger.info(f"Public link consumed: file {file_id} downloaded via token")
        return file_id

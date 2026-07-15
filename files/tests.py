import time

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from users.models import User
from files.models import File
from files.services import FileService


pytestmark = pytest.mark.django_db


class TestFileModel:
    def test_create_file(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        file_obj = File.objects.create(
            user=user,
            name="test.txt",
            size=1024,
            s3_key="files/test.txt",
            mime_type="text/plain",
        )
        assert file_obj.name == "test.txt"
        assert file_obj.size == 1024
        assert file_obj.s3_key == "files/test.txt"
        assert file_obj.mime_type == "text/plain"

    def test_file_ordering(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        File.objects.create(user=user, name="old.txt", size=100, s3_key="files/old.txt")
        time.sleep(0.1)
        File.objects.create(user=user, name="new.txt", size=200, s3_key="files/new.txt")
        files = File.objects.all()
        assert files[0].name == "new.txt"
        assert files[1].name == "old.txt"


class TestFileService:
    def test_create_file(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(user, uploaded, "custom_name.txt")
        assert file_obj.name == "custom_name.txt"
        assert file_obj.size == 7
        assert file_obj.mime_type == "text/plain"
        assert file_obj.s3_key.startswith("files/")
        assert default_storage.exists(file_obj.s3_key)
        default_storage.delete(file_obj.s3_key)

    def test_delete_file(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(user, uploaded)
        assert default_storage.exists(file_obj.s3_key)
        FileService.delete_file(file_obj)
        assert not default_storage.exists(file_obj.s3_key)
        assert not File.objects.filter(id=file_obj.id).exists()


class TestFileAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="testpass"
        )
        login_data = {"email": "test@example.com", "password": "testpass"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        self.access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        self.list_url = reverse("files-list")

    def test_list_files_empty(self):
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_list_files(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(self.user, uploaded)
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == file_obj.id
        default_storage.delete(file_obj.s3_key)

    def test_create_file(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        data = {"file": uploaded, "name": "custom.txt"}
        response = self.client.post(self.list_url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "custom.txt"
        assert response.data["size"] == 7
        assert response.data["mime_type"] == "text/plain"
        file_id = response.data["id"]
        file_obj = File.objects.get(id=file_id)
        assert default_storage.exists(file_obj.s3_key)
        default_storage.delete(file_obj.s3_key)

    def test_create_file_without_name(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        data = {"file": uploaded}
        response = self.client.post(self.list_url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "test.txt"
        file_id = response.data["id"]
        file_obj = File.objects.get(id=file_id)
        default_storage.delete(file_obj.s3_key)

    def test_retrieve_file(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(self.user, uploaded)
        detail_url = reverse("files-detail", args=[file_obj.id])
        response = self.client.get(detail_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == file_obj.id
        default_storage.delete(file_obj.s3_key)

    def test_download_file(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(self.user, uploaded)
        download_url = reverse("files-download", args=[file_obj.id])
        response = self.client.get(download_url)
        assert response.status_code == status.HTTP_200_OK
        assert (
            response["Content-Disposition"] == f'attachment; filename="{file_obj.name}"'
        )
        content = b"".join(response.streaming_content)
        assert content == b"content"
        default_storage.delete(file_obj.s3_key)

    def test_download_nonexistent_file(self):
        file_obj = File.objects.create(
            user=self.user, name="missing.txt", size=0, s3_key="files/missing.txt"
        )
        download_url = reverse("files-download", args=[file_obj.id])
        response = self.client.get(download_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_file(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(self.user, uploaded)
        detail_url = reverse("files-detail", args=[file_obj.id])
        data = {"name": "updated.txt"}
        response = self.client.patch(detail_url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "updated.txt"
        file_obj.refresh_from_db()
        assert file_obj.name == "updated.txt"
        default_storage.delete(file_obj.s3_key)

    def test_delete_file(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(self.user, uploaded)
        detail_url = reverse("files-detail", args=[file_obj.id])
        response = self.client.delete(detail_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not File.objects.filter(id=file_obj.id).exists()
        assert not default_storage.exists(file_obj.s3_key)

    def test_other_user_cannot_access(self):
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(self.user, uploaded)
        self.client.credentials()
        other_token_url = reverse("token_obtain_pair")
        other_login = {"email": "other@example.com", "password": "testpass"}
        response = self.client.post(other_token_url, other_login)
        other_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_token}")
        detail_url = reverse("files-detail", args=[file_obj.id])
        response = self.client.get(detail_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        download_url = reverse("files-download", args=[file_obj.id])
        response = self.client.get(download_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response = self.client.patch(detail_url, {"name": "hack.txt"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response = self.client.delete(detail_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        default_storage.delete(file_obj.s3_key)

    def test_unauthenticated_access(self):
        self.client.credentials()
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        file_obj = FileService.create_file(self.user, uploaded)
        detail_url = reverse("files-detail", args=[file_obj.id])
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response = self.client.get(detail_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        download_url = reverse("files-download", args=[file_obj.id])
        response = self.client.get(download_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response = self.client.post(self.list_url, {}, format="multipart")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        default_storage.delete(file_obj.s3_key)

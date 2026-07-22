from PIL import Image
import io
import pytest
import datetime
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from users.models import User
from files.models import File, SharedAccess
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
        old_time = timezone.now() - datetime.timedelta(hours=2)
        new_time = timezone.now()
        file1 = File.objects.create(
            user=user, name="old.txt", size=100, s3_key="files/old.txt"
        )
        file2 = File.objects.create(
            user=user, name="new.txt", size=200, s3_key="files/new.txt"
        )
        File.objects.filter(id=file1.id).update(uploaded_at=old_time)
        File.objects.filter(id=file2.id).update(uploaded_at=new_time)
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


class TestFileSharing:
    def setup_method(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass"
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com", password="testpass"
        )
        login_data = {"email": "owner@example.com", "password": "testpass"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        self.access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        self.file_obj = FileService.create_file(self.owner, uploaded)
        self.file_obj.is_shared = False
        self.file_obj.save()
        self.share_url = reverse("files-share", args=[self.file_obj.id])
        self.shares_url = reverse("files-shares", args=[self.file_obj.id])

    def teardown_method(self):
        if self.file_obj.s3_key and default_storage.exists(self.file_obj.s3_key):
            default_storage.delete(self.file_obj.s3_key)

    def test_share_file_success(self):
        data = {"email": "other@example.com", "permission": "view"}
        response = self.client.post(self.share_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert SharedAccess.objects.filter(
            file=self.file_obj, shared_with=self.other
        ).exists()
        self.file_obj.refresh_from_db()
        assert self.file_obj.is_shared is True

    def test_share_file_self_forbidden(self):
        data = {"email": "owner@example.com", "permission": "view"}
        response = self.client.post(self.share_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_share_file_nonexistent_user(self):
        data = {"email": "nonexistent@example.com", "permission": "view"}
        response = self.client.post(self.share_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_shares(self):
        SharedAccess.objects.create(
            file=self.file_obj, shared_with=self.other, permission="view"
        )
        response = self.client.get(self.shares_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_remove_share(self):
        share = SharedAccess.objects.create(
            file=self.file_obj, shared_with=self.other, permission="view"
        )
        remove_url = reverse("files-remove-share", args=[self.file_obj.id, share.id])
        response = self.client.delete(remove_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SharedAccess.objects.filter(id=share.id).exists()
        self.file_obj.refresh_from_db()
        assert self.file_obj.is_shared is False

    def test_transfer_ownership(self):
        transfer_url = f"/api/files/{self.file_obj.id}/transfer/"
        data = {"new_owner_email": "other@example.com"}
        response = self.client.post(transfer_url, data)
        assert response.status_code == status.HTTP_200_OK
        self.file_obj.refresh_from_db()
        assert self.file_obj.user == self.other
        assert not SharedAccess.objects.filter(file=self.file_obj).exists()
        assert self.file_obj.is_shared is False

    def test_shared_with_me_list(self):
        SharedAccess.objects.create(
            file=self.file_obj, shared_with=self.other, permission="view"
        )
        self.client.credentials()
        login_data = {"email": "other@example.com", "password": "testpass"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        url = reverse("files-shared-with-me")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == self.file_obj.id

    def test_download_shared_file(self):
        SharedAccess.objects.create(
            file=self.file_obj, shared_with=self.other, permission="view"
        )
        self.client.credentials()
        login_data = {"email": "other@example.com", "password": "testpass"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        download_url = reverse("files-download", args=[self.file_obj.id])
        response = self.client.get(download_url)
        assert response.status_code == status.HTTP_200_OK


class TestFileFiltering:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        login_data = {"email": "test@example.com", "password": "testpass"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        self.access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        self.list_url = reverse("files-list")

        self.files = []
        names = ["alpha.txt", "beta.pdf", "gamma.jpg", "delta.txt"]
        sizes = [100, 500, 1000, 200]
        mimes = ["text/plain", "application/pdf", "image/jpeg", "text/plain"]
        now = timezone.now()
        for i, (name, size, mime) in enumerate(zip(names, sizes, mimes)):
            uploaded = SimpleUploadedFile(name, b"content" * size, content_type=mime)
            file_obj = FileService.create_file(self.user, uploaded)
            uploaded_at = now - timedelta(days=i)
            File.objects.filter(id=file_obj.id).update(
                uploaded_at=uploaded_at, size=size, mime_type=mime
            )
            self.files.append(file_obj)

    def teardown_method(self):
        for file_obj in self.files:
            if file_obj.s3_key and default_storage.exists(file_obj.s3_key):
                default_storage.delete(file_obj.s3_key)

    def test_search_by_name(self):
        response = self.client.get(self.list_url, {"search": "alpha"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "alpha.txt"

    def test_filter_by_mime_type(self):
        response = self.client.get(self.list_url, {"mime_type": "text/plain"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        names = [f["name"] for f in response.data]
        assert "alpha.txt" in names
        assert "delta.txt" in names

    def test_filter_by_size_range(self):
        response = self.client.get(self.list_url, {"size_min": 200, "size_max": 800})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        sizes = [f["size"] for f in response.data]
        assert all(200 <= s <= 800 for s in sizes)

    def test_filter_by_uploaded_at_range(self):
        now = timezone.now()
        after = (now - timedelta(days=4)).isoformat()
        response = self.client.get(self.list_url, {"uploaded_at_after": after})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 4
        for file_data in response.data:
            uploaded_at = file_data["uploaded_at"]
            assert uploaded_at >= after

    def test_ordering_by_name_asc(self):
        response = self.client.get(self.list_url, {"ordering": "name"})
        assert response.status_code == status.HTTP_200_OK
        names = [f["name"] for f in response.data]
        assert names == sorted(names)

    def test_ordering_by_size_desc(self):
        response = self.client.get(self.list_url, {"ordering": "-size"})
        assert response.status_code == status.HTTP_200_OK
        sizes = [f["size"] for f in response.data]
        assert sizes == sorted(sizes, reverse=True)


class TestPublicLinks:
    def setup_method(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass"
        )
        login_data = {"email": "owner@example.com", "password": "testpass"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        self.access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        uploaded = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        self.file_obj = FileService.create_file(self.owner, uploaded)
        self.generate_url = reverse(
            "files-generate-public-link", args=[self.file_obj.id]
        )

    def teardown_method(self):
        cache.clear()
        if self.file_obj.s3_key and default_storage.exists(self.file_obj.s3_key):
            default_storage.delete(self.file_obj.s3_key)

    def test_generate_public_link_success(self):
        data = {"expires_in_seconds": 60}
        response = self.client.post(self.generate_url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "link" in response.data
        assert "token" in response.data
        assert response.data["expires_in_seconds"] == 60

    def test_generate_public_link_forbidden_for_non_owner(self):
        User.objects.create_user(
            username="other", email="other@example.com", password="testpass"
        )
        self.client.credentials()
        login_data = {"email": "other@example.com", "password": "testpass"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        assert response.status_code == status.HTTP_200_OK
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.post(
            self.generate_url, {"expires_in_seconds": 60}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_public_download_success(self):
        response = self.client.post(
            self.generate_url, {"expires_in_seconds": 60}, format="json"
        )
        token = response.data["token"]
        self.client.credentials()
        public_url = reverse("public-download", args=[token])
        response = self.client.get(public_url)
        assert response.status_code == status.HTTP_200_OK
        content = b"".join(response.streaming_content)
        assert content == b"content"

    def test_public_download_once(self):
        response = self.client.post(
            self.generate_url, {"expires_in_seconds": 60}, format="json"
        )
        token = response.data["token"]
        self.client.credentials()
        public_url = reverse("public-download", args=[token])
        response = self.client.get(public_url)
        assert response.status_code == status.HTTP_200_OK
        response = self.client.get(public_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_public_download_expired(self):
        self.client.credentials()
        public_url = reverse("public-download", args=["invalid-token"])
        response = self.client.get(public_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFilePreview:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass')
        login_data = {'email': 'test@example.com', 'password': 'testpass'}
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, login_data)
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def teardown_method(self):
        cache.clear()

    def test_preview_for_image(self):
        img = Image.new('RGB', (100, 100), color='red')
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        uploaded = SimpleUploadedFile('test.jpg', img_io.read(), content_type='image/jpeg')
        data = {'file': uploaded}
        response = self.client.post(reverse('files-list'), data, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        file_id = response.data['id']
        preview_url = reverse('files-preview', args=[file_id])
        preview_response = self.client.get(preview_url)
        assert preview_response.status_code == status.HTTP_200_OK
        assert preview_response['Content-Type'] == 'image/jpeg'

    def test_preview_for_text_file(self):
        uploaded = SimpleUploadedFile('test.txt', b'content', content_type='text/plain')
        data = {'file': uploaded}
        response = self.client.post(reverse('files-list'), data, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        file_id = response.data['id']
        preview_url = reverse('files-preview', args=[file_id])
        preview_response = self.client.get(preview_url)
        assert preview_response.status_code == status.HTTP_404_NOT_FOUND
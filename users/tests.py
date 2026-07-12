import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import User


pytestmark = pytest.mark.django_db


class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        assert user.is_superuser is True
        assert user.is_staff is True


class TestUserRegistration:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("users-register")

    def test_register_user_success(self):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "password2": "securepass123",
        }
        response = self.client.post(self.url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username="newuser").exists()

    def test_register_user_duplicate_username(self):
        User.objects.create_user(
            username="existing", email="existing@example.com", password="testpass123"
        )
        data = {
            "username": "existing",
            "email": "new@example.com",
            "password": "securepass123",
            "password2": "securepass123",
        }
        response = self.client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_password_mismatch(self):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "password2": "differentpass123",
        }
        response = self.client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_missing_fields(self):
        data = {"username": "newuser", "email": "new@example.com"}
        response = self.client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUserLogin:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.url = reverse("token_obtain_pair")

    def test_login_success(self):
        data = {"email": "test@example.com", "password": "testpass123"}
        response = self.client.post(self.url, data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self):
        data = {"email": "test@example.com", "password": "wrongpass"}
        response = self.client.post(self.url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self):
        data = {"email": "nonexistent@example.com", "password": "testpass123"}
        response = self.client.post(self.url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        login_data = {"email": "test@example.com", "password": "testpass123"}
        self.url = reverse("token_obtain_pair")
        response = self.client.post(self.url, login_data)
        assert response.status_code == status.HTTP_200_OK
        self.refresh_token = response.data["refresh"]
        self.refresh_url = reverse("token_refresh")

    def test_refresh_token_success(self):
        data = {"refresh": self.refresh_token}
        response = self.client.post(self.refresh_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_token_invalid(self):
        data = {"refresh": "invalid.token.here"}
        response = self.client.post(self.refresh_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserProfile:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="testpass123",
        )
        self.profile_url = reverse("users-profile")
        login_data = {"email": "test@example.com", "password": "testpass123"}
        token_url = reverse("token_obtain_pair")
        response = self.client.post(token_url, login_data)
        assert response.status_code == status.HTTP_200_OK
        self.access_token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def test_get_profile_success(self):
        response = self.client.get(self.profile_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"
        assert response.data["email"] == "test@example.com"
        assert response.data["first_name"] == "Test"
        assert response.data["last_name"] == "User"

    def test_update_profile_success(self):
        data = {"first_name": "Updated", "last_name": "Name"}
        response = self.client.patch(self.profile_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"
        assert response.data["last_name"] == "Name"

    def test_update_profile_email(self):
        data = {"email": "newemail@example.com"}
        response = self.client.patch(self.profile_url, data)
        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.email == "test@example.com"

    def test_profile_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.profile_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

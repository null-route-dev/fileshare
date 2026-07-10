from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from .models import User


class UserService:
    @staticmethod
    def create_user(data):
        password = data.get('password')
        password2 = data.get('password2')

        if not password or not password2:
            raise ValidationError("Password fields are required")

        if password != password2:
            raise ValidationError("Passwords do not match")

        try:
            validate_password(password)
        except ValidationError as e:
            raise ValidationError({"password": e.messages})

        user_data = {
            'username': data.get('username'),
            'email': data.get('email'),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
        }

        try:
            user = User.objects.create_user(**user_data, password=password)
        except IntegrityError as e:
            if 'username' in str(e):
                raise ValidationError({"username": "User with this username already exists."})
            if 'email' in str(e):
                raise ValidationError({"email": "User with this email already exists."})
            raise

        return user

    @staticmethod
    def update_profile(user, data):
        allowed_fields = ['username', 'first_name', 'last_name']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])

        try:
            user.full_clean()
            user.save()
        except ValidationError as e:
            raise ValidationError(e.message_dict)
        except IntegrityError as e:
            if 'username' in str(e):
                raise ValidationError({"username": "User with this username already exists."})
            raise

        return user

    @staticmethod
    def get_user_by_id(user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_email(email):
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None
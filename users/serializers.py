from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
        ]
        extra_kwargs = {
            "email": {
                "required": True,
                "validators": [UniqueValidator(queryset=User.objects.all())],
            }
        }

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["email"]

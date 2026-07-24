import logging
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django_ratelimit.decorators import ratelimit
from django.conf import settings
from .models import User
from .serializers import UserRegistrationSerializer, UserProfileSerializer
from .services import UserService
from .permissions import IsSelfProfile
from config.logging_utils import audit_log, audit_logger


logger = logging.getLogger("fileshare")


@method_decorator(
    ratelimit(key="ip", rate=settings.RATELIMIT_AUTH_RATE, method="POST", block=True),
    name="dispatch",
)
class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "register":
            return UserRegistrationSerializer
        return UserProfileSerializer

    def get_permissions(self):
        if self.action == "register":
            return [permissions.AllowAny()]
        if self.action == "profile":
            return [permissions.IsAuthenticated(), IsSelfProfile()]
        return super().get_permissions()

    @action(detail=False, methods=["post"], url_path="register")
    @audit_log("register_user")
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserService.create_user(serializer.validated_data)
            return Response(
                UserProfileSerializer(user).data, status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {
                    "errors": e.message_dict
                    if hasattr(e, "message_dict")
                    else {"error": str(e)}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get", "put", "patch"], url_path="profile")
    def profile(self, request):
        user = request.user
        action_type = "view_profile" if request.method == "GET" else "update_profile"

        if request.method == "GET":
            serializer = UserProfileSerializer(user)
            audit_logger.info(
                f"{user.email} - {action_type} - SUCCESS",
                extra={"user": user.email, "action": action_type, "status": "SUCCESS"},
            )
            return Response(serializer.data)

        serializer = UserProfileSerializer(
            user, data=request.data, partial=request.method == "PATCH"
        )
        serializer.is_valid(raise_exception=True)

        try:
            updated_user = UserService.update_profile(user, serializer.validated_data)
            audit_logger.info(
                f"{user.email} - {action_type} - SUCCESS",
                extra={"user": user.email, "action": action_type, "status": "SUCCESS"},
            )
            return Response(UserProfileSerializer(updated_user).data)
        except ValidationError as e:
            audit_logger.warning(
                f"{user.email} - {action_type} - FAILED: {str(e)}",
                extra={
                    "user": user.email,
                    "action": action_type,
                    "status": "FAILED",
                    "error": str(e),
                },
            )
            return Response(
                {
                    "errors": e.message_dict
                    if hasattr(e, "message_dict")
                    else {"error": str(e)}
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(
    ratelimit(key="ip", rate=settings.RATELIMIT_AUTH_RATE, method="POST", block=True),
    name="dispatch",
)
class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "unknown")
        try:
            response = super().post(request, *args, **kwargs)
            audit_logger.info(
                f"{email} - login - SUCCESS",
                extra={"user": email, "action": "login", "status": "SUCCESS"},
            )
            return response
        except (TokenError, InvalidToken) as e:
            audit_logger.warning(
                f"{email} - login - FAILED: {str(e)}",
                extra={
                    "user": email,
                    "action": "login",
                    "status": "FAILED",
                    "error": str(e),
                },
            )
            raise
        except Exception as e:
            audit_logger.error(
                f"{email} - login - FAILED: {str(e)}",
                extra={
                    "user": email,
                    "action": "login",
                    "status": "FAILED",
                    "error": str(e),
                },
                exc_info=True,
            )
            raise


@method_decorator(
    ratelimit(key="ip", rate=settings.RATELIMIT_AUTH_RATE, method="POST", block=True),
    name="dispatch",
)
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        user_email = "unknown"
        try:
            response = super().post(request, *args, **kwargs)
            audit_logger.info(
                f"{user_email} - refresh_token - SUCCESS",
                extra={
                    "user": user_email,
                    "action": "refresh_token",
                    "status": "SUCCESS",
                },
            )
            return response
        except (TokenError, InvalidToken) as e:
            audit_logger.warning(
                f"{user_email} - refresh_token - FAILED: {str(e)}",
                extra={
                    "user": user_email,
                    "action": "refresh_token",
                    "status": "FAILED",
                    "error": str(e),
                },
            )
            raise
        except Exception as e:
            audit_logger.error(
                f"{user_email} - refresh_token - FAILED: {str(e)}",
                extra={
                    "user": user_email,
                    "action": "refresh_token",
                    "status": "FAILED",
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

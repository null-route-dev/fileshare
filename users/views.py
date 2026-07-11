from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .models import User
from .serializers import UserRegistrationSerializer, UserProfileSerializer
from .services import UserService
from .permissions import IsSelfProfile


class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegistrationSerializer
        return UserProfileSerializer

    def get_permissions(self):
        if self.action == 'register':
            return [permissions.AllowAny()]
        if self.action == 'profile':
            return [permissions.IsAuthenticated(), IsSelfProfile()]
        return super().get_permissions()

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserService.create_user(serializer.validated_data)
            return Response(
                UserProfileSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {'errors': e.message_dict if hasattr(e, 'message_dict') else {'error': str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='profile')
    def profile(self, request):
        user = request.user

        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)

        serializer = UserProfileSerializer(
            user,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)

        try:
            updated_user = UserService.update_profile(user, serializer.validated_data)
            return Response(UserProfileSerializer(updated_user).data)
        except ValidationError as e:
            return Response(
                {'errors': e.message_dict if hasattr(e, 'message_dict') else {'error': str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )
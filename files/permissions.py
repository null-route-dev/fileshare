from datetime import timezone
from rest_framework import permissions
from .models import SharedAccess


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class CanAccessSharedFile(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.user == request.user:
            return True

        try:
            share = SharedAccess.objects.get(file=obj, shared_with=request.user)
        except SharedAccess.DoesNotExist:
            return False

        if share.expires_at and share.expires_at < timezone.now():
            return False

        if request.method in permissions.SAFE_METHODS or request.method == "GET":
            return share.permission in ["view", "edit"]
        if request.method in ["PUT", "PATCH", "DELETE"]:
            return share.permission == "edit"

        return False

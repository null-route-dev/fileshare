from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileViewSet, PublicDownloadView

router = DefaultRouter()
router.register(r"files", FileViewSet, basename="files")

urlpatterns = [
    path("", include(router.urls)),
    path("public/<str:token>/", PublicDownloadView.as_view(), name="public-download"),
]

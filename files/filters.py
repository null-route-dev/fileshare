import django_filters
from .models import File


class FileFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    uploaded_at_after = django_filters.DateTimeFilter(
        field_name="uploaded_at", lookup_expr="gte"
    )
    uploaded_at_before = django_filters.DateTimeFilter(
        field_name="uploaded_at", lookup_expr="lte"
    )
    size_min = django_filters.NumberFilter(field_name="size", lookup_expr="gte")
    size_max = django_filters.NumberFilter(field_name="size", lookup_expr="lte")
    mime_type = django_filters.CharFilter(lookup_expr="exact")
    is_shared = django_filters.BooleanFilter()

    class Meta:
        model = File
        fields = [
            "name",
            "uploaded_at_after",
            "uploaded_at_before",
            "size_min",
            "size_max",
            "mime_type",
            "is_shared",
        ]

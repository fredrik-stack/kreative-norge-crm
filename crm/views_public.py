# crm/views_public.py
from django.conf import settings
from django.db.models import Prefetch
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema

from .models import Organization, OrganizationPerson, PersonContact
from .serializers_public import PublicActorSerializer
from .services.images.projection import prefetch_public_image_projection


class PublicActorPublicViewSet(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicActorSerializer

    lookup_field = "org_number"
    lookup_url_kwarg = "org_number"

    def get_queryset(self):
        queryset = Organization.objects.filter(is_published=True).order_by("name")
        public_contacts = PersonContact.objects.filter(is_public=True).order_by(
            "type", "value"
        )
        public_people = (
            OrganizationPerson.objects.filter(status="ACTIVE", publish_person=True)
            .select_related("person")
            .order_by("person__full_name", "person_id")
            .prefetch_related(
                Prefetch(
                    "person__contacts",
                    queryset=public_contacts,
                    to_attr="_public_contacts",
                )
            )
        )
        queryset = queryset.prefetch_related(
            "tags",
            "categories",
            "subcategories__category",
            Prefetch(
                "org_people",
                queryset=public_people,
                to_attr="_public_people_links",
            ),
        )
        if settings.PUBLIC_IMAGE_API_SCHEMA_ENABLED:
            return prefetch_public_image_projection(queryset)
        return queryset

    @extend_schema(
        description="Public, read-only liste over publiserte aktører (Organization.is_published=True).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

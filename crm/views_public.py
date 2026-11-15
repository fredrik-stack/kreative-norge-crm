# crm/views_public.py
from django.conf import settings
from django.db.models import Prefetch
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.generics import get_object_or_404
from drf_spectacular.utils import extend_schema

from .models import OrganizationPerson, PersonContact
from .serializers_public import PublicActorSerializer
from .services.images.projection import prefetch_public_image_projection
from .services.public_actor_identity import public_actors, public_actor_by_org_number


class PublicActorPublicViewSet(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicActorSerializer

    lookup_field = "org_number"
    lookup_url_kwarg = "org_number"

    def get_queryset(self):
        queryset = public_actors().order_by("name")
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

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        if "canonical_id" in self.kwargs:
            actor = get_object_or_404(queryset, pk=self.kwargs["canonical_id"])
        else:
            actor = public_actor_by_org_number(queryset, self.kwargs["org_number"])
        self.check_object_permissions(self.request, actor)
        return actor

    @extend_schema(
        description="Read-only legacy-kompatibel PUBLIC-liste: én rad per publisert Organization, canonical_id=PK. Ingen assignment- eller target-tag-cutover.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# crm/views_public.py
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import Organization
from .serializers_public import PublicActorSerializer


class PublicActorPublicViewSet(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicActorSerializer

    lookup_field = "org_number"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return Organization.objects.filter(is_published=True).order_by("name")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="pk",  # må være pk fordi routeren bruker {pk}
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Organisasjonsnummer (org_number). Eksempel: 998544092",
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        description="Public, read-only liste over publiserte aktører (Organization.is_published=True).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)




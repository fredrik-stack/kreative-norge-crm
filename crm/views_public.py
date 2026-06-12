# crm/views_public.py
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.shortcuts import get_object_or_404

from .models import Organization
from .serializers_public import PublicActorSerializer


class PublicActorPublicViewSet(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicActorSerializer

    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return (
            Organization.objects.filter(is_published=True)
            .order_by("name")
            .prefetch_related("tags", "categories", "subcategories__category", "org_people__person__contacts")
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="pk",  # må være pk fordi routeren bruker {pk}
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Organisasjonsnummer (org_number), eller id-prefiks for aktører uten org.nr. Eksempel: 998544092 eller id-123",
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        identifier = kwargs.get(self.lookup_url_kwarg, "")
        queryset = self.get_queryset()
        if identifier.startswith("id-") and identifier[3:].isdigit():
            instance = get_object_or_404(queryset, pk=int(identifier[3:]))
        else:
            instance = get_object_or_404(queryset, org_number=identifier)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        description="Public, read-only liste over publiserte aktører (Organization.is_published=True).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


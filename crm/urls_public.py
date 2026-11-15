from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_public import PublicActorPublicViewSet

router = DefaultRouter()
router.register(r"actors", PublicActorPublicViewSet, basename="public-actors")

urlpatterns = [
    # An explicit namespace preserves numeric org-number URLs as aliases.
    path(
        "actors/id/<int:canonical_id>/",
        PublicActorPublicViewSet.as_view(
            {"get": "retrieve"}, lookup_field="pk", lookup_url_kwarg="canonical_id",
        ),
        name="public-actors-canonical-detail",
    ),
    path("", include(router.urls)),
]


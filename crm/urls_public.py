from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_public import PublicActorPublicViewSet

router = DefaultRouter()
router.register(r"actors", PublicActorPublicViewSet, basename="public-actors")

urlpatterns = [
    path("", include(router.urls)),
]


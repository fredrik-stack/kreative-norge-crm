from django.urls import path

from .views_public_site import PublicActorDetailView, PublicActorListView

urlpatterns = [
    path("actors/", PublicActorListView.as_view(), name="public-actor-list"),
    path("actors/<slug:identifier>/", PublicActorDetailView.as_view(), name="public-actor-detail"),
]

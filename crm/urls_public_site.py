from django.urls import path

from .views_public_site import PublicActorDetailView, PublicActorLegacyDetailRedirectView, PublicActorListView

urlpatterns = [
    path("actors/", PublicActorListView.as_view(), name="public-actor-list"),
    path("actors/id/<int:actor_id>/", PublicActorDetailView.as_view(), name="public-actor-detail"),
    path("actors/<slug:org_number>/", PublicActorLegacyDetailRedirectView.as_view(), name="public-actor-detail-legacy"),
]

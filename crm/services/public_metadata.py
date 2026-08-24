from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from crm.models import Organization
from crm.services.images.projection import PublicImageProjection, PublicImageVariant
from crm.services.images.public_urls import build_public_fallback_url


PUBLIC_ACTOR_LIST_DESCRIPTION = (
    "En oversikt over musikkbransjen og andre kreative næringer. "
    "Finn aktører etter navn, kategori eller tag."
)


@dataclass(frozen=True)
class PublicPageMetadata:
    title: str
    canonical_url: str
    description: str | None
    image: PublicImageVariant
    image_alt: str | None


def _absolute_public_url(path: str) -> str:
    origin = settings.PUBLIC_SITE_ORIGIN
    if not origin:
        raise ImproperlyConfigured("PUBLIC_SITE_ORIGIN is not configured.")
    return f"{origin}{path}"


def build_public_actor_list_metadata() -> PublicPageMetadata:
    return PublicPageMetadata(
        title="Kreative Norge",
        canonical_url=_absolute_public_url(reverse("public-actor-list")),
        description=PUBLIC_ACTOR_LIST_DESCRIPTION,
        image=PublicImageVariant(
            url=build_public_fallback_url("share"),
            width=1200,
            height=630,
        ),
        image_alt=None,
    )


def build_public_actor_metadata(
    organization: Organization,
    projection: PublicImageProjection,
) -> PublicPageMetadata:
    description = (organization.description or "").strip() or None
    image_alt = projection.alt_text.strip() or None
    return PublicPageMetadata(
        title=organization.name,
        canonical_url=_absolute_public_url(
            reverse("public-actor-detail", args=[organization.pk])
        ),
        description=description,
        image=projection.share,
        image_alt=image_alt,
    )

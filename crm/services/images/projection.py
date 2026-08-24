from __future__ import annotations

from dataclasses import asdict, dataclass

from django.db.models import Prefetch, QuerySet

from crm.models import (
    Organization,
    OrganizationImageRelease,
    OrganizationImageSelection,
)
from image_safety.release_keys import REQUIRED_RELEASE_VARIANTS

from .bridge_client import ImageSafetyBridgeClient, ImageSafetyBridgeError
from .public_urls import build_public_fallback_url, build_public_media_url
from .release_validation import (
    PublicReleaseMappingInvalid,
    PublicReleaseScopeInactive,
    validated_release_mappings,
)


@dataclass(frozen=True)
class PublicImageVariant:
    url: str
    width: int
    height: int


@dataclass(frozen=True)
class PublicImageProjection:
    kind: str
    alt_text: str
    credit: str | None
    square: PublicImageVariant
    landscape: PublicImageVariant
    share: PublicImageVariant

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PublicImageProjectionResult:
    projection: PublicImageProjection
    reason: str
    authorize_count: int = 0
    safety_cursor: int | None = None


_FALLBACK_DIMENSIONS = {
    "square": (512, 512),
    "landscape": (800, 450),
    "share": (1200, 630),
}


def prefetch_public_image_projection(queryset: QuerySet) -> QuerySet:
    """Prefetch all projection DB state in fixed queries for a catalog queryset."""

    releases = OrganizationImageRelease.objects.select_related(
        "tenant", "organization", "selection", "rendition_set"
    ).prefetch_related("renditions__rendition")
    selections = OrganizationImageSelection.objects.filter(
        status=OrganizationImageSelection.Status.ACTIVE
    ).select_related("tenant", "organization", "rendition_set").prefetch_related(
        Prefetch("public_releases", queryset=releases, to_attr="_projection_releases")
    )
    return queryset.prefetch_related(
        Prefetch(
            "image_selections",
            queryset=selections,
            to_attr="_public_image_projection_selections",
        )
    )


def _fallback(reason: str, *, authorize_count: int = 0) -> PublicImageProjectionResult:
    variants = {
        variant: PublicImageVariant(
            url=build_public_fallback_url(variant),
            width=dimensions[0],
            height=dimensions[1],
        )
        for variant, dimensions in _FALLBACK_DIMENSIONS.items()
    }
    return PublicImageProjectionResult(
        projection=PublicImageProjection(
            kind="system_fallback",
            # Production fallback v1 is generic decoration, not actor content.
            alt_text="",
            credit=None,
            square=variants["square"],
            landscape=variants["landscape"],
            share=variants["share"],
        ),
        reason=reason,
        authorize_count=authorize_count,
    )


def _active_selections(
    organization: Organization,
) -> tuple[OrganizationImageSelection, ...]:
    prefetched = getattr(organization, "_public_image_projection_selections", None)
    if prefetched is not None:
        return tuple(prefetched)
    releases = OrganizationImageRelease.objects.select_related(
        "tenant", "organization", "selection", "rendition_set"
    ).prefetch_related("renditions__rendition")
    return tuple(
        organization.image_selections.filter(
            status=OrganizationImageSelection.Status.ACTIVE
        )
        .select_related("tenant", "organization", "rendition_set")
        .prefetch_related(
            Prefetch(
                "public_releases",
                queryset=releases,
                to_attr="_projection_releases",
            )
        )
    )


def _selection_releases(
    selection: OrganizationImageSelection,
) -> tuple[OrganizationImageRelease, ...]:
    prefetched = getattr(selection, "_projection_releases", None)
    if prefetched is not None:
        return tuple(prefetched)
    return tuple(selection.public_releases.all())


def project_public_image(
    organization: Organization,
    *,
    bridge: ImageSafetyBridgeClient | None = None,
) -> PublicImageProjectionResult:
    """Resolve one fail-closed public image without storage or state mutation."""

    if not organization.is_published:
        return _fallback("organization_unpublished")

    selections = _active_selections(organization)
    if not selections:
        return _fallback("no_active_selection")
    if len(selections) != 1:
        return _fallback("selection_scope_mismatch")
    selection = selections[0]
    if (
        selection.tenant_id != organization.tenant_id
        or selection.organization_id != organization.pk
    ):
        return _fallback("selection_scope_mismatch")
    if (
        selection.selection_kind
        == OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK
    ):
        return _fallback("selection_system_fallback")
    if selection.selection_kind != OrganizationImageSelection.SelectionKind.ASSET:
        return _fallback("selection_scope_mismatch")

    releases = _selection_releases(selection)
    if not releases:
        return _fallback("release_missing")
    if len(releases) != 1:
        return _fallback("release_mapping_invalid")
    release = releases[0]
    try:
        mappings = validated_release_mappings(release)
    except PublicReleaseScopeInactive:
        return _fallback("release_scope_inactive")
    except PublicReleaseMappingInvalid:
        return _fallback("release_mapping_invalid")

    bridge = bridge or ImageSafetyBridgeClient(timeout=5.0)
    cursors: list[int] = []
    authorize_count = 0
    for variant in sorted(REQUIRED_RELEASE_VARIANTS):
        mapping = mappings[variant]
        authorize_count += 1
        try:
            authorization = bridge.authorize(
                release_id=str(release.release_id),
                tenant_id=release.tenant_id,
                organization_id=release.organization_id,
                variant=variant,
                public_storage_key=mapping.public_storage_key,
                artifact_checksum_sha256=mapping.artifact_checksum_sha256_snapshot,
            )
        except ImageSafetyBridgeError:
            return _fallback("safety_unavailable", authorize_count=authorize_count)
        if not authorization.authorized:
            reason = f"safety_{authorization.category}"
            return _fallback(reason, authorize_count=authorize_count)
        cursors.append(authorization.read_cursor)

    variants = {}
    for variant in REQUIRED_RELEASE_VARIANTS:
        mapping = mappings[variant]
        rendition = mapping.rendition
        variants[variant] = PublicImageVariant(
            url=build_public_media_url(mapping.public_storage_key),
            width=rendition.width,
            height=rendition.height,
        )
    credit = selection.public_credit or None
    return PublicImageProjectionResult(
        projection=PublicImageProjection(
            kind="asset",
            alt_text=selection.alt_text,
            credit=credit,
            square=variants["square"],
            landscape=variants["landscape"],
            share=variants["share"],
        ),
        reason="asset",
        authorize_count=authorize_count,
        safety_cursor=min(cursors) if cursors else None,
    )

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from crm.models import (
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
)
from image_safety.release_keys import (
    InvalidPublicReleaseKeyError,
    PUBLIC_RELEASE_EXTENSIONS,
    REQUIRED_RELEASE_VARIANTS,
    build_public_release_key,
    canonical_release_id,
)

from .bridge_client import ImageSafetyBridgeClient, ImageSafetyBridgeError
from .materialization import (
    ImageMaterializationError,
    MaterializationInput,
    verify_materialized_rendition,
)


class PublicImageServingError(RuntimeError):
    pass


class PublicImageNotFound(PublicImageServingError):
    pass


class PublicImageUnavailable(PublicImageServingError):
    pass


@dataclass(frozen=True)
class PreparedPublicImage:
    release_id: str
    variant: str
    public_storage_key: str
    content_type: str
    content_length: int
    checksum_sha256: str
    safety_category: str
    safety_cursor: int

    @property
    def internal_redirect(self) -> str:
        return f"/_protected-public-image/{self.public_storage_key}"


_CONTENT_TYPES = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _load_release(release_id: str) -> OrganizationImageRelease:
    try:
        return (
            OrganizationImageRelease.objects.select_related(
                "tenant", "organization", "selection", "rendition_set"
            )
            .prefetch_related("renditions__rendition")
            .get(release_id=release_id)
        )
    except OrganizationImageRelease.DoesNotExist as error:
        raise PublicImageNotFound("Release is unknown.") from error


def _validated_mappings(
    release: OrganizationImageRelease,
) -> dict[str, OrganizationImageReleaseRendition]:
    selection = release.selection
    if (
        release.key_schema_version != OrganizationImageRelease.KEY_SCHEMA_VERSION
        or release.tenant_id != release.organization.tenant_id
        or release.tenant_id != selection.tenant_id
        or release.organization_id != selection.organization_id
        or release.rendition_set_id != selection.rendition_set_id
        or release.selection_revision_snapshot != selection.revision
        or selection.status != OrganizationImageSelection.Status.ACTIVE
        or selection.selection_kind != OrganizationImageSelection.SelectionKind.ASSET
        or not release.organization.is_published
    ):
        raise PublicImageNotFound("Release scope or publication is not active.")

    mappings = tuple(release.renditions.all())
    by_variant = {mapping.variant: mapping for mapping in mappings}
    if len(mappings) != 3 or set(by_variant) != REQUIRED_RELEASE_VARIANTS:
        raise PublicImageUnavailable("Release mapping set is incomplete.")
    for mapping in mappings:
        rendition = mapping.rendition
        try:
            expected_key = build_public_release_key(
                release.release_id, mapping.variant, mapping.output_format
            )
        except InvalidPublicReleaseKeyError as error:
            raise PublicImageUnavailable("Release mapping is inconsistent.") from error
        if (
            rendition.tenant_id != release.tenant_id
            or rendition.rendition_set_id != release.rendition_set_id
            or rendition.variant != mapping.variant
            or rendition.output_format != mapping.output_format
            or rendition.artifact_storage_key
            != mapping.artifact_storage_key_snapshot
            or rendition.checksum_sha256
            != mapping.artifact_checksum_sha256_snapshot
            or mapping.public_storage_key != expected_key
            or rendition.width <= 0
            or rendition.height <= 0
            or rendition.file_size_bytes <= 0
        ):
            raise PublicImageUnavailable("Release mapping is inconsistent.")
    return by_variant


def _materialization_input(
    release: OrganizationImageRelease,
    mapping: OrganizationImageReleaseRendition,
) -> MaterializationInput:
    rendition = mapping.rendition
    return MaterializationInput(
        release_id=str(release.release_id),
        variant=mapping.variant,
        output_format=mapping.output_format,
        width=rendition.width,
        height=rendition.height,
        file_size_bytes=rendition.file_size_bytes,
        artifact_storage_key=mapping.artifact_storage_key_snapshot,
        checksum_sha256=mapping.artifact_checksum_sha256_snapshot,
        public_storage_key=mapping.public_storage_key,
    )


def prepare_public_image(
    *,
    release_id: str,
    variant: str,
    extension: str,
    bridge: ImageSafetyBridgeClient | None = None,
) -> PreparedPublicImage:
    if not settings.PUBLIC_IMAGE_SERVING_ENABLED:
        raise PublicImageNotFound("Public image serving is disabled.")
    try:
        canonical_id = canonical_release_id(release_id)
    except (TypeError, ValueError) as error:
        raise PublicImageNotFound("Release ID is invalid.") from error

    release = _load_release(canonical_id)
    mappings = _validated_mappings(release)
    mapping = mappings.get(variant)
    if mapping is None or PUBLIC_RELEASE_EXTENSIONS[mapping.output_format] != extension:
        raise PublicImageNotFound("Release variant is unknown.")

    bridge = bridge or ImageSafetyBridgeClient(timeout=5.0)
    try:
        authorization = bridge.authorize(
            release_id=canonical_id,
            tenant_id=release.tenant_id,
            organization_id=release.organization_id,
            variant=variant,
            public_storage_key=mapping.public_storage_key,
            artifact_checksum_sha256=mapping.artifact_checksum_sha256_snapshot,
        )
    except ImageSafetyBridgeError as error:
        raise PublicImageUnavailable("Safety authorization is unavailable.") from error
    if not authorization.authorized:
        raise PublicImageNotFound("Safety authorization rejected the release.")

    try:
        for candidate in mappings.values():
            verify_materialized_rendition(_materialization_input(release, candidate))
    except ImageMaterializationError as error:
        raise PublicImageUnavailable("Release files failed verification.") from error

    rendition = mapping.rendition
    return PreparedPublicImage(
        release_id=canonical_id,
        variant=variant,
        public_storage_key=mapping.public_storage_key,
        content_type=_CONTENT_TYPES[mapping.output_format],
        content_length=rendition.file_size_bytes,
        checksum_sha256=mapping.artifact_checksum_sha256_snapshot,
        safety_category=authorization.category,
        safety_cursor=authorization.read_cursor,
    )

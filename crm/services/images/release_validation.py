from __future__ import annotations

from crm.models import (
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
)
from image_safety.release_keys import (
    InvalidPublicReleaseKeyError,
    REQUIRED_RELEASE_VARIANTS,
    build_public_release_key,
)


class PublicReleaseValidationError(RuntimeError):
    """Base class for fail-closed public release validation failures."""


class PublicReleaseScopeInactive(PublicReleaseValidationError):
    """The release is structurally valid but is not in an active public scope."""


class PublicReleaseMappingInvalid(PublicReleaseValidationError):
    """The immutable release mapping set is missing or inconsistent."""


def validated_release_mappings(
    release: OrganizationImageRelease,
) -> dict[str, OrganizationImageReleaseRendition]:
    """Validate the domain invariants shared by projection and byte serving."""

    selection = release.selection
    if (
        release.key_schema_version != OrganizationImageRelease.KEY_SCHEMA_VERSION
        or release.tenant_id != release.organization.tenant_id
        or release.tenant_id != selection.tenant_id
        or release.organization_id != selection.organization_id
        or release.rendition_set_id != selection.rendition_set_id
        or release.selection_revision_snapshot != selection.revision
        or selection.status != OrganizationImageSelection.Status.ACTIVE
        or selection.selection_kind
        != OrganizationImageSelection.SelectionKind.ASSET
        or not release.organization.is_published
    ):
        raise PublicReleaseScopeInactive(
            "Release scope or publication is not active."
        )

    mappings = tuple(release.renditions.all())
    by_variant = {mapping.variant: mapping for mapping in mappings}
    if len(mappings) != 3 or set(by_variant) != REQUIRED_RELEASE_VARIANTS:
        raise PublicReleaseMappingInvalid("Release mapping set is incomplete.")

    for mapping in mappings:
        rendition = mapping.rendition
        try:
            expected_key = build_public_release_key(
                release.release_id, mapping.variant, mapping.output_format
            )
        except InvalidPublicReleaseKeyError as error:
            raise PublicReleaseMappingInvalid(
                "Release mapping is inconsistent."
            ) from error
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
            raise PublicReleaseMappingInvalid("Release mapping is inconsistent.")

    return by_variant

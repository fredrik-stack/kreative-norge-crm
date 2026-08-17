from __future__ import annotations

from dataclasses import dataclass
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from crm.models import (
    ImageRendition,
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
)
from image_safety.release_keys import (
    InvalidPublicReleaseKeyError,
    PUBLIC_RELEASE_EXTENSIONS,
    REQUIRED_RELEASE_VARIANTS,
    build_public_release_key,
)


class ImageReleaseError(Exception):
    """Base class for public image release domain failures."""


class ImageReleaseFeatureDisabledError(ImageReleaseError):
    pass


class InvalidImageReleaseError(ImageReleaseError):
    pass


class IncompleteImageReleaseError(InvalidImageReleaseError):
    pass


@dataclass(frozen=True)
class OrganizationImageReleaseResult:
    release: OrganizationImageRelease
    renditions: tuple[OrganizationImageReleaseRendition, ...]


def _validate_release_scope(
    selection: OrganizationImageSelection,
    renditions: list[ImageRendition],
) -> None:
    if selection.selection_kind != OrganizationImageSelection.SelectionKind.ASSET:
        raise InvalidImageReleaseError("System fallback selections cannot have asset releases.")
    if not selection.rendition_set_id:
        raise InvalidImageReleaseError("Asset selection must reference a rendition set.")
    if selection.organization.tenant_id != selection.tenant_id:
        raise InvalidImageReleaseError(
            "Selection organization must belong to the selection tenant."
        )
    if selection.rendition_set.tenant_id != selection.tenant_id:
        raise InvalidImageReleaseError(
            "Selection rendition set must belong to the selection tenant."
        )
    if selection.rendition_set.asset.tenant_id != selection.tenant_id:
        raise InvalidImageReleaseError(
            "Selection asset must belong to the selection tenant."
        )

    variants = {rendition.variant for rendition in renditions}
    if len(renditions) != 3 or variants != REQUIRED_RELEASE_VARIANTS:
        raise IncompleteImageReleaseError(
            "Release requires exactly square, landscape, and share renditions."
        )
    for rendition in renditions:
        if rendition.tenant_id != selection.tenant_id:
            raise InvalidImageReleaseError(
                "Every rendition must belong to the selection tenant."
            )
        if rendition.rendition_set_id != selection.rendition_set_id:
            raise InvalidImageReleaseError(
                "Every rendition must belong to the selection rendition set."
            )


def create_organization_image_release(
    *,
    selection: OrganizationImageSelection,
) -> OrganizationImageReleaseResult:
    if not settings.IMAGE_ASSET_FEATURE_ENABLED:
        raise ImageReleaseFeatureDisabledError(
            "Image asset feature is disabled; public release creation is unavailable."
        )
    if not selection.pk:
        raise InvalidImageReleaseError("Selection must be persisted before release creation.")

    try:
        with transaction.atomic():
            locked_selection = (
                OrganizationImageSelection.objects.select_for_update(of=("self",))
                .select_related(
                    "tenant",
                    "organization",
                    "rendition_set",
                    "rendition_set__asset",
                )
                .get(pk=selection.pk)
            )
            renditions = list(
                ImageRendition.objects.select_for_update()
                .filter(rendition_set_id=locked_selection.rendition_set_id)
                .order_by("variant", "pk")
            )
            _validate_release_scope(locked_selection, renditions)

            release = OrganizationImageRelease(
                release_id=uuid.uuid4(),
                tenant=locked_selection.tenant,
                organization=locked_selection.organization,
                selection=locked_selection,
                rendition_set=locked_selection.rendition_set,
                key_schema_version=OrganizationImageRelease.KEY_SCHEMA_VERSION,
            )
            release = OrganizationImageRelease.objects._insert_from_release_service(
                [release]
            )[0]
            mappings = [
                OrganizationImageReleaseRendition(
                    release=release,
                    rendition=rendition,
                    variant=rendition.variant,
                    output_format=rendition.output_format,
                    artifact_storage_key_snapshot=rendition.artifact_storage_key,
                    artifact_checksum_sha256_snapshot=rendition.checksum_sha256,
                    public_storage_key=build_public_release_key(
                        release.release_id,
                        rendition.variant,
                        rendition.output_format,
                    ),
                )
                for rendition in renditions
            ]
            created_mappings = (
                OrganizationImageReleaseRendition.objects._insert_from_release_service(
                    mappings
                )
            )
    except OrganizationImageSelection.DoesNotExist as error:
        raise InvalidImageReleaseError("Selection does not exist.") from error
    except (IntegrityError, ValidationError) as error:
        raise InvalidImageReleaseError("Release aggregate is invalid.") from error

    return OrganizationImageReleaseResult(
        release=release,
        renditions=tuple(created_mappings),
    )

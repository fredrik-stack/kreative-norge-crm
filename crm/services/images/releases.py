from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from crm.validators import validate_sha256, validate_storage_key
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

from .bridge_client import (
    BridgeActivation,
    BridgeRenditionSnapshot,
    BridgeReservation,
    ImageSafetyBridgeClient,
)
from .materialization import (
    ImageMaterializationError,
    MaterializationInput,
    MaterializationResult,
    delete_materialized_release,
    materialize_release,
)
from .safety_guards import (
    ImageSafetyGuardUnavailable,
    ImageSourceChecksumDenied,
    require_source_checksum_allowed,
)


class ImageReleaseError(Exception):
    """Base class for public image release domain failures."""


class ImageReleaseFeatureDisabledError(ImageReleaseError):
    pass


class InvalidImageReleaseError(ImageReleaseError):
    pass


class IncompleteImageReleaseError(InvalidImageReleaseError):
    pass


class ImageReleaseSafetyUnavailable(ImageReleaseError):
    pass


class ImageReleaseChecksumDenied(InvalidImageReleaseError):
    pass


@dataclass(frozen=True)
class _RenditionSnapshot:
    rendition_id: int
    tenant_id: int
    rendition_set_id: int
    variant: str
    output_format: str
    width: int
    height: int
    file_size_bytes: int
    artifact_storage_key: str
    checksum_sha256: str


@dataclass(frozen=True)
class _SelectionSnapshot:
    tenant_id: int
    organization_id: int
    selection_id: int
    selection_revision: int
    rendition_set_id: int
    source_checksum_sha256: str
    renditions: tuple[_RenditionSnapshot, ...]


@dataclass(frozen=True)
class OrganizationImageReleaseResult:
    release: OrganizationImageRelease
    renditions: tuple[OrganizationImageReleaseRendition, ...]
    reservation: BridgeReservation
    materializations: tuple[MaterializationResult, ...]
    activation: BridgeActivation


def _validate_release_scope(
    selection: OrganizationImageSelection,
    renditions: list[ImageRendition],
) -> None:
    if selection.revision <= 0:
        raise InvalidImageReleaseError("Selection revision must be positive.")
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
        if (
            rendition.output_format not in PUBLIC_RELEASE_EXTENSIONS
            or rendition.width <= 0
            or rendition.height <= 0
            or rendition.file_size_bytes <= 0
        ):
            raise InvalidImageReleaseError("Rendition metadata is invalid.")
        try:
            validate_storage_key(rendition.artifact_storage_key)
            validate_sha256(rendition.checksum_sha256)
        except ValidationError as error:
            raise InvalidImageReleaseError(
                "Rendition artifact identity is invalid."
            ) from error
        extension = PUBLIC_RELEASE_EXTENSIONS[rendition.output_format]
        expected_artifact_key = (
            f"tenants/{selection.tenant_id}/artifacts/"
            f"{selection.rendition_set.processing_version}/"
            f"{selection.rendition_set.asset.checksum_sha256}/"
            f"{selection.rendition_set.render_config_hash_sha256}/"
            f"{rendition.variant}-{rendition.checksum_sha256}.{extension}"
        )
        if rendition.artifact_storage_key != expected_artifact_key:
            raise InvalidImageReleaseError(
                "Rendition artifact key is outside its canonical tenant scope."
            )


def _validate_existing_before_reservation(
    selection: OrganizationImageSelection,
    renditions: list[ImageRendition],
) -> None:
    existing = (
        OrganizationImageRelease.objects.filter(selection_id=selection.pk)
        .select_related("selection")
        .first()
    )
    if existing is None:
        return
    if (
        existing.tenant_id != selection.tenant_id
        or existing.organization_id != selection.organization_id
        or existing.selection_revision_snapshot != selection.revision
        or existing.rendition_set_id != selection.rendition_set_id
        or existing.key_schema_version != OrganizationImageRelease.KEY_SCHEMA_VERSION
    ):
        raise InvalidImageReleaseError("Existing release aggregate conflicts with selection.")
    expected = {
        item.variant: (
            item.pk,
            item.output_format,
            item.artifact_storage_key,
            item.checksum_sha256,
            build_public_release_key(
                existing.release_id, item.variant, item.output_format
            ),
        )
        for item in renditions
    }
    actual = {
        item.variant: (
            item.rendition_id,
            item.output_format,
            item.artifact_storage_key_snapshot,
            item.artifact_checksum_sha256_snapshot,
            item.public_storage_key,
        )
        for item in existing.renditions.order_by("variant", "pk")
    }
    if actual != expected:
        raise InvalidImageReleaseError(
            "Existing release mappings conflict with current immutable artifacts."
        )


def _snapshot_locked_selection(selection_id: int) -> _SelectionSnapshot:
    try:
        selection = (
            OrganizationImageSelection.objects.select_for_update(of=("self",))
            .select_related("organization", "rendition_set", "rendition_set__asset")
            .get(pk=selection_id)
        )
    except OrganizationImageSelection.DoesNotExist as error:
        raise InvalidImageReleaseError("Selection does not exist.") from error
    renditions = list(
        ImageRendition.objects.select_for_update()
        .filter(rendition_set_id=selection.rendition_set_id)
        .order_by("variant", "pk")
    )
    _validate_release_scope(selection, renditions)
    _validate_existing_before_reservation(selection, renditions)
    return _SelectionSnapshot(
        tenant_id=selection.tenant_id,
        organization_id=selection.organization_id,
        selection_id=selection.pk,
        selection_revision=selection.revision,
        rendition_set_id=selection.rendition_set_id,
        source_checksum_sha256=selection.rendition_set.asset.checksum_sha256,
        renditions=tuple(
            _RenditionSnapshot(
                rendition_id=item.pk,
                tenant_id=item.tenant_id,
                rendition_set_id=item.rendition_set_id,
                variant=item.variant,
                output_format=item.output_format,
                width=item.width,
                height=item.height,
                file_size_bytes=item.file_size_bytes,
                artifact_storage_key=item.artifact_storage_key,
                checksum_sha256=item.checksum_sha256,
            )
            for item in renditions
        ),
    )


def _take_snapshot(selection_id: int) -> _SelectionSnapshot:
    with transaction.atomic():
        return _snapshot_locked_selection(selection_id)


def _bridge_renditions(
    snapshot: _SelectionSnapshot,
) -> tuple[BridgeRenditionSnapshot, ...]:
    return tuple(
        BridgeRenditionSnapshot(
            variant=item.variant,
            output_format=item.output_format,
            artifact_storage_key=item.artifact_storage_key,
            artifact_checksum_sha256=item.checksum_sha256,
        )
        for item in snapshot.renditions
    )


def _verify_bound_aggregate(
    release: OrganizationImageRelease,
    mappings: tuple[OrganizationImageReleaseRendition, ...],
    snapshot: _SelectionSnapshot,
    reservation: BridgeReservation,
) -> None:
    if (
        str(release.release_id) != reservation.release_id
        or release.tenant_id != snapshot.tenant_id
        or release.organization_id != snapshot.organization_id
        or release.selection_id != snapshot.selection_id
        or release.selection_revision_snapshot != snapshot.selection_revision
        or release.rendition_set_id != snapshot.rendition_set_id
        or release.key_schema_version != OrganizationImageRelease.KEY_SCHEMA_VERSION
    ):
        raise InvalidImageReleaseError(
            "Existing database release conflicts with the safety reservation."
        )
    expected = {
        item.variant: (
            item.rendition_id,
            item.output_format,
            item.artifact_storage_key,
            item.checksum_sha256,
            reservation.public_keys[item.variant],
        )
        for item in snapshot.renditions
    }
    actual = {
        item.variant: (
            item.rendition_id,
            item.output_format,
            item.artifact_storage_key_snapshot,
            item.artifact_checksum_sha256_snapshot,
            item.public_storage_key,
        )
        for item in mappings
    }
    if actual != expected:
        raise InvalidImageReleaseError(
            "Existing database release mappings conflict with the safety reservation."
        )


def _load_bound_aggregate(
    snapshot: _SelectionSnapshot,
    reservation: BridgeReservation,
) -> tuple[OrganizationImageRelease, tuple[OrganizationImageReleaseRendition, ...]]:
    try:
        release = OrganizationImageRelease.objects.get(selection_id=snapshot.selection_id)
    except OrganizationImageRelease.DoesNotExist as error:
        raise InvalidImageReleaseError("Release binding was not committed.") from error
    mappings = tuple(release.renditions.order_by("variant", "pk"))
    _verify_bound_aggregate(release, mappings, snapshot, reservation)
    return release, mappings


def _bind_release(
    snapshot: _SelectionSnapshot,
    reservation: BridgeReservation,
) -> tuple[OrganizationImageRelease, tuple[OrganizationImageReleaseRendition, ...]]:
    try:
        with transaction.atomic():
            current = _snapshot_locked_selection(snapshot.selection_id)
            if current != snapshot:
                raise InvalidImageReleaseError(
                    "Selection or rendition metadata changed during reservation."
                )
            existing = (
                OrganizationImageRelease.objects.select_for_update()
                .filter(selection_id=snapshot.selection_id)
                .first()
            )
            if existing is not None:
                mappings = tuple(existing.renditions.order_by("variant", "pk"))
                _verify_bound_aggregate(existing, mappings, snapshot, reservation)
                return existing, mappings

            release = OrganizationImageRelease(
                release_id=reservation.release_id,
                tenant_id=snapshot.tenant_id,
                organization_id=snapshot.organization_id,
                selection_id=snapshot.selection_id,
                selection_revision_snapshot=snapshot.selection_revision,
                rendition_set_id=snapshot.rendition_set_id,
                key_schema_version=OrganizationImageRelease.KEY_SCHEMA_VERSION,
            )
            release = OrganizationImageRelease.objects._insert_from_release_service(
                [release]
            )[0]
            mappings = [
                OrganizationImageReleaseRendition(
                    release=release,
                    rendition_id=item.rendition_id,
                    variant=item.variant,
                    output_format=item.output_format,
                    artifact_storage_key_snapshot=item.artifact_storage_key,
                    artifact_checksum_sha256_snapshot=item.checksum_sha256,
                    public_storage_key=reservation.public_keys[item.variant],
                )
                for item in snapshot.renditions
            ]
            created = tuple(
                OrganizationImageReleaseRendition.objects._insert_from_release_service(
                    mappings
                )
            )
            return release, created
    except IntegrityError:
        # A concurrent identical request may win the unique selection gate.
        return _load_bound_aggregate(snapshot, reservation)
    except ValidationError as error:
        raise InvalidImageReleaseError("Release aggregate is invalid.") from error


def _materialization_inputs(
    snapshot: _SelectionSnapshot,
    reservation: BridgeReservation,
) -> tuple[MaterializationInput, ...]:
    return tuple(
        MaterializationInput(
            release_id=reservation.release_id,
            variant=item.variant,
            output_format=item.output_format,
            width=item.width,
            height=item.height,
            file_size_bytes=item.file_size_bytes,
            artifact_storage_key=item.artifact_storage_key,
            checksum_sha256=item.checksum_sha256,
            public_storage_key=reservation.public_keys[item.variant],
        )
        for item in snapshot.renditions
    )


def create_organization_image_release(
    *, selection: OrganizationImageSelection
) -> OrganizationImageReleaseResult:
    if not (
        settings.IMAGE_ASSET_FEATURE_ENABLED
        and settings.PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED
    ):
        raise ImageReleaseFeatureDisabledError(
            "Public image release materialization is disabled."
        )
    if not selection.pk:
        raise InvalidImageReleaseError("Selection must be persisted before release creation.")

    snapshot = _take_snapshot(selection.pk)
    bridge = ImageSafetyBridgeClient()
    try:
        require_source_checksum_allowed(
            tenant_id=snapshot.tenant_id,
            source_checksum_sha256=snapshot.source_checksum_sha256,
            bridge=bridge,
        )
    except ImageSourceChecksumDenied as error:
        raise ImageReleaseChecksumDenied(str(error)) from error
    except ImageSafetyGuardUnavailable as error:
        raise ImageReleaseSafetyUnavailable(str(error)) from error
    reservation = bridge.reserve(
        tenant_id=snapshot.tenant_id,
        organization_id=snapshot.organization_id,
        selection_id=snapshot.selection_id,
        selection_revision=snapshot.selection_revision,
        rendition_set_id=snapshot.rendition_set_id,
        renditions=_bridge_renditions(snapshot),
    )
    release, mappings = _bind_release(snapshot, reservation)
    materialization_inputs = _materialization_inputs(snapshot, reservation)
    materializations = materialize_release(materialization_inputs)
    # Close the approval→materialization race with a concurrent takedown. A
    # workflow that passed the first guard before deny must not leave restored
    # origin bytes behind after the checksum becomes terminal.
    try:
        require_source_checksum_allowed(
            tenant_id=snapshot.tenant_id,
            source_checksum_sha256=snapshot.source_checksum_sha256,
            bridge=bridge,
        )
    except (ImageSourceChecksumDenied, ImageSafetyGuardUnavailable) as error:
        try:
            delete_materialized_release(materialization_inputs)
        except ImageMaterializationError as deletion_error:
            raise ImageReleaseSafetyUnavailable(
                "Unconfirmed release bytes could not be removed from public delivery."
            ) from deletion_error
        if isinstance(error, ImageSourceChecksumDenied):
            raise ImageReleaseChecksumDenied(str(error)) from error
        raise ImageReleaseSafetyUnavailable(str(error)) from error
    activation = bridge.activate(release_id=reservation.release_id)
    return OrganizationImageReleaseResult(
        release=release,
        renditions=mappings,
        reservation=reservation,
        materializations=materializations,
        activation=activation,
    )

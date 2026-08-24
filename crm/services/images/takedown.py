from __future__ import annotations

from dataclasses import dataclass
import logging
from time import monotonic
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction

from crm.models import (
    ImageReviewEvent,
    Organization,
    OrganizationImageRelease,
    OrganizationImageSelection,
    TenantMembership,
)
from image_safety.release_keys import (
    PUBLIC_RELEASE_EXTENSIONS,
    REQUIRED_RELEASE_VARIANTS,
    build_public_release_key,
)

from .bridge_client import (
    BridgeDeny,
    ImageSafetyBridgeConflict,
    ImageSafetyBridgeClient,
    ImageSafetyBridgeError,
)
from .materialization import (
    DeliveryDeletionResult,
    ImageMaterializationError,
    MaterializationInput,
    delete_materialized_release,
)
from .selections import _create_selection_revision


LOGGER = logging.getLogger("crm.images.takedown")
ALLOWED_TAKEDOWN_ROLES = frozenset(
    {TenantMembership.Role.SUPERADMIN, TenantMembership.Role.GRUPPEADMIN}
)


class ImageTakedownError(RuntimeError):
    code = "image_takedown_error"


class ImageTakedownDisabled(ImageTakedownError):
    code = "not_found"


class ImageTakedownPermissionDenied(ImageTakedownError):
    code = "permission_denied"


class ImageTakedownInvalid(ImageTakedownError):
    code = "invalid_takedown"


class ImageTakedownConflict(ImageTakedownError):
    code = "takedown_conflict"


class ImageTakedownUnavailable(ImageTakedownError):
    code = "safety_unavailable"


@dataclass(frozen=True)
class FormalImageTakedownResult:
    selection_id: int
    selection_revision: int
    review_event_id: int
    idempotent_retry: bool
    release_disposition: str
    checksum_disposition: str
    anchor_cursor: int
    origin_files_deleted: int
    origin_files_already_missing: int


@dataclass(frozen=True)
class _TakedownTarget:
    release: OrganizationImageRelease
    source_checksum_sha256: str
    items: tuple[MaterializationInput, ...]


def _validate_actor(actor, tenant_id: int) -> None:
    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
        or not getattr(actor, "is_active", False)
        or not getattr(actor, "pk", None)
    ):
        raise ImageTakedownPermissionDenied(
            "An active authenticated administrator is required."
        )
    if actor.is_superuser:
        return
    if not TenantMembership.objects.filter(
        tenant_id=tenant_id,
        user_id=actor.pk,
        role__in=ALLOWED_TAKEDOWN_ROLES,
    ).exists():
        raise ImageTakedownPermissionDenied(
            "The actor cannot perform formal takedown in this tenant."
        )


def _validate_reason(reason_code: object) -> str:
    if reason_code not in ImageReviewEvent.TakedownReason.values:
        raise ImageTakedownInvalid("A supported takedown reason code is required.")
    return str(reason_code)


def _target_from_release(
    release: OrganizationImageRelease,
    *,
    tenant_id: int,
    organization_id: int,
) -> _TakedownTarget:
    if (
        release.tenant_id != tenant_id
        or release.organization_id != organization_id
        or release.selection.tenant_id != tenant_id
        or release.selection.organization_id != organization_id
        or release.selection_revision_snapshot != release.selection.revision
        or release.rendition_set_id != release.selection.rendition_set_id
        or release.rendition_set.tenant_id != tenant_id
        or release.rendition_set.asset.tenant_id != tenant_id
    ):
        raise ImageTakedownConflict("Release scope is inconsistent.")
    mappings = tuple(release.renditions.all())
    if len(mappings) != 3 or {item.variant for item in mappings} != REQUIRED_RELEASE_VARIANTS:
        raise ImageTakedownConflict("Release mapping set is incomplete.")
    items = []
    for mapping in mappings:
        rendition = mapping.rendition
        expected_key = build_public_release_key(
            release.release_id, mapping.variant, mapping.output_format
        )
        if (
            mapping.public_storage_key != expected_key
            or mapping.rendition_id != rendition.pk
            or rendition.rendition_set_id != release.rendition_set_id
            or mapping.variant != rendition.variant
            or mapping.output_format != rendition.output_format
            or mapping.artifact_storage_key_snapshot != rendition.artifact_storage_key
            or mapping.artifact_checksum_sha256_snapshot != rendition.checksum_sha256
            or PUBLIC_RELEASE_EXTENSIONS.get(mapping.output_format)
            != mapping.public_storage_key.rsplit(".", 1)[-1]
        ):
            raise ImageTakedownConflict("Release mapping is inconsistent.")
        items.append(
            MaterializationInput(
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
        )
    return _TakedownTarget(
        release=release,
        source_checksum_sha256=release.rendition_set.asset.checksum_sha256,
        items=tuple(items),
    )


def _load_release(release_id, *, tenant_id: int, organization_id: int):
    try:
        release = (
            OrganizationImageRelease.objects.select_related(
                "selection", "rendition_set__asset"
            )
            .prefetch_related("renditions__rendition")
            .get(
                release_id=release_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
        )
    except OrganizationImageRelease.DoesNotExist as error:
        raise ImageTakedownConflict("The exact takedown release is unavailable.") from error
    return _target_from_release(
        release, tenant_id=tenant_id, organization_id=organization_id
    )


def _delete_origin(target: _TakedownTarget) -> tuple[DeliveryDeletionResult, ...]:
    try:
        return delete_materialized_release(target.items)
    except ImageMaterializationError as error:
        raise ImageTakedownUnavailable(
            "The denied release origin could not be verified as removed."
        ) from error


def formal_takedown_organization_image(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    reason_code: str,
    bridge: ImageSafetyBridgeClient | None = None,
) -> FormalImageTakedownResult:
    started_at = monotonic()
    correlation_id = uuid.uuid4().hex
    if not settings.PUBLIC_IMAGE_TAKEDOWN_ENABLED:
        raise ImageTakedownDisabled("Formal image takedown is disabled.")
    if (
        isinstance(tenant_id, bool)
        or not isinstance(tenant_id, int)
        or tenant_id <= 0
        or isinstance(organization_id, bool)
        or not isinstance(organization_id, int)
        or organization_id <= 0
    ):
        raise ImageTakedownInvalid("Tenant and organization IDs must be positive integers.")
    reason_code = _validate_reason(reason_code)
    bridge = bridge or ImageSafetyBridgeClient()

    try:
        with transaction.atomic():
            _validate_actor(actor, tenant_id)
            organization = (
                Organization.objects.select_for_update()
                .filter(pk=organization_id, tenant_id=tenant_id)
                .first()
            )
            if organization is None:
                raise ImageTakedownInvalid(
                    "The organization was not found in the target tenant."
                )
            active_selection = (
                OrganizationImageSelection.objects.select_for_update(of=("self",))
                .select_related("rendition_set__asset")
                .filter(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    status=OrganizationImageSelection.Status.ACTIVE,
                )
                .first()
            )
            if active_selection is None:
                raise ImageTakedownInvalid("An active image selection is required.")

            retry_event = None
            if active_selection.selection_kind == OrganizationImageSelection.SelectionKind.ASSET:
                releases = tuple(
                    OrganizationImageRelease.objects.select_related(
                        "selection", "rendition_set__asset"
                    )
                    .prefetch_related("renditions__rendition")
                    .filter(selection_id=active_selection.pk)
                )
                if len(releases) != 1:
                    raise ImageTakedownConflict(
                        "The active asset selection must have exactly one bound release."
                    )
                target = _target_from_release(
                    releases[0], tenant_id=tenant_id, organization_id=organization_id
                )
            elif (
                active_selection.selection_kind
                == OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK
            ):
                retry_event = (
                    ImageReviewEvent.objects.filter(
                        tenant_id=tenant_id,
                        organization_id_snapshot=organization_id,
                        selection_id=active_selection.pk,
                        event_type=ImageReviewEvent.EventType.FORMAL_TAKEDOWN,
                    )
                    .order_by("-created_at", "-pk")
                    .first()
                )
                if retry_event is None or retry_event.release_id_snapshot is None:
                    raise ImageTakedownInvalid(
                        "The active fallback is not a retryable formal takedown."
                    )
                if retry_event.takedown_reason_code != reason_code:
                    raise ImageTakedownConflict(
                        "The retry reason does not match the formal takedown audit."
                    )
                target = _load_release(
                    retry_event.release_id_snapshot,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                )
                if (
                    retry_event.asset_checksum_sha256_snapshot
                    != target.source_checksum_sha256
                ):
                    raise ImageTakedownConflict(
                        "The retry source checksum does not match the audit snapshot."
                    )
            else:
                raise ImageTakedownConflict("The active selection kind is unsupported.")

            try:
                denial: BridgeDeny = bridge.deny(
                    release_id=str(target.release.release_id),
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    source_checksum_sha256=target.source_checksum_sha256,
                    reason_code=reason_code,
                )
            except ImageSafetyBridgeConflict as error:
                raise ImageTakedownConflict(
                    "The permanent deny conflicts with existing safety state."
                ) from error
            except ImageSafetyBridgeError as error:
                raise ImageTakedownUnavailable(
                    "The release deny was not confirmed by image safety."
                ) from error

            if retry_event is None:
                selection_result = _create_selection_revision(
                    actor=actor,
                    tenant_id=tenant_id,
                    organization=organization,
                    active_selection=active_selection,
                    selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                    rendition_set=None,
                    alt_text="Standardbilde",
                    public_credit="",
                    asset=active_selection.rendition_set.asset,
                    evidence=None,
                    technical_warnings=[],
                    event_type=ImageReviewEvent.EventType.FORMAL_TAKEDOWN,
                    audit_rendition_set=active_selection.rendition_set,
                    takedown_reason_code=reason_code,
                    release_id_snapshot=target.release.release_id,
                )
                result_selection = selection_result.selection
                result_event = selection_result.event
            else:
                result_selection = active_selection
                result_event = retry_event
    except IntegrityError as error:
        raise ImageTakedownConflict(
            "The image selection changed concurrently; retry the takedown."
        ) from error

    deletions = _delete_origin(target)
    deleted = sum(item.deleted for item in deletions)
    missing = len(deletions) - deleted
    LOGGER.info(
        "formal_image_takedown tenant_id=%s organization_id=%s release_id=%s "
        "actor_user_id=%s review_event_id=%s correlation_id=%s reason_code=%s "
        "release_disposition=%s checksum_disposition=%s anchor_cursor=%s "
        "origin_deleted=%s origin_missing=%s verification=origin_absent duration_ms=%.3f",
        tenant_id,
        organization_id,
        target.release.release_id,
        actor.pk,
        result_event.pk,
        correlation_id,
        reason_code,
        denial.release_disposition,
        denial.checksum_disposition,
        denial.anchor_cursor,
        deleted,
        missing,
        (monotonic() - started_at) * 1000,
    )
    return FormalImageTakedownResult(
        selection_id=result_selection.pk,
        selection_revision=result_selection.revision,
        review_event_id=result_event.pk,
        idempotent_retry=retry_event is not None,
        release_disposition=denial.release_disposition,
        checksum_disposition=denial.checksum_disposition,
        anchor_cursor=denial.anchor_cursor,
        origin_files_deleted=deleted,
        origin_files_already_missing=missing,
    )

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from crm.models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    ImageReviewEvent,
    Organization,
    OrganizationImageSelection,
    TenantMembership,
    validate_technical_warnings,
)


IMAGE_APPROVAL_TEXT_VERSION = "image-approval-v1"
IMAGE_APPROVAL_TEXT = (
    "Jeg bekrefter at bildet er relevant for aktøren, at det kommer fra aktøren "
    "selv, en offisiell kilde eller en annen kilde som tillater bruken, og at det "
    "kan publiseres i Kreative Norge og tilhørende kort- og delingsvisninger."
)

REQUIRED_RENDITION_VARIANTS = frozenset(
    {
        ImageRendition.Variant.SQUARE,
        ImageRendition.Variant.LANDSCAPE,
        ImageRendition.Variant.SHARE,
    }
)
ALLOWED_SELECTION_ROLES = frozenset(
    {
        TenantMembership.Role.SUPERADMIN,
        TenantMembership.Role.GRUPPEADMIN,
        TenantMembership.Role.REDIGERER,
    }
)
SENSITIVE_QUERY_KEYS = frozenset(
    {
        "credential",
        "credentials",
        "signature",
        "sig",
        "token",
        "access_token",
        "id_token",
        "refresh_token",
        "auth",
        "authorization",
        "api_key",
        "apikey",
        "access_key",
        "secret",
        "secret_key",
        "password",
        "passwd",
        "sv",
        "se",
        "sp",
        "sr",
    }
)
SENSITIVE_QUERY_KEY_PREFIXES = (
    "x-amz-",
    "x-goog-",
)


class ImageSelectionError(Exception):
    """Base class for selection command failures."""


class ImageFeatureDisabledError(ImageSelectionError):
    pass


class ImageSelectionPermissionDenied(ImageSelectionError):
    pass


class ImageSelectionNotFoundError(ImageSelectionError):
    pass


class InvalidImageSelectionError(ImageSelectionError):
    pass


class InvalidImageSelectionTransitionError(InvalidImageSelectionError):
    pass


class IncompleteRenditionSetError(ImageSelectionError):
    pass


class ExpectedRevisionConflictError(ImageSelectionError):
    pass


class ImageSelectionConcurrencyError(ImageSelectionError):
    pass


@dataclass(frozen=True, slots=True)
class AssetApprovalEvidence:
    source_type: str
    source_url: str = ""
    source_page_url: str = ""
    provider: str = ""
    technical_warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.technical_warnings, (list, tuple)):
            object.__setattr__(self, "technical_warnings", tuple(self.technical_warnings))


@dataclass(frozen=True, slots=True)
class OrganizationImageSelectionResult:
    selection: OrganizationImageSelection
    event: ImageReviewEvent
    previous_selection: OrganizationImageSelection | None


def _raise_invalid_validation(error: ValidationError) -> None:
    raise InvalidImageSelectionError("Invalid image selection input.") from error


def _validate_identifier(value, field_name: str, *, allow_zero: bool = False) -> None:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InvalidImageSelectionError(f"{field_name} must be an integer >= {minimum}.")


def _validate_actor_capability(actor, tenant_id: int) -> None:
    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
        or not getattr(actor, "is_active", False)
        or not getattr(actor, "pk", None)
    ):
        raise ImageSelectionPermissionDenied("An active authenticated actor is required.")
    if not actor.get_username():
        raise ImageSelectionPermissionDenied("The actor must have a username.")
    if actor.is_superuser:
        return

    allowed = TenantMembership.objects.filter(
        tenant_id=tenant_id,
        user_id=actor.pk,
        role__in=ALLOWED_SELECTION_ROLES,
    ).exists()
    if not allowed:
        raise ImageSelectionPermissionDenied(
            "The actor does not have image selection capability in the target tenant."
        )


def _validate_snapshot_url(value: str, field_name: str) -> None:
    if not value:
        return
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise InvalidImageSelectionError(
            f"{field_name} must be a valid HTTP(S) URL."
        ) from error
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise InvalidImageSelectionError(f"{field_name} must use HTTP or HTTPS.")
    if parsed.username is not None or parsed.password is not None:
        raise InvalidImageSelectionError(f"{field_name} cannot contain credentials.")
    if parsed.fragment:
        raise InvalidImageSelectionError(f"{field_name} cannot contain a fragment.")
    query_keys = {
        key.strip().casefold()
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
    }
    if any(
        key in SENSITIVE_QUERY_KEYS
        or key.startswith(SENSITIVE_QUERY_KEY_PREFIXES)
        for key in query_keys
    ):
        raise InvalidImageSelectionError(
            f"{field_name} cannot contain signed or tokenized URLs."
        )


def _validate_asset_evidence(evidence: AssetApprovalEvidence) -> list[str]:
    if not isinstance(evidence, AssetApprovalEvidence):
        raise InvalidImageSelectionError("Asset selections require typed approval evidence.")
    string_values = {
        "source_type": evidence.source_type,
        "source_url": evidence.source_url,
        "source_page_url": evidence.source_page_url,
        "provider": evidence.provider,
    }
    if any(not isinstance(value, str) for value in string_values.values()):
        raise InvalidImageSelectionError("Approval evidence text values must be strings.")
    if evidence.source_type not in ImageReviewEvent.SourceType.values:
        raise InvalidImageSelectionError("Approval evidence has an unsupported source type.")
    if evidence.source_type not in {
        ImageReviewEvent.SourceType.UPLOAD,
        ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH,
    } and not evidence.source_url:
        raise InvalidImageSelectionError("This approval source requires a source URL.")
    if not isinstance(evidence.technical_warnings, tuple):
        raise InvalidImageSelectionError("Technical warnings must be a typed list of short text values.")
    _validate_snapshot_url(evidence.source_url, "source_url")
    _validate_snapshot_url(evidence.source_page_url, "source_page_url")
    warnings = list(evidence.technical_warnings)
    try:
        validate_technical_warnings(warnings)
    except ValidationError as error:
        _raise_invalid_validation(error)
    return warnings


def _locked_asset_context(tenant_id: int, rendition_set_id: int):
    rendition_set = (
        ImageRenditionSet.objects.select_for_update()
        .filter(pk=rendition_set_id, tenant_id=tenant_id)
        .first()
    )
    if rendition_set is None:
        raise ImageSelectionNotFoundError(
            "The rendition set was not found in the target tenant."
        )

    asset = (
        ImageAsset.objects.select_for_update()
        .filter(pk=rendition_set.asset_id, tenant_id=tenant_id)
        .first()
    )
    if asset is None:
        raise ImageSelectionNotFoundError("The rendition asset does not belong to the target tenant.")

    renditions = list(
        ImageRendition.objects.select_for_update()
        .filter(rendition_set_id=rendition_set.pk)
        .order_by("pk")
    )
    if any(rendition.tenant_id != tenant_id for rendition in renditions):
        raise ImageSelectionNotFoundError(
            "A rendition does not belong to the target tenant."
        )
    variants = [rendition.variant for rendition in renditions]
    if len(variants) != len(REQUIRED_RENDITION_VARIANTS) or set(variants) != REQUIRED_RENDITION_VARIANTS:
        raise IncompleteRenditionSetError(
            "The rendition set must contain exactly square, landscape, and share."
        )
    return rendition_set, asset


def _build_event(
    *,
    tenant_id: int,
    organization: Organization,
    selection: OrganizationImageSelection,
    previous_selection: OrganizationImageSelection | None,
    actor,
    asset: ImageAsset | None,
    evidence: AssetApprovalEvidence | None,
    technical_warnings: list[str],
    timestamp,
    event_type: str,
    restored_from_selection: OrganizationImageSelection | None = None,
) -> ImageReviewEvent:
    is_asset = selection.selection_kind == OrganizationImageSelection.SelectionKind.ASSET
    is_restore = event_type == ImageReviewEvent.EventType.SELECTION_RESTORED
    event = ImageReviewEvent(
        tenant_id=tenant_id,
        organization=organization,
        selection=selection,
        rendition_set=selection.rendition_set if is_asset else None,
        asset=asset if is_asset else None,
        previous_selection=previous_selection,
        restored_from_selection=restored_from_selection,
        actor_user=actor,
        event_type=event_type,
        organization_id_snapshot=organization.pk,
        organization_name_snapshot=organization.name,
        organization_org_number_snapshot=organization.org_number or "",
        selection_id_snapshot=selection.pk,
        selection_revision_snapshot=selection.revision,
        selection_kind_snapshot=selection.selection_kind,
        rendition_set_id_snapshot=selection.rendition_set_id if is_asset else None,
        asset_id_snapshot=asset.pk if asset else None,
        asset_checksum_sha256_snapshot=asset.checksum_sha256 if asset else "",
        asset_validation_version_snapshot=asset.validation_version if asset else "",
        previous_selection_id_snapshot=previous_selection.pk if previous_selection else None,
        previous_selection_revision_snapshot=(
            previous_selection.revision if previous_selection else None
        ),
        restored_from_selection_id_snapshot=(
            restored_from_selection.pk if restored_from_selection else None
        ),
        restored_from_selection_revision_snapshot=(
            restored_from_selection.revision if restored_from_selection else None
        ),
        actor_user_id_snapshot=actor.pk,
        actor_username_snapshot=actor.get_username(),
        alt_text_snapshot=selection.alt_text,
        public_credit_snapshot=selection.public_credit,
        source_type_snapshot=evidence.source_type if evidence else "",
        source_url_snapshot=evidence.source_url if evidence else "",
        source_page_url_snapshot=evidence.source_page_url if evidence else "",
        provider_snapshot=evidence.provider if evidence else "",
        technical_warnings_snapshot=technical_warnings,
        approval_text_version_snapshot=(
            IMAGE_APPROVAL_TEXT_VERSION if is_asset and not is_restore else ""
        ),
        approval_text_snapshot=IMAGE_APPROVAL_TEXT if is_asset and not is_restore else "",
        created_at=timestamp,
    )
    try:
        event.full_clean()
    except ValidationError as error:
        _raise_invalid_validation(error)
    event.save()
    return event


def _locked_selection_context(*, actor, tenant_id: int, organization_id: int):
    organization = (
        Organization.objects.select_for_update()
        .filter(pk=organization_id, tenant_id=tenant_id)
        .first()
    )
    if organization is None:
        raise ImageSelectionNotFoundError(
            "The organization was not found in the target tenant."
        )

    _validate_actor_capability(actor, tenant_id)

    active_selection = (
        OrganizationImageSelection.objects.select_for_update()
        .filter(
            tenant_id=tenant_id,
            organization_id=organization_id,
            status=OrganizationImageSelection.Status.ACTIVE,
        )
        .first()
    )
    return organization, active_selection


def _create_selection_revision(
    *,
    actor,
    tenant_id: int,
    organization: Organization,
    active_selection: OrganizationImageSelection | None,
    selection_kind: str,
    rendition_set: ImageRenditionSet | None,
    alt_text: str,
    public_credit: str,
    asset: ImageAsset | None,
    evidence: AssetApprovalEvidence | None,
    technical_warnings: list[str],
    event_type: str,
    restored_from_selection: OrganizationImageSelection | None = None,
) -> OrganizationImageSelectionResult:
    highest_revision = (
        OrganizationImageSelection.objects.filter(
            tenant_id=tenant_id,
            organization_id=organization.pk,
        ).aggregate(max_revision=Max("revision"))["max_revision"]
        or 0
    )
    timestamp = timezone.now()

    if active_selection:
        active_selection.status = OrganizationImageSelection.Status.ARCHIVED
        active_selection.save(update_fields=["status"])

    selection = OrganizationImageSelection(
        tenant_id=tenant_id,
        organization=organization,
        selection_kind=selection_kind,
        rendition_set=rendition_set,
        alt_text=alt_text,
        public_credit=public_credit,
        revision=highest_revision + 1,
        status=OrganizationImageSelection.Status.ACTIVE,
        locked_by=actor,
        locked_at=timestamp,
    )
    try:
        selection.full_clean()
    except ValidationError as error:
        _raise_invalid_validation(error)
    selection.save()

    event = _build_event(
        tenant_id=tenant_id,
        organization=organization,
        selection=selection,
        previous_selection=active_selection,
        actor=actor,
        asset=asset,
        evidence=evidence,
        technical_warnings=technical_warnings,
        timestamp=timestamp,
        event_type=event_type,
        restored_from_selection=restored_from_selection,
    )
    return OrganizationImageSelectionResult(
        selection=selection,
        event=event,
        previous_selection=active_selection,
    )


def lock_organization_image_selection(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    expected_revision: int,
    selection_kind: str,
    rendition_set_id: int | None = None,
    alt_text: str,
    public_credit: str = "",
    asset_evidence: AssetApprovalEvidence | None = None,
) -> OrganizationImageSelectionResult:
    if not settings.IMAGE_ASSET_FEATURE_ENABLED:
        raise ImageFeatureDisabledError("Image asset selection is disabled.")

    _validate_identifier(tenant_id, "tenant_id")
    _validate_identifier(organization_id, "organization_id")
    _validate_identifier(expected_revision, "expected_revision", allow_zero=True)

    try:
        with transaction.atomic():
            organization, active_selection = _locked_selection_context(
                actor=actor,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            actual_revision = active_selection.revision if active_selection else 0
            if expected_revision != actual_revision:
                raise ExpectedRevisionConflictError(
                    f"Expected active revision {expected_revision}, found {actual_revision}."
                )

            rendition_set = None
            asset = None
            evidence = None
            technical_warnings: list[str] = []
            if selection_kind == OrganizationImageSelection.SelectionKind.ASSET:
                if rendition_set_id is None:
                    raise InvalidImageSelectionError(
                        "Asset selections require a rendition set."
                    )
                _validate_identifier(rendition_set_id, "rendition_set_id")
                evidence = asset_evidence
                technical_warnings = _validate_asset_evidence(evidence)
                rendition_set, asset = _locked_asset_context(tenant_id, rendition_set_id)
            elif selection_kind == OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK:
                if rendition_set_id is not None:
                    raise InvalidImageSelectionError(
                        "System fallback cannot reference a rendition set."
                    )
                if asset_evidence is not None:
                    raise InvalidImageSelectionError(
                        "System fallback cannot include asset approval evidence."
                    )
                if active_selection is not None:
                    if (
                        active_selection.selection_kind
                        == OrganizationImageSelection.SelectionKind.ASSET
                    ):
                        raise InvalidImageSelectionTransitionError(
                            "Use remove_organization_image_to_fallback for asset-to-fallback transitions."
                        )
                    raise InvalidImageSelectionTransitionError(
                        "The active selection is already system fallback."
                    )
            else:
                raise InvalidImageSelectionError("Unsupported selection kind.")

            return _create_selection_revision(
                actor=actor,
                tenant_id=tenant_id,
                organization=organization,
                active_selection=active_selection,
                selection_kind=selection_kind,
                rendition_set=rendition_set,
                alt_text=alt_text,
                public_credit=public_credit,
                asset=asset,
                evidence=evidence,
                technical_warnings=technical_warnings,
                event_type=(
                    ImageReviewEvent.EventType.SELECTION_REPLACED
                    if active_selection
                    else ImageReviewEvent.EventType.SELECTION_LOCKED
                ),
            )
    except IntegrityError as error:
        raise ImageSelectionConcurrencyError(
            "The image selection changed concurrently; reload before retrying."
        ) from error


def remove_organization_image_to_fallback(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    expected_revision: int,
    fallback_alt_text: str,
) -> OrganizationImageSelectionResult:
    if not settings.IMAGE_ASSET_FEATURE_ENABLED:
        raise ImageFeatureDisabledError("Image asset selection is disabled.")

    _validate_identifier(tenant_id, "tenant_id")
    _validate_identifier(organization_id, "organization_id")
    _validate_identifier(expected_revision, "expected_revision", allow_zero=True)
    if not isinstance(fallback_alt_text, str) or not fallback_alt_text.strip():
        raise InvalidImageSelectionError(
            "fallback_alt_text must be a non-empty text value."
        )

    try:
        with transaction.atomic():
            organization, active_selection = _locked_selection_context(
                actor=actor,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            if active_selection is None:
                raise InvalidImageSelectionTransitionError(
                    "An active asset selection is required before removal to fallback."
                )
            if expected_revision != active_selection.revision:
                raise ExpectedRevisionConflictError(
                    f"Expected active revision {expected_revision}, found {active_selection.revision}."
                )
            if active_selection.selection_kind != OrganizationImageSelection.SelectionKind.ASSET:
                raise InvalidImageSelectionTransitionError(
                    "The active selection is already system fallback."
                )

            return _create_selection_revision(
                actor=actor,
                tenant_id=tenant_id,
                organization=organization,
                active_selection=active_selection,
                selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                rendition_set=None,
                alt_text=fallback_alt_text,
                public_credit="",
                asset=None,
                evidence=None,
                technical_warnings=[],
                event_type=ImageReviewEvent.EventType.SELECTION_REMOVED_TO_FALLBACK,
            )
    except IntegrityError as error:
        raise ImageSelectionConcurrencyError(
            "The image selection changed concurrently; reload before retrying."
        ) from error


def restore_archived_organization_image_selection(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    expected_revision: int,
    source_selection_id: int,
) -> OrganizationImageSelectionResult:
    if not settings.IMAGE_ASSET_FEATURE_ENABLED:
        raise ImageFeatureDisabledError("Image asset selection is disabled.")

    _validate_identifier(tenant_id, "tenant_id")
    _validate_identifier(organization_id, "organization_id")
    _validate_identifier(expected_revision, "expected_revision", allow_zero=True)
    _validate_identifier(source_selection_id, "source_selection_id")

    try:
        with transaction.atomic():
            organization, active_selection = _locked_selection_context(
                actor=actor,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            if active_selection is None:
                raise InvalidImageSelectionTransitionError(
                    "An active selection is required before restoring an archived asset."
                )
            if expected_revision != active_selection.revision:
                raise ExpectedRevisionConflictError(
                    f"Expected active revision {expected_revision}, found {active_selection.revision}."
                )

            source_selection = (
                OrganizationImageSelection.objects.select_for_update()
                .filter(
                    pk=source_selection_id,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                )
                .first()
            )
            if source_selection is None:
                raise ImageSelectionNotFoundError(
                    "The restore source selection was not found in the target organization."
                )
            if source_selection.status != OrganizationImageSelection.Status.ARCHIVED:
                raise InvalidImageSelectionTransitionError(
                    "The restore source selection must be archived."
                )
            if source_selection.selection_kind != OrganizationImageSelection.SelectionKind.ASSET:
                raise InvalidImageSelectionTransitionError(
                    "Only archived asset selections can be restored."
                )
            if source_selection.pk == active_selection.pk:
                raise InvalidImageSelectionTransitionError(
                    "The active selection cannot be used as a restore source."
                )
            if source_selection.revision >= active_selection.revision:
                raise InvalidImageSelectionTransitionError(
                    "The restore source revision must be older than the active revision."
                )
            if source_selection.rendition_set_id is None:
                raise InvalidImageSelectionTransitionError(
                    "The restore source must reference a rendition set."
                )

            rendition_set, asset = _locked_asset_context(
                tenant_id,
                source_selection.rendition_set_id,
            )
            return _create_selection_revision(
                actor=actor,
                tenant_id=tenant_id,
                organization=organization,
                active_selection=active_selection,
                selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                rendition_set=rendition_set,
                alt_text=source_selection.alt_text,
                public_credit=source_selection.public_credit,
                asset=asset,
                evidence=None,
                technical_warnings=[],
                event_type=ImageReviewEvent.EventType.SELECTION_RESTORED,
                restored_from_selection=source_selection,
            )
    except IntegrityError as error:
        raise ImageSelectionConcurrencyError(
            "The image selection changed concurrently; reload before retrying."
        ) from error

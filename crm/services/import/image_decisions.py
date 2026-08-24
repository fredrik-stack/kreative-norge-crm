from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from crm.models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    ImageReviewEvent,
    ImportImageDecision,
    ImportRow,
    Organization,
    OrganizationImageSelection,
    TenantMembership,
)
from crm.services.images.selections import (
    ALLOWED_SELECTION_ROLES,
    AssetApprovalEvidence,
    IMAGE_APPROVAL_TEXT,
    IMAGE_APPROVAL_TEXT_VERSION,
    REQUIRED_RENDITION_VARIANTS,
    lock_organization_image_selection,
    remove_organization_image_to_fallback,
    validate_asset_approval_evidence,
)
from crm.services.images.safety_guards import (
    ImageSafetyGuardUnavailable,
    ImageSourceChecksumDenied,
    require_source_checksum_allowed,
)


class ImportImageDecisionError(ValueError):
    code = "invalid_import_image_decision"


class ImportImageDecisionFeatureDisabled(ImportImageDecisionError):
    code = "feature_disabled"


class ImportImageDecisionPermissionDenied(ImportImageDecisionError):
    code = "permission_denied"


class ImportImageDecisionConflict(ImportImageDecisionError):
    code = "stale_image_review"


class ImportImageDecisionNotReady(ImportImageDecisionError):
    code = "image_not_ready"


@dataclass(frozen=True, slots=True)
class ImportImageApplyResult:
    decision: ImportImageDecision
    selection: OrganizationImageSelection | None
    event: ImageReviewEvent | None
    changed: bool


def canonical_actor_snapshot(snapshot: dict[str, object]) -> tuple[dict[str, object], str]:
    if not isinstance(snapshot, dict) or not snapshot:
        raise ImportImageDecisionError("A non-empty proposed actor snapshot is required.")
    try:
        encoded = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ImportImageDecisionError("The proposed actor snapshot must be canonical JSON.") from error
    canonical = json.loads(encoded.decode("utf-8"))
    return canonical, hashlib.sha256(encoded).hexdigest()


def canonical_rendition_set_snapshot(
    rendition_set: ImageRenditionSet,
) -> tuple[dict[str, object], str]:
    renditions = list(
        ImageRendition.objects.filter(rendition_set=rendition_set)
        .order_by("variant", "pk")
        .values(
            "id",
            "tenant_id",
            "rendition_set_id",
            "variant",
            "output_format",
            "width",
            "height",
            "file_size_bytes",
            "checksum_sha256",
            "artifact_storage_key",
        )
    )
    snapshot = {
        "tenant_id": rendition_set.tenant_id,
        "rendition_set_id": rendition_set.pk,
        "asset_id": rendition_set.asset_id,
        "fit_mode": rendition_set.fit_mode,
        "focus_x": format(rendition_set.focus_x, "f"),
        "focus_y": format(rendition_set.focus_y, "f"),
        "zoom": format(rendition_set.zoom, "f"),
        "processing_version": rendition_set.processing_version,
        "render_config_hash_sha256": rendition_set.render_config_hash_sha256,
        "renditions": renditions,
    }
    encoded = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return json.loads(encoded.decode("utf-8")), hashlib.sha256(encoded).hexdigest()


def _require_feature() -> None:
    if not settings.IMPORT_IMAGE_DECISIONS_ENABLED:
        raise ImportImageDecisionFeatureDisabled("Import image decisions are disabled.")


def _require_actor(actor, tenant_id: int) -> None:
    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
        or not getattr(actor, "is_active", False)
        or not getattr(actor, "pk", None)
    ):
        raise ImportImageDecisionPermissionDenied("An active authenticated actor is required.")
    if actor.is_superuser:
        return
    if not TenantMembership.objects.filter(
        tenant_id=tenant_id,
        user_id=actor.pk,
        role__in=ALLOWED_SELECTION_ROLES,
    ).exists():
        raise ImportImageDecisionPermissionDenied(
            "The actor cannot review images in the import tenant."
        )


def _prepared_asset(
    *,
    tenant_id: int,
    asset_id: int | None,
    rendition_set_id: int | None,
) -> tuple[ImageAsset, ImageRenditionSet]:
    rendition_set = (
        ImageRenditionSet.objects.select_for_update()
        .filter(pk=rendition_set_id, tenant_id=tenant_id)
        .first()
    )
    asset = None
    if rendition_set is not None and rendition_set.asset_id == asset_id:
        asset = (
            ImageAsset.objects.select_for_update()
            .filter(pk=asset_id, tenant_id=tenant_id)
            .first()
        )
    if asset is None or rendition_set is None:
        raise ImportImageDecisionNotReady("The approved asset is not ready in the import tenant.")
    variants = list(
        ImageRendition.objects.select_for_update().filter(
            tenant_id=tenant_id,
            rendition_set=rendition_set,
        ).values_list("variant", flat=True)
    )
    if len(variants) != len(REQUIRED_RENDITION_VARIANTS) or set(variants) != REQUIRED_RENDITION_VARIANTS:
        raise ImportImageDecisionNotReady(
            "The approved rendition set must contain square, landscape, and share."
        )
    return asset, rendition_set


@transaction.atomic
def create_import_image_decision(
    *,
    import_row_id: int,
    actor,
    decision_kind: str,
    proposed_actor_snapshot: dict[str, object],
    target_organization_id: int | None = None,
    expected_selection_id: int | None = None,
    expected_selection_revision: int = 0,
    asset_id: int | None = None,
    rendition_set_id: int | None = None,
    approved_alt_text: str = "",
    approved_public_credit: str = "",
    asset_evidence: AssetApprovalEvidence | None = None,
) -> ImportImageDecision:
    _require_feature()
    row = (
        ImportRow.objects.select_for_update()
        .select_related("import_job")
        .filter(pk=import_row_id)
        .first()
    )
    if row is None:
        raise ImportImageDecisionError("The import row was not found.")
    tenant_id = row.import_job.tenant_id
    _require_actor(actor, tenant_id)
    if decision_kind not in ImportImageDecision.DecisionKind.values:
        raise ImportImageDecisionError("Unsupported import image decision kind.")

    target = None
    current_selection = None
    if target_organization_id is not None:
        target = Organization.objects.filter(
            pk=target_organization_id,
            tenant_id=tenant_id,
        ).first()
        if target is None:
            raise ImportImageDecisionError("The target organization was not found in the import tenant.")
        current_selection = OrganizationImageSelection.objects.filter(
            tenant_id=tenant_id,
            organization=target,
            status=OrganizationImageSelection.Status.ACTIVE,
        ).first()
        current_id = current_selection.pk if current_selection else None
        current_revision = current_selection.revision if current_selection else 0
        if expected_selection_id != current_id or expected_selection_revision != current_revision:
            raise ImportImageDecisionConflict("The organization image changed before review was saved.")
    elif expected_selection_id is not None or expected_selection_revision != 0:
        raise ImportImageDecisionError("A proposed new actor cannot have an expected selection.")

    asset = None
    rendition_set = None
    evidence = None
    rendition_set_snapshot: dict[str, object] = {}
    rendition_set_snapshot_hash = ""
    if decision_kind == ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE:
        asset, rendition_set = _prepared_asset(
            tenant_id=tenant_id,
            asset_id=asset_id,
            rendition_set_id=rendition_set_id,
        )
        if not isinstance(asset_evidence, AssetApprovalEvidence):
            raise ImportImageDecisionError("SET_APPROVED_IMAGE requires typed approval evidence.")
        evidence = asset_evidence
        validate_asset_approval_evidence(evidence)
        rendition_set_snapshot, rendition_set_snapshot_hash = (
            canonical_rendition_set_snapshot(rendition_set)
        )
        if settings.PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED:
            try:
                require_source_checksum_allowed(
                    tenant_id=tenant_id,
                    source_checksum_sha256=asset.checksum_sha256,
                )
            except (ImageSourceChecksumDenied, ImageSafetyGuardUnavailable) as error:
                raise ImportImageDecisionNotReady(
                    "The approved asset is not available for image review."
                ) from error
    elif asset_id is not None or rendition_set_id is not None or asset_evidence is not None:
        raise ImportImageDecisionError("Only SET_APPROVED_IMAGE can reference an asset.")
    if decision_kind == ImportImageDecision.DecisionKind.USE_APPROVED_FALLBACK:
        if not isinstance(approved_alt_text, str) or not approved_alt_text.strip():
            raise ImportImageDecisionError("USE_APPROVED_FALLBACK requires approved alt text.")

    snapshot, snapshot_hash = canonical_actor_snapshot(proposed_actor_snapshot)
    decision = ImportImageDecision(
        import_row=row,
        decided_by=actor,
        decision_kind=decision_kind,
        target_organization=target,
        expected_selection=current_selection,
        expected_selection_revision=expected_selection_revision,
        asset=asset,
        rendition_set=rendition_set,
        approved_alt_text=approved_alt_text,
        approved_public_credit=approved_public_credit,
        source_type_snapshot=evidence.source_type if evidence else "",
        source_url_snapshot=evidence.source_url if evidence else "",
        source_page_url_snapshot=evidence.source_page_url if evidence else "",
        provider_snapshot=evidence.provider if evidence else "",
        technical_warnings_snapshot=list(evidence.technical_warnings) if evidence else [],
        approval_text_version_snapshot=IMAGE_APPROVAL_TEXT_VERSION if evidence else "",
        approval_text_snapshot=IMAGE_APPROVAL_TEXT if evidence else "",
        asset_checksum_sha256_snapshot=asset.checksum_sha256 if asset else "",
        asset_validation_version_snapshot=asset.validation_version if asset else "",
        rendition_set_snapshot=rendition_set_snapshot,
        rendition_set_snapshot_hash_sha256=rendition_set_snapshot_hash,
        proposed_actor_snapshot=snapshot,
        canonical_snapshot_hash_sha256=snapshot_hash,
    )
    try:
        decision.full_clean()
    except ValidationError as error:
        raise ImportImageDecisionError("The typed image decision is invalid.") from error
    ImportImageDecision._base_objects._insert_from_import_service([decision])
    return decision


def _existing_applied_result(decision: ImportImageDecision) -> ImportImageApplyResult | None:
    event = ImageReviewEvent.objects.filter(import_image_decision=decision).select_related("selection").first()
    if event is None:
        return None
    return ImportImageApplyResult(
        decision=decision,
        selection=event.selection,
        event=event,
        changed=True,
    )


@transaction.atomic
def apply_import_image_decision(
    *,
    decision: ImportImageDecision,
    organization: Organization,
    organization_was_created: bool,
    proposed_actor_snapshot: dict[str, object],
) -> ImportImageApplyResult:
    _require_feature()
    decision = (
        ImportImageDecision.objects.select_for_update(of=("self",))
        .select_related(
            "import_row__import_job",
            "decided_by",
            "target_organization",
            "expected_selection",
            "asset",
            "rendition_set",
        )
        .get(pk=decision.pk)
    )
    tenant_id = decision.import_row.import_job.tenant_id
    if organization.tenant_id != tenant_id:
        raise ImportImageDecisionError("The target organization was not found in the import tenant.")
    if decision.target_organization_id is None:
        if not organization_was_created:
            raise ImportImageDecisionConflict("The reviewed proposed actor resolved to an existing organization.")
    elif organization_was_created or organization.pk != decision.target_organization_id:
        raise ImportImageDecisionConflict("The reviewed target organization changed before commit.")

    _, stored_snapshot_hash = canonical_actor_snapshot(decision.proposed_actor_snapshot)
    _, snapshot_hash = canonical_actor_snapshot(proposed_actor_snapshot)
    if (
        stored_snapshot_hash != decision.canonical_snapshot_hash_sha256
        or snapshot_hash != decision.canonical_snapshot_hash_sha256
    ):
        raise ImportImageDecisionConflict("The proposed actor changed after image review.")

    existing = _existing_applied_result(decision)
    if existing is not None:
        return existing

    active_selection = (
        OrganizationImageSelection.objects.select_for_update()
        .filter(
            tenant_id=tenant_id,
            organization=organization,
            status=OrganizationImageSelection.Status.ACTIVE,
        )
        .first()
    )
    active_id = active_selection.pk if active_selection else None
    active_revision = active_selection.revision if active_selection else 0
    if (
        active_id != decision.expected_selection_id
        or active_revision != decision.expected_selection_revision
    ):
        raise ImportImageDecisionConflict("The active image selection changed after review.")

    if decision.decision_kind == ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE:
        return ImportImageApplyResult(
            decision=decision,
            selection=active_selection,
            event=None,
            changed=False,
        )

    if decision.decision_kind == ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE:
        if (
            decision.asset is None
            or decision.rendition_set is None
            or decision.rendition_set.asset_id != decision.asset_id
        ):
            raise ImportImageDecisionNotReady("The approved image state changed after review.")
        current_asset, current_rendition_set = _prepared_asset(
            tenant_id=tenant_id,
            asset_id=decision.asset_id,
            rendition_set_id=decision.rendition_set_id,
        )
        if (
            current_asset.checksum_sha256 != decision.asset_checksum_sha256_snapshot
            or current_asset.validation_version
            != decision.asset_validation_version_snapshot
        ):
            raise ImportImageDecisionNotReady("The approved image state changed after review.")
        current_rendition_snapshot, current_rendition_hash = (
            canonical_rendition_set_snapshot(current_rendition_set)
        )
        try:
            stored_rendition_encoded = json.dumps(
                decision.rendition_set_snapshot,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise ImportImageDecisionNotReady(
                "The reviewed rendition snapshot is invalid."
            ) from error
        stored_rendition_hash = hashlib.sha256(stored_rendition_encoded).hexdigest()
        if (
            stored_rendition_hash != decision.rendition_set_snapshot_hash_sha256
            or current_rendition_hash != decision.rendition_set_snapshot_hash_sha256
            or current_rendition_snapshot != decision.rendition_set_snapshot
        ):
            raise ImportImageDecisionNotReady(
                "The approved rendition state changed after review."
            )
        result = lock_organization_image_selection(
            actor=decision.decided_by,
            tenant_id=tenant_id,
            organization_id=organization.pk,
            expected_revision=decision.expected_selection_revision,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set_id=decision.rendition_set_id,
            alt_text=decision.approved_alt_text,
            public_credit=decision.approved_public_credit,
            asset_evidence=AssetApprovalEvidence(
                source_type=decision.source_type_snapshot,
                source_url=decision.source_url_snapshot,
                source_page_url=decision.source_page_url_snapshot,
                provider=decision.provider_snapshot,
                technical_warnings=tuple(decision.technical_warnings_snapshot),
            ),
            import_image_decision=decision,
        )
    elif active_selection is None:
        result = lock_organization_image_selection(
            actor=decision.decided_by,
            tenant_id=tenant_id,
            organization_id=organization.pk,
            expected_revision=0,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            alt_text=decision.approved_alt_text,
            public_credit="",
            import_image_decision=decision,
        )
    else:
        result = remove_organization_image_to_fallback(
            actor=decision.decided_by,
            tenant_id=tenant_id,
            organization_id=organization.pk,
            expected_revision=decision.expected_selection_revision,
            fallback_alt_text=decision.approved_alt_text,
            import_image_decision=decision,
        )
    return ImportImageApplyResult(
        decision=decision,
        selection=result.selection,
        event=result.event,
        changed=True,
    )

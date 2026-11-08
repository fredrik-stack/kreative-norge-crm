"""Explicit Editor commands over the existing immutable release lifecycle."""
from contextlib import contextmanager
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction

from crm.models import Organization, OrganizationImageSelection, OrganizationImageRelease, ImageReviewEvent, TenantMembership
from .projection import project_public_image
from .releases import create_organization_image_release
from .bridge_client import ImageSafetyBridgeClient, ImageSafetyBridgeError
from .selections import (
    ALLOWED_SELECTION_ROLES, ExpectedRevisionConflictError,
    ImageSelectionPermissionDenied, remove_organization_image_to_fallback,
)

logger = logging.getLogger("crm.images.publication")


def _has_actor_image_approval(selection):
    # Historical v1 approvals are never silently migrated to the new intent.
    return ImageReviewEvent.objects.filter(
        tenant_id=selection.tenant_id, organization_id=selection.organization_id,
        selection_id=selection.pk, selection_revision_snapshot=selection.revision,
        rendition_set_id=selection.rendition_set_id,
        approval_text_version_snapshot="image-approval-v2-actor-image",
        event_type__in=(ImageReviewEvent.EventType.SELECTION_LOCKED, ImageReviewEvent.EventType.SELECTION_REPLACED),
    ).exists()


def image_use_state(selection):
    """Authenticated advisory state, including unpublished preparation.

    This never grants public access. Projection and serving retain their strict
    published check; completion reauthorizes and locks the exact revision.
    """
    if selection is None or selection.selection_kind != OrganizationImageSelection.SelectionKind.ASSET:
        return {"pending": False, "ready": False}
    if not publication_enabled() or not _has_actor_image_approval(selection):
        return {"pending": False, "ready": False}
    from .release_validation import validated_release_mappings, PublicReleaseValidationError
    from .materialization import ImageMaterializationError, verify_materialized_rendition
    from .serving import _materialization_input
    from .projection import _authorization_payload
    try:
        release = OrganizationImageRelease.objects.select_related(
            "organization", "selection", "rendition_set__asset"
        ).prefetch_related("renditions__rendition").get(selection_id=selection.pk)
        mappings = validated_release_mappings(release, require_published=False)
        variants = sorted(mappings)
        decisions = ImageSafetyBridgeClient(timeout=5).authorize_many([
            _authorization_payload(release, mappings[v], v) for v in variants
        ])
        if len(decisions) != 3 or not all(decision.authorized for decision in decisions):
            return {"pending": True, "ready": False}
        for mapping in mappings.values():
            verify_materialized_rendition(_materialization_input(release, mapping))
    except (OrganizationImageRelease.DoesNotExist, PublicReleaseValidationError,
            ImageSafetyBridgeError, ImageMaterializationError):
        return {"pending": True, "ready": False}
    return {"pending": False, "ready": True}


class ImagePublicationError(ValueError):
    def __init__(self, code, message, status_code=400):
        self.code, self.status_code = code, status_code
        super().__init__(message)


def publication_enabled():
    return all(getattr(settings, name) for name in (
        "IMAGE_ASSET_FEATURE_ENABLED", "PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED",
        "PUBLIC_IMAGE_SERVING_ENABLED", "PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED",
    ))


def public_image_state(organization):
    if not publication_enabled():
        return {"enabled": False, "kind": "system_fallback", "reason": "disabled", "image": None}
    result = project_public_image(organization)
    return {"enabled": True, "kind": result.projection.kind,
            "reason": result.reason, "image": result.projection.as_dict()}


@contextmanager
def _authorized_organization(*, actor, tenant_id, organization_id, expected_revision, confirmed):
    if not publication_enabled():
        raise ImagePublicationError("publication_disabled", "Offentlig bildepublisering er ikke aktivert.", 404)
    if confirmed is not True:
        raise ImagePublicationError("confirmation_required", "Bekreft at bildet skal tas i bruk på PUBLIC.")
    if type(expected_revision) is not int or expected_revision < 0:
        raise ImagePublicationError("invalid_revision", "Oppgi gjeldende bilderevisjon.")
    if actor is None or not getattr(actor, "is_authenticated", False) or not actor.pk:
        raise ImageSelectionPermissionDenied("En aktiv innlogget bruker kreves.")
    with transaction.atomic():
        # SHARE is compatible with the strict request boundary and fences user/
        # membership changes throughout reservation, materialization and activation.
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='2s'")
            cursor.execute("SET LOCAL statement_timeout='30s'")
            table = connection.ops.quote_name(get_user_model()._meta.db_table)
            cursor.execute(f"SELECT is_active,is_superuser FROM {table} WHERE id=%s FOR SHARE", [actor.pk])
            user = cursor.fetchone()
            if user is None or not user[0]:
                raise ImageSelectionPermissionDenied("En aktiv innlogget bruker kreves.")
            cursor.execute("SELECT role,is_active FROM crm_tenantmembership WHERE user_id=%s AND tenant_id=%s FOR SHARE", [actor.pk, tenant_id])
            membership = cursor.fetchone()
        from crm.tenant_access import strict_tenant_access, require_tenant_operation
        if strict_tenant_access():
            require_tenant_operation(tenant_id, ALLOWED_SELECTION_ROLES, actor=actor)
        elif not user[1] and (not membership or not membership[1] or membership[0] not in ALLOWED_SELECTION_ROLES):
            raise ImageSelectionPermissionDenied("Du kan ikke publisere bilder i dette kontoret.")
        organization = Organization.objects.select_for_update().filter(pk=organization_id, tenant_id=tenant_id).first()
        if organization is None:
            raise ImagePublicationError("not_found", "Aktøren finnes ikke i dette kontoret.", 404)
        selection = OrganizationImageSelection.objects.select_for_update().filter(
            organization_id=organization_id, tenant_id=tenant_id,
            status=OrganizationImageSelection.Status.ACTIVE,
        ).first()
        if selection is None or selection.revision != expected_revision:
            raise ExpectedRevisionConflictError("Bildet er endret. Last inn gjeldende bilde før du prøver igjen.")
        yield organization, selection


def publish_organization_image(**options):
    with _authorized_organization(**options) as (organization, selection):
        if not organization.is_published:
            raise ImagePublicationError("organization_unpublished", "Publiser aktørprofilen før bildet tas i bruk på PUBLIC.", 409)
        if selection.selection_kind != OrganizationImageSelection.SelectionKind.ASSET:
            raise ImagePublicationError("asset_required", "Velg og godkjenn et bilde først.", 409)
        result = create_organization_image_release(selection=selection)
        state = public_image_state(organization)
        if state["kind"] != "asset":
            raise ImagePublicationError("publication_unverified", "Offentlig bilde kunne ikke bekreftes. Kontroller status og prøv samme revisjon igjen.", 503)
        logger.info("public_image_ready actor_user_id=%s tenant_id=%s organization_id=%s selection_id=%s revision=%s release_id=%s",
                    options['actor'].pk, organization.tenant_id, organization.pk, selection.pk, selection.revision, result.release.release_id)
        return {"release_id": str(result.release.release_id), "revision": selection.revision, "public_image": state}


def complete_organization_image(**options):
    """Second durable server step of the single image confirmation UI action.

    Approval was committed by the preceding HTTP request. Keeping that boundary
    also protects strict tenant mode from rollback/reuse of reserved selection
    identities if the external safety or filesystem step fails.
    """
    with _authorized_organization(**options) as (organization, selection):
        if not _has_actor_image_approval(selection):
            raise ImagePublicationError("image_confirmation_required", "Velg og bekreft bildet i gjeldende bildeflyt.", 409)
        result = create_organization_image_release(selection=selection)
        state = image_use_state(selection)
        if not state["ready"]:
            raise ImagePublicationError("publication_unverified", "Bildet er godkjent, men klargjøringen kunne ikke bekreftes. Last inn status før du fullfører på nytt.", 503)
        logger.info("actor_image_ready actor_user_id=%s tenant_id=%s organization_id=%s selection_id=%s revision=%s release_id=%s",
                    options['actor'].pk, organization.tenant_id, organization.pk, selection.pk, selection.revision, result.release.release_id)
        return {"release_id": str(result.release.release_id), "revision": selection.revision,
                "image_use": state, "public_image": public_image_state(organization)}


def use_organization_image_fallback(**options):
    with _authorized_organization(**options) as (organization, selection):
        result = remove_organization_image_to_fallback(
            actor=options['actor'], tenant_id=organization.tenant_id,
            organization_id=organization.pk, expected_revision=selection.revision,
            fallback_alt_text="Standardbilde for aktør",
        )
        return {"revision": result.selection.revision, "public_image": public_image_state(organization)}

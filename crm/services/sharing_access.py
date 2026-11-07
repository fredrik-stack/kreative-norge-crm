"""Inactive ADR-011 policy foundation, independent of legacy role fallback.

A result is a point-in-time assessment, never a reusable authorization token.
Future writers must recheck inside their atomic revision/audit boundary.
"""
from dataclasses import dataclass
from enum import StrEnum

from django.conf import settings
from django.db.models import Exists, OuterRef, Subquery
from django.db.models.functions import Now

from crm.models import (
    Organization, OrganizationTenantAssignment, Person, PersonTenantAssignment,
    SharingAgreement, SharingAgreementAcceptance, TenantMembership,
)


class Capability(StrEnum):
    SHARED_MATCH = "shared_match"
    ADD_TO_OWN_TENANT = "add_to_own_tenant"
    EDIT_SHARED_CORE = "edit_shared_core"
    EDIT_PUBLISHED_CORE = "edit_published_core"
    PUBLISH = "publish"
    READ_PRIVATE_OVERLAY = "read_private_overlay"
    WRITE_PRIVATE_OVERLAY = "write_private_overlay"
    WRITE_IMAGE_HOME = "write_image_home"
    TRANSFER_IMAGE_HOME = "transfer_image_home"


READERS = frozenset(TenantMembership.Role.values)
EDITORS = READERS - {TenantMembership.Role.LESER}
# Image-home capabilities are named but deliberately ungranted until its bridge.
CAPABILITY_ROLES = {
    Capability.SHARED_MATCH: READERS,
    Capability.ADD_TO_OWN_TENANT: EDITORS,
    Capability.EDIT_SHARED_CORE: EDITORS,
    Capability.EDIT_PUBLISHED_CORE: EDITORS,
    Capability.PUBLISH: EDITORS,
    Capability.READ_PRIVATE_OVERLAY: READERS,
    Capability.WRITE_PRIVATE_OVERLAY: EDITORS,
}


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    code: str
    agreement_id: int | None = None
    assignment_id: int | None = None


def assess_access(*, user_id, tenant_id, sharing_domain_id, capability,
                  entity_type=None, entity_id=None, assignment_id=None):
    """Require explicit trusted request context; caller must bind active tenant.

    Shared match has no object. Add targets an existing object in the exact
    domain, only for this membership's tenant. Other operations require its
    exact assignment. Private operations can never use another tenant's row.
    No serializer, matching query, writer or endpoint is exposed here.
    """
    deny = lambda code: AccessDecision(False, code)
    if not settings.SHARING_ACCESS_ENABLED:
        return deny("DISABLED")
    if any(type(value) is not int or value <= 0 for value in (user_id, tenant_id, sharing_domain_id)):
        return deny("INVALID_CONTEXT")
    try:
        capability = Capability(capability)
    except (ValueError, TypeError):
        return deny("UNKNOWN_CAPABILITY")
    # One SQL statement evaluates identity, membership, domain and agreement
    # acceptance against one PostgreSQL statement snapshot, using database time.
    current = SharingAgreement.objects.filter(
        sharing_domain_id=sharing_domain_id, effective_at__lte=Now(),
    ).order_by("-effective_at").values("pk")[:1]
    accepted = SharingAgreementAcceptance.objects.filter(
        user_id=OuterRef("user_id"), agreement_id=OuterRef("current_agreement"),
        revocation__isnull=True,
    )
    membership = TenantMembership.objects.filter(
        user_id=user_id, tenant_id=tenant_id, is_active=True,
        user__is_active=True, tenant__sharing_domain_id=sharing_domain_id,
    ).annotate(current_agreement=Subquery(current), accepted=Exists(accepted)).values(
        "role", "current_agreement", "accepted",
    ).first()
    if membership is None:
        return deny("INVALID_MEMBERSHIP")
    if membership["role"] not in CAPABILITY_ROLES.get(capability, frozenset()):
        return deny("CAPABILITY_DENIED")
    if not membership["current_agreement"] or not membership["accepted"]:
        return deny("AGREEMENT_REQUIRED")
    agreement_id = membership["current_agreement"]
    if capability == Capability.SHARED_MATCH:
        if any(value is not None for value in (entity_type, entity_id, assignment_id)):
            return deny("INVALID_SCOPE")
        return AccessDecision(True, "ALLOWED", agreement_id)
    cases = {"organization": (Organization, OrganizationTenantAssignment, "organization_id"),
             "person": (Person, PersonTenantAssignment, "person_id")}
    if not isinstance(entity_type, str) or entity_type not in cases or type(entity_id) is not int or entity_id <= 0:
        return deny("INVALID_SCOPE")
    model, assignments, field = cases[entity_type]
    fields = ("pk", "is_published") if model is Organization else ("pk",)
    entity = model.objects.filter(pk=entity_id, sharing_domain_id=sharing_domain_id).values(*fields).first()
    if entity is None:
        return deny("INVALID_SCOPE")
    if capability in {Capability.PUBLISH, Capability.EDIT_PUBLISHED_CORE} and model is not Organization:
        return deny("INVALID_SCOPE")
    if capability == Capability.EDIT_SHARED_CORE and model is Organization and entity["is_published"]:
        return deny("PUBLISHED_CAPABILITY_REQUIRED")
    if capability == Capability.ADD_TO_OWN_TENANT:
        if assignment_id is not None:
            return deny("INVALID_SCOPE")
        return AccessDecision(True, "ALLOWED", agreement_id)
    if type(assignment_id) is not int or assignment_id <= 0:
        return deny("INVALID_ASSIGNMENT")
    assigned = assignments.objects.filter(
        pk=assignment_id, tenant_id=tenant_id, tenant__sharing_domain_id=sharing_domain_id,
        **{field: entity_id},
    ).exists()
    if not assigned:
        return deny("INVALID_ASSIGNMENT")
    return AccessDecision(True, "ALLOWED", agreement_id, assignment_id)

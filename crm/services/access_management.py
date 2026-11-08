"""Small ADR-011 administration boundary; grants never confer shared data access."""
from contextlib import contextmanager
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction, DatabaseError, InterfaceError
from django.db.models.functions import Now

from crm.models import (
    AccessManagementGrant as Grant, AccessManagementGrantRevocation as GrantRevocation,
    MembershipManagementAudit, TenantMembership, Tenant, SharingDomain,
    SharingAgreement, SharingAgreementAcceptance, SharingAgreementRevocation,
)


class ManagementError(Exception):
    pass


def positive(*values):
    if any(type(v) is not int or v <= 0 for v in values):
        raise ManagementError("INVALID_CONTEXT")


@contextmanager
def boundary():
    if settings.ACCESS_MANAGEMENT_ENABLED is not True:
        raise ManagementError("DISABLED")
    if connection.vendor != "postgresql" or connection.in_atomic_block or not connection.get_autocommit():
        raise ManagementError("OUTER_TRANSACTION_UNSUPPORTED")
    try:
        with transaction.atomic(durable=True):
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                cursor.execute("SET LOCAL lock_timeout = '2s'")
                cursor.execute("SET LOCAL statement_timeout = '30s'")
            yield
    except (DatabaseError, InterfaceError):
        raise ManagementError("OUTCOME_REQUIRES_READBACK") from None


def _lock(domain_id, *user_ids):
    positive(domain_id, *user_ids)
    if not SharingDomain.objects.select_for_update().filter(pk=domain_id).exists():
        raise ManagementError("ACCESS_DENIED")
    users = list(get_user_model().objects.select_for_update().filter(pk__in=user_ids).order_by("pk"))
    if {u.pk for u in users} != set(user_ids) or any(not u.is_active for u in users):
        raise ManagementError("ACCESS_DENIED")


def _grant(actor_id, domain_id, action, tenant_id=None):
    grant = Grant.objects.select_for_update(of=("self",)).filter(user_id=actor_id, sharing_domain_id=domain_id,
        action=action, tenant_id=tenant_id, revocation__isnull=True).order_by("pk").first()
    if grant is None:
        raise ManagementError("ACCESS_DENIED")
    if tenant_id is not None and not Tenant.objects.filter(pk=tenant_id, sharing_domain_id=domain_id).exists():
        raise ManagementError("ACCESS_DENIED")
    return grant


def _membership(actor_id, tenant_id, domain_id):
    membership = TenantMembership.objects.select_for_update(of=("self",)).filter(
        user_id=actor_id, tenant_id=tenant_id, is_active=True,
        tenant__sharing_domain_id=domain_id, role__in=TenantMembership.Role.values).first()
    if membership is None:
        raise ManagementError("ACCESS_DENIED")
    return membership


def _current(domain_id):
    return SharingAgreement.objects.filter(sharing_domain_id=domain_id,
        effective_at__lte=Now()).order_by("-effective_at").first()


def _membership_row(row):
    return {"username": row.user.get_username(), "role": row.role, "is_active": row.is_active,
        "expected_updated_at": row.updated_at.isoformat()}


def list_memberships(*, actor_id, tenant_id, domain_id):
    positive(actor_id, tenant_id, domain_id)
    with boundary():
        _lock(domain_id, actor_id)
        _grant(actor_id, domain_id, Grant.Action.MANAGE_TENANT_MEMBERSHIPS, tenant_id)
        return [_membership_row(row) for row in TenantMembership.objects.filter(
            tenant_id=tenant_id).select_related("user").order_by("user__username")]


def set_membership(*, actor_id, tenant_id, domain_id, username, role, is_active, expected_updated_at):
    positive(actor_id, tenant_id, domain_id)
    if (type(username) is not str or not username or role not in TenantMembership.Role.values
            or type(is_active) is not bool or (expected_updated_at is not None and type(expected_updated_at) is not str)):
        raise ManagementError("INVALID_VALUES")
    with boundary():
        # Look up the existing account only; no account creation or user enumeration.
        # Lock the domain before users, matching agreement/writer lock order.
        target = get_user_model().objects.filter(username=username).first()
        _lock(domain_id, *sorted({actor_id, target.pk} if target else {actor_id}))
        grant = _grant(actor_id, domain_id, Grant.Action.MANAGE_TENANT_MEMBERSHIPS, tenant_id)
        if target is None or not target.is_active:
            raise ManagementError("TARGET_UNAVAILABLE")
        if target.pk == actor_id:
            raise ManagementError("SELF_CHANGE_DENIED")
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM crm_tenant WHERE id=%s FOR SHARE", [tenant_id])
        row = TenantMembership.objects.select_for_update().filter(user=target, tenant_id=tenant_id).first()
        previous_role, previous_active = (row.role, row.is_active) if row else (None, None)
        if (row.updated_at.isoformat() if row else None) != expected_updated_at:
            raise ManagementError("STALE_MEMBERSHIP")
        if row and (row.role, row.is_active) == (role, is_active):
            return _membership_row(row)
        if row is None:
            row = TenantMembership(user=target, tenant_id=tenant_id)
        row.role, row.is_active = role, is_active
        row.save()
        MembershipManagementAudit.objects.create(actor_id=actor_id, target_user_id=target.pk,
            tenant_id=tenant_id, sharing_domain_id=domain_id, grant_id=grant.pk,
            previous_role=previous_role, role=role, previous_active=previous_active,
            is_active=is_active, occurred_at=Now())
        return _membership_row(row)


def publish_agreement(*, actor_id, domain_id, version, text, effective_at, legal_approval_reference, approved):
    positive(actor_id, domain_id, version)
    if approved is not True:
        raise ManagementError("LEGAL_APPROVAL_REQUIRED")
    if (type(text) is not str or not text.strip() or type(legal_approval_reference) is not str
            or not legal_approval_reference.strip() or len(legal_approval_reference)>200):
        raise ManagementError("INVALID_VALUES")
    with boundary():
        _lock(domain_id, actor_id)
        _grant(actor_id, domain_id, Grant.Action.PUBLISH_SHARING_AGREEMENT)
        row = SharingAgreement.objects.create(sharing_domain_id=domain_id, version=version, text=text,
            effective_at=effective_at, created_by_id=actor_id, legal_approval_reference=legal_approval_reference)
        return {"agreement_id": row.pk, "version": row.version}


def accept_agreement(*, actor_id, tenant_id, domain_id, agreement_id, confirmed):
    positive(actor_id, tenant_id, domain_id, agreement_id)
    if confirmed is not True:
        raise ManagementError("EXPLICIT_ACCEPTANCE_REQUIRED")
    with boundary():
        _lock(domain_id, actor_id)
        _membership(actor_id, tenant_id, domain_id)
        current = _current(domain_id)
        if current is None or current.pk != agreement_id:
            raise ManagementError("STALE_AGREEMENT")
        if SharingAgreementAcceptance.objects.filter(user_id=actor_id,
                agreement_id=agreement_id, revocation__isnull=True).exists():
            raise ManagementError("ALREADY_ACCEPTED")
        # Existing DB trigger rechecks the current version at insertion time, including clock transitions.
        row = SharingAgreementAcceptance.objects.create(user_id=actor_id, tenant_id=tenant_id, agreement=current)
        return {"acceptance_id": row.pk}


def revoke_acceptance(*, actor_id, acceptance_id):
    positive(actor_id, acceptance_id)
    with boundary():
        row = SharingAgreementAcceptance.objects.filter(pk=acceptance_id, user_id=actor_id).select_related("agreement").first()
        if row is None:
            raise ManagementError("ACCESS_DENIED")
        # No current membership or acceptance required to withdraw one's own acceptance.
        _lock(row.agreement.sharing_domain_id, actor_id)
        if SharingAgreementRevocation.objects.filter(acceptance_id=acceptance_id).exists():
            return {"revoked": True}
        SharingAgreementRevocation.objects.create(acceptance_id=acceptance_id, actor_id=actor_id)
        return {"revoked": True}


def context(*, actor_id):
    positive(actor_id)
    if settings.ACCESS_MANAGEMENT_ENABLED is not True:
        return {"enabled": False, "memberships": [], "grants": [], "acceptances": [], "published_agreements": []}
    if not get_user_model().objects.filter(pk=actor_id, is_active=True).exists():
        raise ManagementError("ACCESS_DENIED")
    memberships = list(TenantMembership.objects.filter(user_id=actor_id, is_active=True,
        role__in=TenantMembership.Role.values, tenant__sharing_domain__isnull=False).select_related("tenant"))
    result = []
    for row in memberships:
        current = _current(row.tenant.sharing_domain_id)
        result.append({"tenant_id": row.tenant_id, "tenant_name": row.tenant.name,
            "domain_id": row.tenant.sharing_domain_id, "role": row.role,
            "agreement": None if current is None else {"id": current.pk, "version": current.version,
                "text": current.text, "effective_at": current.effective_at.isoformat()}})
    grants = [{"action": row.action, "tenant_id": row.tenant_id,
        "tenant_name": row.tenant.name if row.tenant else None,
        "domain_id": row.sharing_domain_id, "domain_name": row.sharing_domain.name}
        for row in Grant.objects.filter(user_id=actor_id, revocation__isnull=True).select_related("tenant", "sharing_domain")
        if row.tenant is None or row.tenant.sharing_domain_id == row.sharing_domain_id]
    acceptances = [{"id": row.pk, "agreement_id": row.agreement_id,
        "domain_id": row.agreement.sharing_domain_id, "version": row.agreement.version,
        "revoked": hasattr(row, "revocation")}
        for row in SharingAgreementAcceptance.objects.filter(user_id=actor_id).select_related("agreement", "revocation")]
    publishing_domains = {g["domain_id"] for g in grants if g["action"] == Grant.Action.PUBLISH_SHARING_AGREEMENT}
    publications = [{"id": a.pk, "domain_id": a.sharing_domain_id, "version": a.version,
        "text": a.text, "effective_at": a.effective_at.isoformat(), "legal_approval_reference": a.legal_approval_reference}
        for a in SharingAgreement.objects.filter(sharing_domain_id__in=publishing_domains).order_by("sharing_domain_id", "version")]
    return {"enabled": True, "memberships": result, "grants": grants, "acceptances": acceptances,
        "published_agreements": publications}


def appoint(*, actor_id, user_id, domain_id, tenant_id, action, request_id, mandate_reference, expected_database):
    """Privileged offline appointment under a SEPARATE mandate; no runtime caller."""
    positive(actor_id, user_id, domain_id)
    if actor_id == user_id:
        raise ManagementError("SELF_APPOINTMENT_DENIED")
    if (type(request_id) is not UUID or not mandate_reference.strip() or len(mandate_reference)>200
            or action not in Grant.Action.values or connection.settings_dict["NAME"] != expected_database
            or ((action == Grant.Action.MANAGE_TENANT_MEMBERSHIPS) != (tenant_id is not None))):
        raise ManagementError("INVALID_APPOINTMENT")
    with boundary():
        _lock(domain_id, *sorted({actor_id, user_id}))
        if tenant_id is not None and not Tenant.objects.filter(pk=tenant_id, sharing_domain_id=domain_id).exists():
            raise ManagementError("INVALID_SCOPE")
        data = dict(user_id=user_id, sharing_domain_id=domain_id, tenant_id=tenant_id,
            action=action, appointed_by_id=actor_id, mandate_reference=mandate_reference)
        existing = Grant.objects.filter(request_id=request_id).first()
        if existing:
            if any(getattr(existing,k) != v for k,v in data.items()):
                raise ManagementError("APPOINTMENT_CONFLICT")
            return existing.pk
        return Grant.objects.create(request_id=request_id, **data).pk


def withdraw_appointment(*, actor_id, grant_id, mandate_reference, expected_database):
    positive(actor_id, grant_id)
    if not mandate_reference.strip() or len(mandate_reference)>200 or connection.settings_dict["NAME"] != expected_database:
        raise ManagementError("INVALID_APPOINTMENT")
    with boundary():
        row = Grant.objects.filter(pk=grant_id).first()
        if row is None:
            raise ManagementError("INVALID_SCOPE")
        _lock(row.sharing_domain_id, actor_id)
        existing = GrantRevocation.objects.filter(grant=row).first()
        if existing:
            if (existing.actor_id, existing.mandate_reference) != (actor_id, mandate_reference):
                raise ManagementError("APPOINTMENT_CONFLICT")
            return existing.pk
        return GrantRevocation.objects.create(grant=row, actor_id=actor_id, mandate_reference=mandate_reference).pk

"""ADR-011: deliberately disconnected, narrow writer; no request callers.

The canonical counter counts ONLY this service's writes. The DB stamp also
invalidates snapshots after legacy edits of this field contract/publication.
Neither is a grant or an audit/revision of all legacy/profile/M2M changes.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction, OperationalError
from django.db.models import Max

from crm.models import (
    CanonicalWriteAudit, Organization, Person, OrganizationTenantAssignment,
    PersonTenantAssignment, SharingDomain, TenantMembership,
)
from crm.services import sharing_access


class CanonicalWriteError(Exception):
    """Only fixed, non-PII codes are exposed by the supported service."""


@dataclass(frozen=True)
class Revision:
    entity_type: str
    entity_id: int
    sharing_domain_id: int
    revision: int
    write_stamp: UUID


CASES = {
    "organization": (Organization, OrganizationTenantAssignment, "organization_id", frozenset({"name", "description"})),
    "person": (Person, PersonTenantAssignment, "person_id", frozenset({"full_name"})),
}
ACTIONS = frozenset({sharing_access.Capability.EDIT_SHARED_CORE, sharing_access.Capability.EDIT_PUBLISHED_CORE})


def _enabled():
    if settings.CANONICAL_WRITER_ENABLED is not True or settings.SHARING_ACCESS_ENABLED is not True:
        raise CanonicalWriteError("WRITER_DISABLED")


@contextmanager
def _boundary():
    _enabled()
    if connection.vendor != "postgresql" or connection.in_atomic_block or not connection.get_autocommit():
        raise CanonicalWriteError("OUTER_TRANSACTION_UNSUPPORTED")
    try:
        with transaction.atomic(durable=True):
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                cursor.execute("SET LOCAL lock_timeout = '2s'")
                cursor.execute("SET LOCAL statement_timeout = '30s'")
            yield
    except OperationalError:
        # Includes lock timeout, deadlock or a lost connection/COMMIT response.
        # No blind retry: callers must obtain a fresh revision/read back audit.
        raise CanonicalWriteError("WRITE_OUTCOME_REQUIRES_READBACK") from None


def _lock_context(*, user_id, tenant_id, sharing_domain_id, entity_type, entity_id, assignment_id, capability):
    if any(type(v) is not int or v <= 0 for v in (user_id, tenant_id, sharing_domain_id, entity_id, assignment_id)):
        raise CanonicalWriteError("INVALID_CONTEXT")
    if not isinstance(entity_type, str) or entity_type not in CASES:
        raise CanonicalWriteError("INVALID_SCOPE")
    try:
        capability = sharing_access.Capability(capability)
    except (ValueError, TypeError):
        raise CanonicalWriteError("INVALID_CAPABILITY") from None
    if capability not in ACTIONS:
        raise CanonicalWriteError("INVALID_CAPABILITY")
    model, assignments, field, fields = CASES[entity_type]
    # Same domain -> user order as agreement acceptance/revocation triggers.
    # SHARE on tenant is compatible with the legacy profile guard's SHARE.
    if not SharingDomain.objects.select_for_update().filter(pk=sharing_domain_id).values("pk").first():
        raise CanonicalWriteError("ACCESS_DENIED")
    if not get_user_model().objects.select_for_update().filter(pk=user_id).values("pk").first():
        raise CanonicalWriteError("ACCESS_DENIED")
    with connection.cursor() as cursor:
        cursor.execute('SELECT id FROM crm_tenant WHERE id=%s FOR SHARE', [tenant_id])
        if cursor.fetchone() is None:
            raise CanonicalWriteError("ACCESS_DENIED")
    if not TenantMembership.objects.select_for_update(of=("self",)).filter(user_id=user_id, tenant_id=tenant_id).order_by("pk").values("pk").first():
        raise CanonicalWriteError("ACCESS_DENIED")
    columns = ["pk", "sharing_domain_id", "canonical_write_stamp"]
    if model is Organization:
        columns.append("is_published")
    entity = model.objects.select_for_update().filter(pk=entity_id).values(*columns).first()
    if entity is None:
        raise CanonicalWriteError("ACCESS_DENIED")
    if not assignments.objects.select_for_update().filter(pk=assignment_id, tenant_id=tenant_id, **{field: entity_id}).values("pk").first():
        raise CanonicalWriteError("ACCESS_DENIED")
    # Always fresh after waits. Never accept a caller-supplied AccessDecision.
    decision = sharing_access.assess_access(user_id=user_id, tenant_id=tenant_id,
        sharing_domain_id=sharing_domain_id, capability=capability,
        entity_type=entity_type, entity_id=entity_id, assignment_id=assignment_id)
    if not decision.allowed:
        raise CanonicalWriteError(decision.code)
    return model, fields, entity, decision, capability


def _revision(entity_type, entity_id, sharing_domain_id, entity):
    counter = CanonicalWriteAudit.objects.filter(entity_type=entity_type, entity_id=entity_id).aggregate(n=Max("revision"))["n"] or 0
    return Revision(entity_type, entity_id, sharing_domain_id, counter, entity["canonical_write_stamp"])


def get_revision(**context):
    """Authorized internal metadata snapshot only; no row initialization or UI."""
    with _boundary():
        _, _, entity, _, _ = _lock_context(**context)
        return _revision(context["entity_type"], context["entity_id"], context["sharing_domain_id"], entity)


def write_core(*, expected_revision, values, **context):
    """Explicit patch of the three approved representative fields only.

    No normalization, import merge, notes, contacts, publication or assignment.
    Caller binds actor and active tenant to authenticated request context.
    """
    with _boundary():
        model, fields, entity, decision, capability = _lock_context(**context)
        current = _revision(context["entity_type"], context["entity_id"], context["sharing_domain_id"], entity)
        if (type(expected_revision) is not Revision or type(expected_revision.revision) is not int
                or type(expected_revision.write_stamp) is not UUID or expected_revision != current):
            raise CanonicalWriteError("STALE_REVISION")
        if type(values) is not dict or not values or set(values)-fields:
            raise CanonicalWriteError("INVALID_FIELDS")
        try:
            for name, value in values.items():
                field = model._meta.get_field(name)
                if value is not None and not isinstance(value, str):
                    raise ValidationError("Invalid value type")
                field.clean(value, None)
        except ValidationError:
            raise CanonicalWriteError("INVALID_VALUES") from None
        # Fetch only allowed patch values after successful fresh authorization.
        entity.update(model.objects.filter(pk=context["entity_id"]).values(*sorted(fields)).get())
        changes = {key: value for key, value in values.items() if value != entity[key]}
        if not changes:
            raise CanonicalWriteError("NO_CHANGES")
        _enabled()
        # The row and auth prerequisites remain locked. Recheck clock-dependent
        # current agreement at the UPDATE's own statement time (no grace).
        columns = sorted(changes)
        quote = connection.ops.quote_name
        assignments = ', '.join(quote(name)+'=%s' for name in columns)
        sql = f'''UPDATE {quote(model._meta.db_table)} SET {assignments}, updated_at=statement_timestamp()
            WHERE id=%s AND sharing_domain_id=%s AND canonical_write_stamp=%s
            AND %s = (SELECT id FROM crm_sharingagreement
                WHERE sharing_domain_id=%s AND effective_at <= statement_timestamp()
                ORDER BY effective_at DESC LIMIT 1)
            RETURNING canonical_write_stamp, statement_timestamp()'''
        params = [changes[k] for k in columns] + [context['entity_id'], context['sharing_domain_id'], current.write_stamp,
            decision.agreement_id, context['sharing_domain_id']]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
        if result is None:
            raise CanonicalWriteError("STALE_AUTHORIZATION_OR_REVISION")
        stamp, occurred_at = result
        CanonicalWriteAudit.objects.create(actor_id=context['user_id'], tenant_id=context['tenant_id'],
            assignment_id=context['assignment_id'], sharing_domain_id=context['sharing_domain_id'],
            agreement_id=decision.agreement_id, entity_type=context['entity_type'], entity_id=context['entity_id'],
            action=capability.value, previous_revision=current.revision, revision=current.revision+1,
            write_stamp=stamp, changed_fields=columns, occurred_at=occurred_at)
        return Revision(current.entity_type, current.entity_id, current.sharing_domain_id, current.revision+1, stamp)

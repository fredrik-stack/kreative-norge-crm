"""Explicit operator-only PK shadow. Never used by application read paths."""
import re
from collections import Counter

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q

from crm.models import (
    Organization, OrganizationTenantAssignment, Person, PersonTenantAssignment,
    SharingDomain, Tenant,
)
from crm.services.domain_backfill import database_identity

VERSION = 1
DOMAIN = {"id": 1, "slug": "musikkontoret", "name": "Musikkontoret"}
TENANTS = (
    (1, "musikkontoretnord", "Musikkontoret Nord"),
    (2, "musikkontoretmxst", "Musikkontoret MØST"),
    (3, "musikkontoretbrak", "Musikkontoret Brak"),
    (6, "musikkontoretoks", "Musikkontoret ØKS"),
    (7, "musikkontoretsorf", "Musikkontoret SØRF"),
    (8, "musikkontoretstar", "Musikkontoret STAR"),
    (9, "musikkontorettempo", "Musikkontoret Tempo"),
)
TENANT_IDS = tuple(row[0] for row in TENANTS)
EXIT_CODES = {"FULL_EQUAL": 0, "EXPLAINED_PARTIAL": 2, "FAILED": 3, "INCOMPLETE": 4}


class ShadowPrecondition(Exception):
    """Only internally defined reason codes may cross the report boundary."""


def incomplete(reason):
    return {"measurement_version": VERSION, "status": "INCOMPLETE",
            "completed_comparisons": 0, "reason_codes": [reason]}


def _require_scope():
    domains = list(SharingDomain.objects.filter(
        Q(pk=DOMAIN["id"]) | Q(slug=DOMAIN["slug"])
    ).values("id", "slug", "name"))
    tenants = list(Tenant.objects.filter(
        Q(pk__in=TENANT_IDS) | Q(sharing_domain_id=DOMAIN["id"])
    ).order_by("pk").values_list("id", "slug", "name", "sharing_domain_id"))
    if domains != [DOMAIN] or tenants != [(*row, DOMAIN["id"]) for row in TENANTS]:
        raise ShadowPrecondition("SCOPE_MISMATCH")


def _load_model(model, assignment, field):
    """Materialize structural scope before applying the valid assignment filter."""
    pool = model.objects.filter(Q(tenant_id__in=TENANT_IDS) | Q(sharing_domain_id=DOMAIN["id"]))
    profiles = list(pool.values("id", "tenant_id", "sharing_domain_id", "tenant__sharing_domain_id"))
    rows = list(assignment.objects.filter(
        Q(tenant_id__in=TENANT_IDS) | Q(**{f"{field}__in": pool.values("pk")})
    ).values("id", "tenant_id", "tenant__sharing_domain_id",
             f"{field}_id", f"{field}__tenant_id", f"{field}__sharing_domain_id"))
    normalized = [
        {"profile_id": row[f"{field}_id"], "tenant_id": row["tenant_id"],
         "tenant_domain": row["tenant__sharing_domain_id"],
         "profile_tenant": row[f"{field}__tenant_id"],
         "profile_domain": row[f"{field}__sharing_domain_id"]}
        for row in rows
    ]
    # Independent of legacy tenant and L: extra inbound assignments must remain visible.
    assignment_sets = {
        tenant: set(model.objects.filter(
            sharing_domain_id=DOMAIN["id"], tenant_assignments__tenant_id=tenant,
            tenant_assignments__tenant__sharing_domain_id=DOMAIN["id"],
        ).order_by().values_list("pk", flat=True).distinct())
        for tenant in TENANT_IDS
    }
    return profiles, normalized, assignment_sets


def _compare_model(label, profiles, assignments, assignment_sets):
    """Pure classification; no profile identifiers escape this function."""
    problems = Counter()
    by_profile = Counter(row["profile_id"] for row in assignments)
    for profile in profiles:
        domain = profile["sharing_domain_id"]
        if profile["tenant_id"] not in TENANT_IDS or profile["tenant__sharing_domain_id"] != DOMAIN["id"]:
            problems["PROFILE_TENANT_MISMATCH"] += 1
        if domain is not None and domain != DOMAIN["id"]:
            problems["PROFILE_DOMAIN_MISMATCH"] += 1
        expected = 0 if domain is None else 1
        if by_profile[profile["id"]] != expected:
            problems["ASSIGNMENT_CARDINALITY"] += 1
    for row in assignments:
        if (row["tenant_id"] not in TENANT_IDS or row["profile_tenant"] not in TENANT_IDS
                or row["tenant_id"] != row["profile_tenant"]):
            problems["ASSIGNMENT_TENANT_MISMATCH"] += 1
        if row["tenant_domain"] != DOMAIN["id"] or row["profile_domain"] != DOMAIN["id"]:
            problems["ASSIGNMENT_DOMAIN_MISMATCH"] += 1
    comparisons = []
    for tenant in TENANT_IDS:
        legacy_rows = [p for p in profiles if p["tenant_id"] == tenant]
        legacy = {p["id"] for p in legacy_rows}
        unbound = {p["id"] for p in legacy_rows if p["sharing_domain_id"] is None}
        bound = {p["id"] for p in legacy_rows if p["sharing_domain_id"] == DOMAIN["id"]}
        assigned = assignment_sets[tenant]
        missing, extra = legacy - assigned, assigned - legacy
        equal = legacy == assigned
        partial = missing == unbound and not extra and bound == assigned
        if not partial:
            problems["PK_SET_MISMATCH"] += 1
        comparisons.append({
            "model": label, "tenant_id": tenant, "legacy_count": len(legacy),
            "null_count": len(unbound), "bound_count": len(bound), "assignment_count": len(assigned),
            "legacy_only_count": len(missing), "assignment_only_count": len(extra),
            "bound_only_count": len(bound - assigned), "assignment_not_bound_count": len(assigned - bound),
            "full_equal": equal, "bound_equal": bound == assigned,
        })
    return comparisons, problems


def measure(*, environment, expected_database, code_baseline):
    """Caller verifies baseline against reviewed deployment before invoking.

    All database reads, including identity and scope, share this one snapshot.
    Exceptions are sanitized by the command; no raw exception is logged here.
    """
    if settings.SHARING_DOMAIN_SHADOW_ENABLED is not True:
        raise ShadowPrecondition("GATE_DISABLED")
    if environment not in {"local", "test", "staging"} or not re.fullmatch(r"[0-9a-f]{40}", code_baseline or ""):
        raise ShadowPrecondition("INVALID_CONTEXT")
    if connection.vendor != "postgresql":
        raise ShadowPrecondition("POSTGRESQL_REQUIRED")
    if connection.in_atomic_block or not connection.get_autocommit():
        raise ShadowPrecondition("OUTER_TRANSACTION")
    with transaction.atomic(durable=True):
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            cursor.execute("SET LOCAL lock_timeout = '2s'")
        identity = database_identity()
        if identity != expected_database:
            raise ShadowPrecondition("DATABASE_MISMATCH")
        _require_scope()
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_current_snapshot()::text, clock_timestamp(), current_setting('transaction_read_only'), current_setting('transaction_isolation')")
            snapshot, started, read_only, isolation = cursor.fetchone()
        if read_only != "on" or isolation != "repeatable read":
            raise ShadowPrecondition("SNAPSHOT_MISMATCH")
        comparisons, problems = [], Counter()
        for model, assignment, field in (
            (Organization, OrganizationTenantAssignment, "organization"),
            (Person, PersonTenantAssignment, "person"),
        ):
            rows, findings = _compare_model(model.__name__, *_load_model(model, assignment, field))
            comparisons.extend(rows)
            problems.update(findings)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_current_snapshot()::text, clock_timestamp(), current_setting('transaction_read_only'), current_setting('transaction_isolation')")
            end_snapshot, ended, read_only, isolation = cursor.fetchone()
        if (snapshot != end_snapshot or read_only != "on" or isolation != "repeatable read"
                or len(comparisons) != 14):
            raise ShadowPrecondition("SNAPSHOT_MISMATCH")
        status = "FAILED" if problems else (
            "EXPLAINED_PARTIAL" if any(r["null_count"] for r in comparisons) else "FULL_EQUAL"
        )
        report = {
            "measurement_version": VERSION, "status": status, "completed_comparisons": len(comparisons),
            "environment": environment, "database_identity": identity, "code_baseline": code_baseline,
            "domain": DOMAIN, "tenants": [{"id": i, "slug": s, "name": n} for i, s, n in TENANTS],
            "snapshot": snapshot, "started_at": started.isoformat(), "ended_at": ended.isoformat(),
            "transaction_read_only": True, "transaction_isolation": isolation,
            "comparisons": comparisons, "structural_deviations": dict(sorted(problems.items())),
            "reason_codes": sorted(problems),
        }
    return report

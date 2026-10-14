"""Explicit, operator-only legacy registration. No startup, signal or API caller."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import connection, models, transaction

from crm.domain_integrity import _legacy_assignment_scope
from crm.models import (
    LegacyDomainBackfillBatch, Organization, OrganizationTenantAssignment,
    Person, PersonTenantAssignment, SharingDomain, Tenant,
)
from crm.services.phone_backfill import write_phone_backfill_manifest, _validate_manifest_parent

PLAN_VERSION = 1
LOCK_TIMEOUT = "5s"
STRUCTURAL_TABLES = (
    "crm_sharingdomain", "crm_tenant", "crm_organization", "crm_person",
    "crm_organizationtenantassignment", "crm_persontenantassignment",
)
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def snapshot_tables():
    # Include auto-created tag/taxonomy join tables and existing image/import state.
    # Only the new operator receipt table is excluded from the preservation digest.
    return sorted({model._meta.db_table for model in apps.get_app_config("crm").get_models(include_auto_created=True)
                   if model is not LegacyDomainBackfillBatch})


def lock_tables():
    return sorted(set(snapshot_tables()) | {get_user_model()._meta.db_table})


def database_identity():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), system_identifier::text FROM pg_control_system()")
        name, cluster = cursor.fetchone()
    return f"postgresql:{cluster}:{name}"


def _require_outer_transaction():
    if connection.vendor != "postgresql" or connection.in_atomic_block:
        raise CommandError("Use PostgreSQL and call outside an existing transaction.")


def _mapping(mapping):
    if not isinstance(mapping, dict) or set(mapping) != {"domain", "tenants"}:
        raise CommandError("Mapping needs exactly domain and tenants.")
    domain, tenants = mapping["domain"], mapping["tenants"]
    if not isinstance(domain, dict) or set(domain) != {"id", "slug", "name"}:
        raise CommandError("Domain identity needs explicit id (null only for creation), slug and name.")
    if domain["id"] is not None and (type(domain["id"]) is not int or domain["id"] < 1):
        raise CommandError("Invalid domain ID.")
    if not isinstance(domain["slug"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,50}", domain["slug"]):
        raise CommandError("Invalid explicit domain slug.")
    if not isinstance(domain["name"], str) or not domain["name"].strip() or len(domain["name"]) > 255:
        raise CommandError("Invalid explicit domain name.")
    if not isinstance(tenants, list) or not tenants:
        raise CommandError("An explicit nonempty tenant scope is required.")
    for tenant in tenants:
        if not isinstance(tenant, dict) or set(tenant) != {"id", "slug", "name"}:
            raise CommandError("Each tenant needs id, exact slug and exact name.")
        if type(tenant["id"]) is not int or tenant["id"] < 1 or not all(isinstance(tenant[f], str) and tenant[f] for f in ("slug", "name")):
            raise CommandError("Invalid tenant identity.")
    if len({t["id"] for t in tenants}) != len(tenants) or len({t["slug"] for t in tenants}) != len(tenants):
        raise CommandError("Duplicate tenant scope.")
    return {"domain": dict(domain), "tenants": sorted(tenants, key=lambda t: t["id"])}


def _snapshot():
    preserved, structure = {}, {}
    for table in snapshot_tables():
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT row_to_json(t) FROM "{table}" t ORDER BY id')
            rows = [row[0] for row in cursor.fetchall()]
        if table in STRUCTURAL_TABLES:
            structure[table] = {"count": len(rows), "sha256": _hash(rows)}
        if table in ("crm_sharingdomain", "crm_organizationtenantassignment", "crm_persontenantassignment"):
            continue
        if table in ("crm_tenant", "crm_organization", "crm_person"):
            rows = [{k: v for k, v in row.items() if k != "sharing_domain_id"} for row in rows]
        preserved[table] = {"count": len(rows), "sha256": _hash(rows)}
    return {"preserved": preserved, "structure": structure}


def _plan(mapping):
    target = mapping["domain"]
    identity_query = models.Q(slug=target["slug"]) | models.Q(pk=target["id"])
    if target["id"] is None:
        identity_query |= models.Q(name=target["name"])
    domains = list(SharingDomain.objects.filter(identity_query).values("id", "name", "slug"))
    if target["id"] is None:
        if domains:
            raise CommandError("Target domain already exists; approve its complete identity first.")
        domain_id = None
    elif domains != [target]:
        raise CommandError("Existing target domain identity does not match the approved mapping.")
    else:
        domain_id = target["id"]
    ids = [row["id"] for row in mapping["tenants"]]
    actual = list(Tenant.objects.filter(pk__in=ids).order_by("id").values("id", "slug", "name"))
    if actual != mapping["tenants"]:
        raise CommandError("Tenant identity mismatch; no guessing or renaming.")
    tenant_rows = list(Tenant.objects.filter(pk__in=ids).order_by("id").values("id", "sharing_domain_id"))
    for tenant in tenant_rows:
        if tenant["sharing_domain_id"] is not None and tenant["sharing_domain_id"] != domain_id:
            raise CommandError("Conflicting tenant domain.")
    tenant_domains = {row["id"]: row["sharing_domain_id"] for row in tenant_rows}
    profiles = {}
    summary = {str(t): {"organizations": 0, "persons": 0} for t in ids}
    for model, assignment, field, label in (
        (Organization, OrganizationTenantAssignment, "organization_id", "organizations"),
        (Person, PersonTenantAssignment, "person_id", "persons"),
    ):
        rows = list(model.objects.filter(tenant_id__in=ids).order_by("id").values("id", "tenant_id", "sharing_domain_id"))
        if assignment.objects.filter(models.Q(tenant_id__in=ids) | models.Q(**{f"{field}__in": [r["id"] for r in rows]})).exclude(**{f"{field[:-3]}__tenant_id": models.F("tenant_id")}).exists():
            raise CommandError("Assignment touches the scope from a different legacy tenant.")
        assignments = list(assignment.objects.filter(**{f"{field}__in": [r["id"] for r in rows]}).order_by("id").values("id", field, "tenant_id"))
        by_entity = {}
        for a in assignments:
            by_entity.setdefault(a[field], []).append(a)
        for row in rows:
            summary[str(row["tenant_id"])][label] += 1
            existing = by_entity.get(row["id"], [])
            if row["sharing_domain_id"] is not None and tenant_domains[row["tenant_id"]] != row["sharing_domain_id"]:
                raise CommandError("Profile binding conflicts with its legacy tenant.")
            if row["sharing_domain_id"] is not None and row["sharing_domain_id"] != domain_id:
                raise CommandError("Conflicting profile domain.")
            if len(existing) > 1 or any(a["tenant_id"] != row["tenant_id"] for a in existing):
                raise CommandError("Unexpected assignment; no automatic reassignment/removal.")
            if existing and (domain_id is None or row["sharing_domain_id"] != domain_id):
                raise CommandError("Assignment has an inconsistent domain.")
            row["assignment_id"] = existing[0]["id"] if existing else None
        profiles[label] = rows
    # Include inbound relations, not only rows whose own tenant is selected.
    with connection.cursor() as cursor:
        cursor.execute("""SELECT count(*) FROM crm_organizationperson r
            JOIN crm_organization o ON o.id=r.organization_id JOIN crm_person p ON p.id=r.person_id
            WHERE (r.tenant_id=ANY(%s) OR o.tenant_id=ANY(%s) OR p.tenant_id=ANY(%s))
              AND (r.tenant_id<>o.tenant_id OR r.tenant_id<>p.tenant_id)""", [ids, ids, ids])
        relation_errors = cursor.fetchone()[0]
        cursor.execute("""SELECT count(*) FROM crm_personcontact c JOIN crm_person p ON p.id=c.person_id
            WHERE (c.tenant_id=ANY(%s) OR p.tenant_id=ANY(%s)) AND c.tenant_id<>p.tenant_id""", [ids, ids])
        contact_errors = cursor.fetchone()[0]
        tag_errors = 0
        for table, entity, fk in (("crm_organization_tags", "crm_organization", "organization_id"), ("crm_person_tags", "crm_person", "person_id")):
            cursor.execute(f'''SELECT count(*) FROM {table} r JOIN {entity} e ON e.id=r.{fk}
                JOIN crm_tag t ON t.id=r.tag_id WHERE (e.tenant_id=ANY(%s) OR t.tenant_id=ANY(%s))
                AND e.tenant_id<>t.tenant_id''', [ids, ids])
            tag_errors += cursor.fetchone()[0]
    if relation_errors or contact_errors or tag_errors:
        raise CommandError("Relationship/contact/tag scope mismatch; a separate review is required.")
    snapshot = _snapshot()
    plan = {"version": PLAN_VERSION, "mapping": mapping, "tenants": tenant_rows,
            "profiles": profiles, "summary": summary, "snapshot": snapshot}
    plan["digest"] = _hash(plan)
    plan["changes"] = int(domain_id is None) + sum(t["sharing_domain_id"] is None for t in tenant_rows) + sum(
        int(r["sharing_domain_id"] is None) + int(r["assignment_id"] is None) for rows in profiles.values() for r in rows)
    return plan


def dry_run(mapping):
    _require_outer_transaction()
    mapping = _mapping(mapping)
    with transaction.atomic(durable=True):
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        identity = database_identity()
        plan = _plan(mapping)
    return {"mode": "DRY_RUN", "database_identity": identity, "plan": plan, "writes": 0}


def _operator(operator_id):
    if type(operator_id) is not int or not get_user_model().objects.filter(pk=operator_id, is_active=True, is_staff=True, is_superuser=True).exists():
        raise CommandError("An explicit active staff/platform-superuser operator is required.")


def _environment(environment, expected_database):
    if not isinstance(environment, str) or not IDENTIFIER.fullmatch(environment):
        raise CommandError("Explicit environment identity is required.")
    if database_identity() != expected_database:
        raise CommandError("Database identity differs from the approved dry-run.")


def read_batch(*, environment, expected_database, batch_id, operator_id):
    _require_outer_transaction()
    with transaction.atomic(durable=True):
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        _environment(environment, expected_database)
        _operator(operator_id)
        try:
            batch = LegacyDomainBackfillBatch.objects.get(environment=environment, database_identity=expected_database, batch_id=batch_id)
        except LegacyDomainBackfillBatch.DoesNotExist as error:
            raise CommandError("No batch registered in this environment/database.") from error
        result = {"mode": "READ_BACK", "batch_id": batch.batch_id, "state": batch.state,
                  "manifest_path": batch.manifest_path, "receipt": batch.receipt}
        if batch.state == "COMMITTED_VERIFIED":
            result["current_state_matches_receipt"] = _snapshot() == batch.receipt["after"]
        return result


def apply_backfill(*, mapping, environment, expected_database, expected_digest,
                   batch_id, operator_id, code_baseline, manifest_path):
    _require_outer_transaction()
    mapping = _mapping(mapping)
    _environment(environment, expected_database)
    _operator(operator_id)
    if not isinstance(batch_id, str) or not IDENTIFIER.fullmatch(batch_id):
        raise CommandError("An explicit valid batch ID is required.")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest or "") or not re.fullmatch(r"[0-9a-f]{40}", code_baseline or ""):
        raise CommandError("Expected plan digest and code baseline are required.")
    if not manifest_path or not Path(manifest_path).is_absolute():
        raise CommandError("Apply requires an absolute private no-clobber manifest path.")
    _validate_manifest_parent(Path(manifest_path))
    request = {"mapping": mapping, "environment": environment, "database_identity": expected_database,
               "expected_digest": expected_digest, "operator_id": operator_id, "code_baseline": code_baseline}
    request_digest = _hash(request)
    batch, created = LegacyDomainBackfillBatch.objects.get_or_create(
        environment=environment, database_identity=expected_database, batch_id=batch_id,
        defaults={"request_digest": request_digest, "plan_digest": expected_digest,
                  "operator_id": operator_id, "code_baseline": code_baseline,
                  "manifest_path": str(manifest_path), "receipt": {"request": request}},
    )
    if not created:
        if batch.request_digest != request_digest or batch.manifest_path != str(manifest_path):
            raise CommandError("Batch already registered; another plan/operator/path cannot reuse it.")
        return read_batch(environment=environment, expected_database=expected_database, batch_id=batch_id, operator_id=operator_id)
    try:
        with transaction.atomic(durable=True):
            with connection.cursor() as cursor:
                # READ COMMITTED obtains a NEW snapshot AFTER waiting for all locks.
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                cursor.execute("SET LOCAL lock_timeout = %s", [LOCK_TIMEOUT])
                for table in lock_tables():
                    cursor.execute(f'LOCK TABLE "{table}" IN SHARE ROW EXCLUSIVE MODE')
            _environment(environment, expected_database)
            _operator(operator_id)
            plan = _plan(mapping)
            if plan["digest"] != expected_digest:
                raise CommandError("Stale approved plan; no data changes were committed.")
            prepared = {"state": "PREPARED", "batch_id": batch_id, "request": request,
                        "request_digest": request_digest, "plan": plan,
                        "target": "exactly one assignment to each selected profile's legacy tenant"}
            write_phone_backfill_manifest(manifest_path, prepared)
            domain_id = mapping["domain"]["id"]
            if domain_id is None:
                domain = SharingDomain.objects.create(name=mapping["domain"]["name"], slug=mapping["domain"]["slug"])
                domain_id = domain.pk
            changes = []
            for row in plan["tenants"]:
                if row["sharing_domain_id"] is None:
                    models.QuerySet.update(Tenant.objects.filter(pk=row["id"]), sharing_domain_id=domain_id)
                    changes.append({"model": "tenant", "id": row["id"], "field": "sharing_domain_id", "before": None, "after": domain_id})
            allowed = []
            inserts = []
            for model, assignment, field, label in (
                (Organization, OrganizationTenantAssignment, "organization_id", "organizations"),
                (Person, PersonTenantAssignment, "person_id", "persons"),
            ):
                for row in plan["profiles"][label]:
                    if row["sharing_domain_id"] is None:
                        models.QuerySet.update(model.objects.filter(pk=row["id"]), sharing_domain_id=domain_id)
                        changes.append({"model": model._meta.model_name, "id": row["id"], "field": "sharing_domain_id", "before": None, "after": domain_id})
                    if row["assignment_id"] is None:
                        allowed.append((assignment._meta.label_lower, row["id"], row["tenant_id"]))
                        inserts.append((assignment, assignment(**{field: row["id"], "tenant_id": row["tenant_id"]})))
            with _legacy_assignment_scope(allowed):
                for assignment, obj in inserts:
                    assignment.objects._insert_for_backfill([obj])
                    changes.append({"model": assignment._meta.model_name, "id": obj.pk,
                                    "profile_id": obj.organization_id if hasattr(obj, "organization_id") else obj.person_id,
                                    "tenant_id": obj.tenant_id})
            target_mapping = {**mapping, "domain": {**mapping["domain"], "id": domain_id}}
            verified = _plan(target_mapping)
            if verified["changes"] != 0 or plan["snapshot"]["preserved"] != verified["snapshot"]["preserved"]:
                raise CommandError("Postcondition/preservation mismatch; transaction rolled back.")
            receipt = {"request": request, "plan_digest": expected_digest, "mapping": target_mapping,
                       "summary": plan["summary"], "before": plan["snapshot"], "after": verified["snapshot"],
                       "changes": changes, "domain_created": mapping["domain"]["id"] is None,
                       "lock_mode": "SHARE ROW EXCLUSIVE", "lock_order": lock_tables(), "lock_timeout": LOCK_TIMEOUT}
            # Receipt and semantic data COMMIT in the SAME DB transaction.
            LegacyDomainBackfillBatch.objects.filter(pk=batch.pk).update(state="COMMITTED_VERIFIED", receipt=receipt)
        # Filesystem acknowledgement can fail AFTER successful DB commit.
        write_phone_backfill_manifest(str(manifest_path) + ".verified.json", {"state": "COMMITTED_VERIFIED", "batch_id": batch_id, "receipt": receipt})
    except Exception as error:
        # Never infer rollback from a failed/lost COMMIT acknowledgement. The DB
        # marker plus read-back resolves it; a registered batch never auto-retries.
        reason = str(error) if isinstance(error, CommandError) else type(error).__name__
        raise CommandError(f"Batch {batch_id} is registered ({reason}); use read-back before any next action.") from error
    return {"mode": "APPLY", "batch_id": batch_id, "state": "COMMITTED_VERIFIED",
            "changes_applied": len(changes) + int(receipt["domain_created"]), "receipt": receipt}

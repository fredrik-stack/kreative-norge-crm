"""Explicit insert-only legacy copy. No startup, signal, API or user authority."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import connection, models, transaction

from crm.models import (
    Organization, OrganizationNoteOverlay, OrganizationTenantAssignment,
    Person, PersonNoteOverlay, PersonTenantAssignment, SharingDomain, Tenant,
    TenantNoteCopyBatch,
)
from crm.note_overlays import require_overlay_storage
from crm.services.domain_backfill import (
    IDENTIFIER, _environment, _hash, _mapping, _operator,
    _require_outer_transaction, database_identity,
)
from crm.services.phone_backfill import _validate_manifest_parent, write_phone_backfill_manifest


PLAN_VERSION = 1
LOCK_TIMEOUT = "5s"
STATEMENT_TIMEOUT = "30s"
CASES = (
    (Organization, OrganizationTenantAssignment, OrganizationNoteOverlay, "organization_id"),
    (Person, PersonTenantAssignment, PersonNoteOverlay, "person_id"),
)
OVERLAY_TABLES = frozenset(case[2]._meta.db_table for case in CASES)


def _require_transaction_context():
    _require_outer_transaction()
    if not connection.get_autocommit():
        raise CommandError("NOTE_COPY_AUTOCOMMIT_REQUIRED")


def _context(*, environment, expected_database, operator_id, code_baseline):
    _environment(environment, expected_database)
    _operator(operator_id)
    if not re.fullmatch(r"[0-9a-f]{40}", code_baseline or ""):
        raise CommandError("NOTE_COPY_CODE_BASELINE")
    return dict(environment=environment, database_identity=expected_database,
                operator_id=operator_id, code_baseline=code_baseline)


def _scope(mapping):
    mapping = _mapping(mapping)
    domain = mapping["domain"]
    if domain["id"] is None or list(SharingDomain.objects.filter(
        models.Q(pk=domain["id"]) | models.Q(slug=domain["slug"])
    ).values("id", "slug", "name")) != [domain]:
        raise CommandError("NOTE_COPY_DOMAIN_IDENTITY")
    tenants = list(Tenant.objects.filter(pk__in=[t["id"] for t in mapping["tenants"]])
                   .order_by("id").values("id", "slug", "name", "sharing_domain_id"))
    if [{k: t[k] for k in ("id", "slug", "name")} for t in tenants] != mapping["tenants"]:
        raise CommandError("NOTE_COPY_TENANT_IDENTITY")
    if any(t["sharing_domain_id"] != domain["id"] for t in tenants):
        raise CommandError("NOTE_COPY_TENANT_DOMAIN")
    return mapping


def _note(value):
    # Typed fingerprints stay private, including hashes of short/empty notes.
    if value is None:
        return {"kind": "null"}
    raw = value.encode("utf-8")
    return {"kind": "empty" if value == "" else "whitespace" if value.isspace() else "text",
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def snapshot_tables():
    return sorted({m._meta.db_table for m in apps.get_app_config("crm").get_models(include_auto_created=True)
                   if m is not TenantNoteCopyBatch})


def lock_tables():
    return sorted(set(snapshot_tables()) | {
        get_user_model()._meta.db_table, TenantNoteCopyBatch._meta.db_table,
    })


def _snapshot():
    result = {}
    for table in snapshot_tables():
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT row_to_json(t) FROM "{table}" t ORDER BY id')
            rows = [r[0] for r in cursor.fetchall()]
        result[table] = {"count": len(rows), "sha256": _hash(rows)}
    return result


def _targets():
    return {overlay._meta.model_name: [
        {"id": row["id"], "assignment_id": row["assignment_id"], "note": _note(row["note"])}
        for row in overlay.objects.order_by("id").values("id", "assignment_id", "note")
    ] for _, _, overlay, _ in CASES}


def _plan(mapping, context):
    mapping = _scope(mapping)
    ids = [t["id"] for t in mapping["tenants"]]
    domain = mapping["domain"]["id"]
    records, candidates, summary, blockers = {}, {}, [], []
    for model, assignment, overlay, field in CASES:
        label = model._meta.model_name
        rows = list(model.objects.filter(tenant_id__in=ids).order_by("id")
                    .values("id", "tenant_id", "sharing_domain_id", "note"))
        # LEFT JOIN is intentional: corrupt/restored orphan endpoints must be
        # blockers, never disappear through the ORM's non-null FK INNER JOINs.
        columns = ("id", field, "tenant_id", "tenant__sharing_domain_id",
                   field[:-3] + "__tenant_id", field[:-3] + "__sharing_domain_id")
        with connection.cursor() as cursor:
            cursor.execute(f'''SELECT a.id,a.{field},a.tenant_id,t.sharing_domain_id,
                    p.tenant_id,p.sharing_domain_id
                FROM "{assignment._meta.db_table}" a
                LEFT JOIN crm_tenant t ON t.id=a.tenant_id
                LEFT JOIN "{model._meta.db_table}" p ON p.id=a.{field}
                WHERE a.tenant_id=ANY(%s) OR a.{field}=ANY(%s) ORDER BY a.id''',
                [ids, [r["id"] for r in rows]])
            assigned = [dict(zip(columns, row)) for row in cursor.fetchall()]
        by_profile = {}
        for a in assigned:
            by_profile.setdefault(a[field], []).append(a)
            if (a["tenant__sharing_domain_id"] != domain
                    or a[field[:-3] + "__sharing_domain_id"] != domain
                    or a["tenant_id"] != a[field[:-3] + "__tenant_id"]):
                blockers.append({"model": label, "assignment_id": a["id"], "reason": "ASSIGNMENT_SCOPE"})
        existing = set(overlay.objects.filter(assignment_id__in=[a["id"] for a in assigned])
                       .values_list("assignment_id", flat=True))
        records[label], candidates[label] = [], []
        for tenant_id in ids:
            counts = dict(profiles=0, null=0, empty=0, whitespace=0, text=0,
                          deferred_unbound=0, candidates=0)
            for row in (r for r in rows if r["tenant_id"] == tenant_id):
                state = {**row, "note": _note(row["note"])}
                links = by_profile.get(row["id"], [])
                state["assignments"] = links
                records[label].append(state)
                counts["profiles"] += 1
                counts[state["note"]["kind"]] += 1
                if any(a["id"] in existing for a in links):
                    blockers.append({"model": label, "profile_id": row["id"], "reason": "OVERLAY_EXISTS"})
                if row["sharing_domain_id"] is None and not links:
                    counts["deferred_unbound"] += 1
                    continue
                if (row["sharing_domain_id"] != domain or len(links) != 1
                        or links[0]["tenant_id"] != tenant_id
                        or links[0]["tenant__sharing_domain_id"] != domain):
                    blockers.append({"model": label, "profile_id": row["id"], "reason": "OWN_ASSIGNMENT_REQUIRED"})
                    continue
                if row["note"] is not None:
                    candidates[label].append({"profile_id": row["id"], "assignment_id": links[0]["id"],
                                              "note": state["note"]})
                    counts["candidates"] += 1
            summary.append({"model": label, "tenant_id": tenant_id, **counts})
    result = {"version": PLAN_VERSION, "context": context, "mapping": mapping,
              "policy": "NON_NULL_EXACT_INSERT_OWN_LEGACY_ASSIGNMENT",
              "sources": records, "candidates": candidates, "summary": summary,
              "blockers": blockers, "targets": _targets(), "snapshot": _snapshot()}
    result["digest"] = _hash(result)
    return result


def _timeouts(cursor):
    cursor.execute("SET LOCAL lock_timeout = %s", [LOCK_TIMEOUT])
    cursor.execute("SET LOCAL statement_timeout = %s", [STATEMENT_TIMEOUT])


def dry_run(mapping, **options):
    _require_transaction_context()
    with transaction.atomic(durable=True):
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            _timeouts(cursor)
        context = _context(**options)
        plan = _plan(mapping, context)
    return {"mode": "DRY_RUN", "state": "BLOCKED" if plan["blockers"] else "READY",
            "writes": 0, "plan": plan}


def read_batch(*, environment, expected_database, batch_id, operator_id):
    _require_transaction_context()
    with transaction.atomic(durable=True):
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            _timeouts(cursor)
        _environment(environment, expected_database)
        _operator(operator_id)
        try:
            batch = TenantNoteCopyBatch.objects.get(environment=environment,
                database_identity=expected_database, batch_id=batch_id)
        except TenantNoteCopyBatch.DoesNotExist:
            raise CommandError("NOTE_COPY_BATCH_UNKNOWN") from None
        result = {"mode": "READ_BACK", "batch_id": batch_id, "state": batch.state, "receipt": batch.receipt}
        if batch.state == "COMMITTED_VERIFIED":
            current = _snapshot()
            receipt = batch.receipt
            source_tables = [m._meta.db_table for m, _, _, _ in CASES] + [
                Tenant._meta.db_table, SharingDomain._meta.db_table,
                OrganizationTenantAssignment._meta.db_table, PersonTenantAssignment._meta.db_table,
            ]
            result["source_matches_plan"] = all(current[t] == receipt["before"][t] for t in source_tables)
            result["targets_match_receipt"] = all(current[t] == receipt["after"][t] for t in OVERLAY_TABLES)
            result["current_state_matches_receipt"] = current == receipt["after"]
        return result


def apply_copy(*, mapping, environment, expected_database, operator_id, code_baseline,
               expected_digest, batch_id, manifest_path):
    _require_transaction_context()
    context = _context(environment=environment, expected_database=expected_database,
                       operator_id=operator_id, code_baseline=code_baseline)
    mapping = _mapping(mapping)
    if not isinstance(batch_id, str) or not IDENTIFIER.fullmatch(batch_id):
        raise CommandError("NOTE_COPY_BATCH_ID")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest or ""):
        raise CommandError("NOTE_COPY_PLAN_DIGEST")
    if not manifest_path or not Path(manifest_path).is_absolute():
        raise CommandError("NOTE_COPY_MANIFEST_PATH")
    manifest_path = str(_validate_manifest_parent(Path(manifest_path)))
    request = {"mapping": mapping, "context": context, "expected_digest": expected_digest}
    request_digest = _hash(request)
    key = dict(environment=environment, database_identity=expected_database, batch_id=batch_id)

    def replay(batch):
        if batch.request_digest != request_digest or batch.manifest_path != manifest_path:
            raise CommandError("NOTE_COPY_BATCH_REQUEST_CONFLICT")
        return read_batch(environment=environment, expected_database=expected_database,
                          batch_id=batch_id, operator_id=operator_id)

    existing = TenantNoteCopyBatch.objects.filter(**key).first()
    if existing is not None:
        return replay(existing)
    require_overlay_storage()  # Existing storage gate; only this operator process may enable it.
    batch, created = TenantNoteCopyBatch.objects.get_or_create(**key, defaults={
        "request_digest": request_digest, "plan_digest": expected_digest,
        "operator_id": operator_id, "code_baseline": code_baseline,
        "manifest_path": manifest_path, "receipt": {"request": request},
    })
    if not created:
        return replay(batch)
    try:
        with transaction.atomic(durable=True):
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                _timeouts(cursor)
                for table in lock_tables():
                    cursor.execute(f'LOCK TABLE "{table}" IN SHARE ROW EXCLUSIVE MODE')
            _context(environment=environment, expected_database=expected_database,
                     operator_id=operator_id, code_baseline=code_baseline)
            plan = _plan(mapping, context)
            if plan["digest"] != expected_digest:
                raise CommandError("NOTE_COPY_STALE_PLAN")
            if plan["blockers"]:
                raise CommandError("NOTE_COPY_BLOCKED_PLAN")
            write_phone_backfill_manifest(manifest_path, {"state": "PREPARED", "request": request, "plan": plan})
            expected_targets = {label: list(rows) for label, rows in plan["targets"].items()}
            changes = []
            for model, _, overlay, _ in CASES:
                for candidate in plan["candidates"][model._meta.model_name]:
                    value = model.objects.values_list("note", flat=True).get(pk=candidate["profile_id"])
                    if value is None or _note(value) != candidate["note"]:
                        raise CommandError("NOTE_COPY_SOURCE_MISMATCH")
                    row = overlay.objects.create(assignment_id=candidate["assignment_id"], note=value)
                    expected_targets[overlay._meta.model_name].append(
                        {"id": row.pk, "assignment_id": row.assignment_id, "note": candidate["note"]})
                    changes.append({"model": overlay._meta.model_name, "id": row.pk,
                                    "assignment_id": row.assignment_id, "profile_id": candidate["profile_id"]})
            after = _snapshot()
            if (any(after[t] != plan["snapshot"][t] for t in after if t not in OVERLAY_TABLES)
                    or _targets() != expected_targets):
                raise CommandError("NOTE_COPY_POSTCONDITION")
            receipt = {"request": request, "plan_digest": expected_digest, "summary": plan["summary"],
                       "before": plan["snapshot"], "after": after, "changes": changes,
                       "lock_mode": "SHARE ROW EXCLUSIVE", "lock_order": lock_tables(),
                       "lock_timeout": LOCK_TIMEOUT, "statement_timeout": STATEMENT_TIMEOUT}
            TenantNoteCopyBatch.objects.filter(pk=batch.pk).update(state="COMMITTED_VERIFIED", receipt=receipt)
        write_phone_backfill_manifest(manifest_path + ".verified.json",
            {"state": "COMMITTED_VERIFIED", "batch_id": batch_id, "receipt": receipt})
    except Exception as error:
        # Do not expose DB errors (which may contain note values), or infer rollback
        # from a lost acknowledgement. PREPARED is never an automatic retry grant.
        raise CommandError("NOTE_COPY_REGISTERED_USE_READ_BACK") from error
    return {"mode": "APPLY", "batch_id": batch_id, "state": "COMMITTED_VERIFIED", "receipt": receipt}


def public_report(report):
    """CLI allowlist: no row identities, per-profile hashes, raw notes or errors."""
    result = {k: report[k] for k in ("mode", "state", "writes", "batch_id", "source_matches_plan",
              "targets_match_receipt", "current_state_matches_receipt") if k in report}
    if "plan" in report:
        plan = report["plan"]
        result.update(plan_digest=plan["digest"], summary=plan["summary"],
                      blockers=len(plan["blockers"]), blocker_reasons=sorted({b["reason"] for b in plan["blockers"]}))
    elif report["state"] == "COMMITTED_VERIFIED":
        result.update(summary=report["receipt"]["summary"],
                      copied=len(report["receipt"]["changes"]))
    return result

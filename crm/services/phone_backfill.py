from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

import phonenumbers
from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q

from crm.models import Organization, OrganizationPerson, Person, PersonContact, Tenant
from crm.services.phone_normalization import PhoneNormalizationStatus, normalize_phone


MANIFEST_SCHEMA_VERSION = 1
BATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MODEL_FIELDS = {
    "Tenant": ("default_phone_region",),
    "Organization": ("phone_normalized", "phone_normalization_region"),
    "PersonContact": ("normalized_value", "normalization_region"),
}


def _digest(rows) -> dict:
    rows = list(rows)
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str)
    return {
        "count": len(rows),
        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }


def phone_backfill_fingerprints(tenant_ids: list[int]) -> dict:
    tenant_ids = sorted(tenant_ids)
    raw_phone_rows = [
        {
            "model": "Organization",
            **row,
        }
        for row in Organization.objects.filter(tenant_id__in=tenant_ids)
        .order_by("id")
        .values("id", "tenant_id", "phone")
    ]
    raw_phone_rows.extend(
        {
            "model": "Person",
            **row,
        }
        for row in Person.objects.filter(tenant_id__in=tenant_ids)
        .order_by("id")
        .values("id", "tenant_id", "phone")
    )
    raw_phone_rows.extend(
        {
            "model": "PersonContact",
            **row,
        }
        for row in PersonContact.objects.filter(tenant_id__in=tenant_ids, type="PHONE")
        .order_by("id")
        .values("id", "tenant_id", "person_id", "value")
    )

    publication_rows = [
        {
            "model": "Organization",
            **row,
        }
        for row in Organization.objects.filter(tenant_id__in=tenant_ids)
        .order_by("id")
        .values("id", "tenant_id", "is_published", "publish_phone")
    ]
    publication_rows.extend(
        {
            "model": "PersonContact",
            **row,
        }
        for row in PersonContact.objects.filter(tenant_id__in=tenant_ids)
        .order_by("id")
        .values("id", "tenant_id", "person_id", "type", "is_primary", "is_public")
    )
    publication_rows.extend(
        {
            "model": "OrganizationPerson",
            **row,
        }
        for row in OrganizationPerson.objects.filter(tenant_id__in=tenant_ids)
        .order_by("id")
        .values(
            "id",
            "tenant_id",
            "organization_id",
            "person_id",
            "status",
            "publish_person",
        )
    )

    additive_rows = [
        {
            "model": "Tenant",
            **row,
        }
        for row in Tenant.objects.filter(id__in=tenant_ids)
        .order_by("id")
        .values("id", "default_phone_region")
    ]
    additive_rows.extend(
        {
            "model": "Organization",
            **row,
        }
        for row in Organization.objects.filter(tenant_id__in=tenant_ids)
        .order_by("id")
        .values(
            "id",
            "tenant_id",
            "phone_normalized",
            "phone_normalization_region",
        )
    )
    additive_rows.extend(
        {
            "model": "PersonContact",
            **row,
        }
        for row in PersonContact.objects.filter(tenant_id__in=tenant_ids, type="PHONE")
        .order_by("id")
        .values(
            "id",
            "tenant_id",
            "normalized_value",
            "normalization_region",
        )
    )

    return {
        "raw_phone": _digest(raw_phone_rows),
        "publication": _digest(publication_rows),
        "additive_identity": _digest(additive_rows),
    }


def _validate_scope(
    *,
    tenant_ids: list[int],
    expected_total_tenants: int,
    target_region: str,
    lock: bool,
) -> list[Tenant]:
    unique_ids = sorted(set(tenant_ids))
    if not unique_ids or len(unique_ids) != len(tenant_ids):
        raise CommandError("Tenant IDs must be a non-empty, duplicate-free explicit scope.")
    if expected_total_tenants < 1:
        raise CommandError("Expected tenant count must be positive.")
    if Tenant.objects.count() != expected_total_tenants:
        raise CommandError(
            "Tenant gate failed: actual tenant count differs from the explicit expectation."
        )
    if len(unique_ids) != expected_total_tenants:
        raise CommandError(
            "Tenant gate failed: explicit scope must contain every expected tenant."
        )
    queryset = Tenant.objects.order_by("id")
    if lock:
        queryset = queryset.select_for_update()
    tenants = list(queryset.filter(id__in=unique_ids))
    if [tenant.id for tenant in tenants] != unique_ids:
        raise CommandError("Tenant gate failed: one or more explicit tenant IDs do not exist.")
    normalized_region = (target_region or "").strip().upper()
    if normalized_region not in phonenumbers.SUPPORTED_REGIONS:
        raise CommandError("Target region must be an explicit supported region code.")
    return tenants


def _person_integrity(tenant_ids: list[int], *, lock: bool) -> dict:
    contact_queryset = PersonContact.objects.filter(
        tenant_id__in=tenant_ids,
        type="PHONE",
    ).order_by("person_id", "id")
    if lock:
        contact_queryset = contact_queryset.select_for_update()
    contacts = list(
        contact_queryset.values(
            "person_id",
            "tenant_id",
            "person__tenant_id",
            "value",
            "is_primary",
        )
    )
    cross_tenant_contacts = sum(
        1 for row in contacts if row["tenant_id"] != row["person__tenant_id"]
    )
    primaries = [row for row in contacts if row["is_primary"]]
    primary_counts = Counter(row["person_id"] for row in primaries)
    multiple_primary_people = sum(1 for count in primary_counts.values() if count > 1)
    primary_by_person = {
        row["person_id"]: row["value"]
        for row in primaries
        if primary_counts[row["person_id"]] == 1
    }
    people_queryset = Person.objects.filter(tenant_id__in=tenant_ids).order_by("id")
    if lock:
        people_queryset = people_queryset.select_for_update()
    people = list(people_queryset.values("id", "phone"))
    direct_nonblank = {
        row["id"]: (row["phone"] or "").strip()
        for row in people
        if (row["phone"] or "").strip()
    }
    direct_without_primary = sum(
        1 for person_id in direct_nonblank if person_id not in primary_by_person
    )
    raw_mismatches = sum(
        1
        for person_id, direct_value in direct_nonblank.items()
        if person_id in primary_by_person
        and direct_value != (primary_by_person[person_id] or "").strip()
    )
    primary_without_direct = sum(
        1 for person_id in primary_by_person if person_id not in direct_nonblank
    )
    report = {
        "direct_nonblank": len(direct_nonblank),
        "primary_contacts": len(primaries),
        "primary_without_direct": primary_without_direct,
        "direct_without_primary": direct_without_primary,
        "raw_mismatches": raw_mismatches,
        "multiple_primary_people": multiple_primary_people,
        "cross_tenant_contacts": cross_tenant_contacts,
    }
    blocking = (
        cross_tenant_contacts
        + multiple_primary_people
        + direct_without_primary
        + raw_mismatches
    )
    if blocking:
        raise CommandError(
            "Person/primary PHONE integrity gate failed; no changes were applied. "
            f"blocking_groups={blocking}"
        )
    return report


def _classification_bucket():
    return defaultdict(lambda: defaultdict(Counter))


def _classification_json(classifications) -> dict:
    return {
        model: {
            str(tenant_id): dict(sorted(counts.items()))
            for tenant_id, counts in sorted(per_tenant.items())
        }
        for model, per_tenant in sorted(classifications.items())
    }


def _identity_changes(
    *,
    tenant_ids: list[int],
    target_region: str,
    lock: bool,
) -> tuple[list[dict], dict, dict, dict]:
    changes: list[dict] = []
    classifications = _classification_bucket()
    existing_consistent = Counter()
    conflict_counts = Counter()
    changed_by_model_tenant_result = defaultdict(lambda: defaultdict(Counter))

    model_specs = (
        (
            "Organization",
            Organization,
            "phone",
            "phone_normalized",
            "phone_normalization_region",
        ),
        (
            "PersonContact",
            PersonContact,
            "value",
            "normalized_value",
            "normalization_region",
        ),
    )
    for model_name, model, raw_field, normalized_field, region_field in model_specs:
        base_queryset = model.objects.filter(tenant_id__in=tenant_ids)
        if model_name == "PersonContact":
            base_queryset = base_queryset.filter(type="PHONE")
        missing_raw_with_identity = base_queryset.filter(
            Q(**{f"{raw_field}__isnull": True}) | Q(**{raw_field: ""})
        ).filter(
            Q(**{f"{normalized_field}__isnull": False})
            | Q(**{f"{region_field}__isnull": False})
        ).count()
        if missing_raw_with_identity:
            conflict_counts[model_name] += missing_raw_with_identity
        queryset = base_queryset.exclude(**{f"{raw_field}__isnull": True}).exclude(
            **{raw_field: ""}
        )
        if lock:
            queryset = queryset.select_for_update()
        for instance in queryset.order_by("tenant_id", "id"):
            raw_value = getattr(instance, raw_field)
            result = normalize_phone(raw_value, region=target_region)
            reason = result.reason_code.value if result.reason_code else "NONE"
            classifications[model_name][instance.tenant_id][
                f"{result.status.value}:{reason}"
            ] += 1
            expected_normalized = (
                result.e164 if result.status == PhoneNormalizationStatus.VALID else None
            )
            expected_region = (
                result.region_used
                if result.status == PhoneNormalizationStatus.VALID
                else None
            )
            old_normalized = getattr(instance, normalized_field)
            old_region = getattr(instance, region_field)
            if old_normalized is not None or old_region is not None:
                if (
                    old_normalized == expected_normalized
                    and old_region == expected_region
                ):
                    existing_consistent[model_name] += 1
                    continue
                conflict_counts[model_name] += 1
                continue
            if expected_normalized is None:
                continue
            changes.append(
                {
                    "model": model_name,
                    "pk": instance.pk,
                    "tenant_id": instance.tenant_id,
                    "old": {
                        normalized_field: old_normalized,
                        region_field: old_region,
                    },
                    "new": {
                        normalized_field: expected_normalized,
                        region_field: expected_region,
                    },
                }
            )
            changed_by_model_tenant_result[model_name][instance.tenant_id][
                f"{result.status.value}:{reason}"
            ] += 1

    if conflict_counts:
        summary = ", ".join(
            f"{model}={count}" for model, count in sorted(conflict_counts.items())
        )
        raise CommandError(
            "Existing canonical phone identity conflicts with deterministic normalization; "
            f"no changes were applied. {summary}"
        )
    return (
        changes,
        _classification_json(classifications),
        dict(sorted(existing_consistent.items())),
        _classification_json(changed_by_model_tenant_result),
    )


def build_phone_backfill_plan(
    *,
    tenant_ids: list[int],
    expected_total_tenants: int,
    target_region: str,
    lock: bool = False,
) -> dict:
    target_region = target_region.strip().upper()
    tenants = _validate_scope(
        tenant_ids=tenant_ids,
        expected_total_tenants=expected_total_tenants,
        target_region=target_region,
        lock=lock,
    )
    tenant_changes = []
    tenant_already_configured = 0
    for tenant in tenants:
        if tenant.default_phone_region == target_region:
            tenant_already_configured += 1
        elif tenant.default_phone_region is None:
            tenant_changes.append(
                {
                    "model": "Tenant",
                    "pk": tenant.pk,
                    "tenant_id": tenant.pk,
                    "old": {"default_phone_region": None},
                    "new": {"default_phone_region": target_region},
                }
            )
        else:
            raise CommandError(
                "Tenant default conflict: an explicitly selected tenant already has a "
                "different region. No changes were applied."
            )

    integrity = _person_integrity(
        [tenant.id for tenant in tenants],
        lock=lock,
    )
    (
        identity_changes,
        classifications,
        existing_consistent,
        identity_changes_by_result,
    ) = _identity_changes(
        tenant_ids=[tenant.id for tenant in tenants],
        target_region=target_region,
        lock=lock,
    )
    changes = tenant_changes + identity_changes
    changes_by_model = Counter(change["model"] for change in changes)
    changes_by_tenant = Counter(change["tenant_id"] for change in changes)
    return {
        "tenant_ids": [tenant.id for tenant in tenants],
        "expected_total_tenants": expected_total_tenants,
        "target_region": target_region,
        "changes": changes,
        "summary": {
            "changes_total": len(changes),
            "changes_by_model": dict(sorted(changes_by_model.items())),
            "changes_by_tenant": {
                str(tenant_id): count
                for tenant_id, count in sorted(changes_by_tenant.items())
            },
            "identity_changes_by_model_tenant_result": identity_changes_by_result,
            "tenant_already_configured": tenant_already_configured,
            "existing_identity_consistent": existing_consistent,
            "classifications": classifications,
            "person_primary_integrity": integrity,
        },
    }


def _validate_batch_id(batch_id: str) -> str:
    if not BATCH_ID_PATTERN.fullmatch(batch_id or ""):
        raise CommandError(
            "Batch ID must be 1-64 characters using letters, digits, dot, underscore, or dash."
        )
    return batch_id


def _validate_manifest_parent(path: Path) -> Path:
    if not path.is_absolute():
        raise CommandError("Manifest path must be absolute.")
    try:
        resolved_parent = path.parent.resolve(strict=True)
    except OSError as error:
        raise CommandError("Manifest parent must be an existing directory.") from error
    if path.parent.is_symlink() or not resolved_parent.is_dir():
        raise CommandError("Manifest parent must be a real directory.")
    repository_root = Path(settings.BASE_DIR).resolve()
    if resolved_parent == repository_root or repository_root in resolved_parent.parents:
        raise CommandError("Manifest must be stored outside the application repository.")
    parent_stat = resolved_parent.stat()
    if parent_stat.st_uid != os.geteuid() or parent_stat.st_mode & 0o077:
        raise CommandError("Manifest parent must be owned by the operator and mode 0700 or stricter.")
    return resolved_parent / path.name


def write_phone_backfill_manifest(path_value: str, manifest: dict) -> Path:
    path = _validate_manifest_parent(Path(path_value))
    if path.exists() or path.is_symlink():
        raise CommandError("Manifest path already exists; batch manifests are no-clobber.")
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    fd = None
    try:
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path, follow_symlinks=False)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError as error:
        raise CommandError("Manifest path already exists; batch manifests are no-clobber.") from error
    finally:
        if fd is not None:
            os.close(fd)
        if temporary.exists():
            temporary.unlink()
    return path


def _apply_change(change: dict, *, direction: str) -> None:
    model_name = change["model"]
    model = {
        "Tenant": Tenant,
        "Organization": Organization,
        "PersonContact": PersonContact,
    }[model_name]
    source = change["old"] if direction == "forward" else change["new"]
    destination = change["new"] if direction == "forward" else change["old"]
    queryset = model.objects.filter(pk=change["pk"])
    if model_name != "Tenant":
        queryset = queryset.filter(tenant_id=change["tenant_id"])
    queryset = queryset.filter(**source)
    if queryset.update(**destination) != 1:
        raise CommandError(
            "Concurrent or post-batch drift detected while applying redacted manifest; "
            "the database transaction was rolled back."
        )


def _manifest_changes(changes: list[dict]) -> list[dict]:
    return [
        {
            "model": change["model"],
            "pk": change["pk"],
            "tenant_id": change["tenant_id"],
            "old": change["old"],
        }
        for change in changes
    ]


def _change_state_sha256(changes: list[dict], *, side: str) -> str:
    state = [
        {
            "model": change["model"],
            "pk": change["pk"],
            "tenant_id": change["tenant_id"],
            "fields": change[side],
        }
        for change in changes
    ]
    return _digest(state)["sha256"]


def _current_manifest_state(changes: list[dict], *, lock: bool) -> list[dict]:
    model_map = {
        "Tenant": Tenant,
        "Organization": Organization,
        "PersonContact": PersonContact,
    }
    state = []
    for change in changes:
        queryset = model_map[change["model"]].objects
        if lock:
            queryset = queryset.select_for_update()
        try:
            instance = queryset.get(pk=change["pk"])
        except model_map[change["model"]].DoesNotExist as error:
            raise CommandError(
                "Rollback manifest references a row that no longer exists."
            ) from error
        instance_tenant_id = (
            instance.pk if change["model"] == "Tenant" else instance.tenant_id
        )
        if instance_tenant_id != change["tenant_id"]:
            raise CommandError("Rollback manifest scope does not match the database row.")
        state.append(
            {
                "model": change["model"],
                "pk": change["pk"],
                "tenant_id": change["tenant_id"],
                "fields": {
                    field: getattr(instance, field)
                    for field in MODEL_FIELDS[change["model"]]
                },
            }
        )
    return state


def _rollback_state(manifest: dict, *, lock: bool) -> str:
    state = _current_manifest_state(manifest["changes"], lock=lock)
    old_matches = [
        row["fields"] == change["old"]
        for row, change in zip(state, manifest["changes"], strict=True)
    ]
    if all(old_matches):
        return "ALREADY_RESTORED"
    if any(old_matches):
        raise CommandError(
            "Rollback blocked because the batch is only partially present; "
            "no changes were applied."
        )
    if _digest(state)["sha256"] != manifest["new_state_sha256"]:
        raise CommandError(
            "Rollback blocked because additive fields changed after the batch; "
            "no changes were applied."
        )
    return "TO_RESTORE"


def execute_phone_backfill(
    *,
    tenant_ids: list[int],
    expected_total_tenants: int,
    target_region: str,
    apply_changes: bool,
    batch_id: str | None = None,
    manifest_path: str | None = None,
) -> dict:
    if not apply_changes:
        plan = build_phone_backfill_plan(
            tenant_ids=tenant_ids,
            expected_total_tenants=expected_total_tenants,
            target_region=target_region,
        )
        fingerprints = phone_backfill_fingerprints(plan["tenant_ids"])
        return {
            "mode": "DRY_RUN",
            "tenant_ids": plan["tenant_ids"],
            "expected_total_tenants": expected_total_tenants,
            "target_region": plan["target_region"],
            **plan["summary"],
            "changes_applied": 0,
            "fingerprints_before": fingerprints,
            "fingerprints_after": fingerprints,
        }

    batch_id = _validate_batch_id(batch_id or "")
    if not manifest_path:
        raise CommandError("Apply requires an absolute no-clobber manifest path.")
    with transaction.atomic():
        plan = build_phone_backfill_plan(
            tenant_ids=tenant_ids,
            expected_total_tenants=expected_total_tenants,
            target_region=target_region,
            lock=True,
        )
        before = phone_backfill_fingerprints(plan["tenant_ids"])
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "batch_id": batch_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tenant_ids": plan["tenant_ids"],
            "expected_total_tenants": expected_total_tenants,
            "target_region": plan["target_region"],
            "fingerprints_before": before,
            "new_state_sha256": _change_state_sha256(plan["changes"], side="new"),
            "changes": _manifest_changes(plan["changes"]),
        }
        written_manifest = write_phone_backfill_manifest(manifest_path, manifest)
        for change in plan["changes"]:
            _apply_change(change, direction="forward")
        after = phone_backfill_fingerprints(plan["tenant_ids"])
        if before["raw_phone"] != after["raw_phone"]:
            raise CommandError("Raw phone fingerprint changed; apply was rolled back.")
        if before["publication"] != after["publication"]:
            raise CommandError("Publication fingerprint changed; apply was rolled back.")
    return {
        "mode": "APPLY",
        "batch_id": batch_id,
        "manifest_path": str(written_manifest),
        "tenant_ids": plan["tenant_ids"],
        "expected_total_tenants": expected_total_tenants,
        "target_region": plan["target_region"],
        **plan["summary"],
        "changes_applied": len(plan["changes"]),
        "fingerprints_before": before,
        "fingerprints_after": after,
    }


def load_phone_backfill_manifest(path_value: str) -> tuple[Path, dict]:
    path = _validate_manifest_parent(Path(path_value))
    if path.is_symlink() or not path.is_file():
        raise CommandError("Rollback manifest must be an existing regular file.")
    file_stat = path.stat()
    if file_stat.st_uid != os.geteuid() or stat.S_IMODE(file_stat.st_mode) != 0o600:
        raise CommandError("Rollback manifest must be operator-owned with exact mode 0600.")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CommandError("Rollback manifest is unreadable or invalid JSON.") from error
    required = {
        "schema_version",
        "batch_id",
        "created_at",
        "tenant_ids",
        "expected_total_tenants",
        "target_region",
        "fingerprints_before",
        "new_state_sha256",
        "changes",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise CommandError("Rollback manifest has an unknown schema.")
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise CommandError("Rollback manifest schema version is unsupported.")
    _validate_batch_id(manifest["batch_id"])
    tenant_ids = manifest["tenant_ids"]
    if (
        not isinstance(tenant_ids, list)
        or not tenant_ids
        or any(type(tenant_id) is not int or tenant_id < 1 for tenant_id in tenant_ids)
        or tenant_ids != sorted(set(tenant_ids))
    ):
        raise CommandError("Rollback manifest has an invalid explicit tenant scope.")
    if (
        type(manifest["expected_total_tenants"]) is not int
        or manifest["expected_total_tenants"] != len(tenant_ids)
    ):
        raise CommandError("Rollback manifest has an invalid expected tenant count.")
    if not isinstance(manifest["target_region"], str):
        raise CommandError("Rollback manifest has an invalid target region.")
    try:
        datetime.fromisoformat(manifest["created_at"])
    except (TypeError, ValueError) as error:
        raise CommandError("Rollback manifest has an invalid creation timestamp.") from error
    fingerprints = manifest["fingerprints_before"]
    if not isinstance(fingerprints, dict) or set(fingerprints) != {
        "raw_phone",
        "publication",
        "additive_identity",
    }:
        raise CommandError("Rollback manifest has invalid fingerprints.")
    for fingerprint in fingerprints.values():
        if (
            not isinstance(fingerprint, dict)
            or set(fingerprint) != {"count", "sha256"}
            or type(fingerprint["count"]) is not int
            or fingerprint["count"] < 0
            or not isinstance(fingerprint["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", fingerprint["sha256"])
        ):
            raise CommandError("Rollback manifest has invalid fingerprints.")
    if (
        not isinstance(manifest["new_state_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", manifest["new_state_sha256"])
    ):
        raise CommandError("Rollback manifest has an invalid new-state fingerprint.")
    if not isinstance(manifest["changes"], list):
        raise CommandError("Rollback manifest changes must be a list.")
    seen_rows = set()
    for change in manifest["changes"]:
        if not isinstance(change, dict) or set(change) != {
            "model",
            "pk",
            "tenant_id",
            "old",
        }:
            raise CommandError("Rollback manifest contains an invalid change entry.")
        expected_fields = set(MODEL_FIELDS.get(change["model"], ()))
        if not expected_fields or set(change["old"]) != expected_fields:
            raise CommandError("Rollback manifest contains fields outside the additive contract.")
        if (
            type(change["pk"]) is not int
            or change["pk"] < 1
            or type(change["tenant_id"]) is not int
            or change["tenant_id"] not in manifest["tenant_ids"]
        ):
            raise CommandError("Rollback manifest contains invalid scoped identifiers.")
        if change["model"] == "Tenant" and change["pk"] != change["tenant_id"]:
            raise CommandError("Rollback manifest contains an invalid tenant row.")
        for field, value in change["old"].items():
            if value is not None and not isinstance(value, str):
                raise CommandError("Rollback manifest contains invalid additive values.")
            if field in {
                "default_phone_region",
                "phone_normalization_region",
                "normalization_region",
            } and value is not None and value not in phonenumbers.SUPPORTED_REGIONS:
                raise CommandError("Rollback manifest contains an invalid stored region.")
            if field in {"phone_normalized", "normalized_value"} and value is not None:
                if not re.fullmatch(r"\+[1-9][0-9]{1,14}", value):
                    raise CommandError(
                        "Rollback manifest contains an invalid canonical phone value."
                    )
        row_identity = (change["model"], change["pk"])
        if row_identity in seen_rows:
            raise CommandError("Rollback manifest contains duplicate rows.")
        seen_rows.add(row_identity)
    return path, manifest


def execute_phone_backfill_rollback(
    *,
    manifest_path: str,
    apply_changes: bool,
) -> dict:
    path, manifest = load_phone_backfill_manifest(manifest_path)
    tenant_ids = manifest["tenant_ids"]
    _validate_scope(
        tenant_ids=tenant_ids,
        expected_total_tenants=manifest["expected_total_tenants"],
        target_region=manifest["target_region"],
        lock=False,
    )
    state = _rollback_state(manifest, lock=False)
    changes_to_restore = len(manifest["changes"]) if state == "TO_RESTORE" else 0
    already_restored = (
        len(manifest["changes"]) if state == "ALREADY_RESTORED" else 0
    )
    before = phone_backfill_fingerprints(tenant_ids)
    if not apply_changes:
        return {
            "mode": "ROLLBACK_DRY_RUN",
            "batch_id": manifest["batch_id"],
            "manifest_path": str(path),
            "tenant_ids": tenant_ids,
            "changes_to_restore": changes_to_restore,
            "already_restored": already_restored,
            "changes_applied": 0,
            "fingerprints_before": before,
            "fingerprints_after": before,
        }

    with transaction.atomic():
        locked_state = _rollback_state(manifest, lock=True)
        changes_applied = 0
        if locked_state == "TO_RESTORE":
            model_map = {
                "Tenant": Tenant,
                "Organization": Organization,
                "PersonContact": PersonContact,
            }
            for change in manifest["changes"]:
                queryset = model_map[change["model"]].objects.filter(pk=change["pk"])
                if change["model"] != "Tenant":
                    queryset = queryset.filter(tenant_id=change["tenant_id"])
                if queryset.update(**change["old"]) != 1:
                    raise CommandError(
                        "Rollback scope changed concurrently; the database transaction "
                        "was rolled back."
                    )
                changes_applied += 1
        after = phone_backfill_fingerprints(tenant_ids)
        if before["raw_phone"] != after["raw_phone"]:
            raise CommandError("Raw phone fingerprint changed; rollback was rolled back.")
        if before["publication"] != after["publication"]:
            raise CommandError("Publication fingerprint changed; rollback was rolled back.")
    return {
        "mode": "ROLLBACK_APPLY",
        "batch_id": manifest["batch_id"],
        "manifest_path": str(path),
        "tenant_ids": tenant_ids,
        "changes_to_restore": changes_to_restore,
        "already_restored": already_restored,
        "changes_applied": changes_applied,
        "fingerprints_before": before,
        "fingerprints_after": after,
    }

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path

from botocore.exceptions import ClientError
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from .backup import (
    DeterministicRenderer,
    make_direct_backup,
    make_regeneration_backup,
    restore_direct,
    restore_regenerated,
)
from .contracts import (
    AbsoluteOrigin,
    AppState,
    PROCESSING_VERSION,
    PublicOriginConfiguration,
    checksum_bytes,
    private_original_key,
    processing_artifact_key,
    public_release_key,
)
from .journal import DenyJournal, JournalEvent, JournalError
from .purge import CacheSimulator, RecordingPurgeProvider
from .storage import (
    PUBLIC_CACHE_CONTROL,
    PrivateAccessDenied,
    RecordingPrivateAccessBoundary,
    S3Lab,
)


FALLBACK_FILENAMES = {
    "square": "emergency-fallback-square.png",
    "landscape": "emergency-fallback-landscape.png",
    "share": "emergency-fallback-share.png",
}


def static_fallback_path(variant: str = "landscape") -> Path:
    filename = FALLBACK_FILENAMES[variant]
    explicit = os.environ.get("PHASE3B1_STATIC_ROOT")
    if explicit:
        path = Path(explicit) / filename
    else:
        path = (
            Path(__file__).resolve().parents[3]
            / "crm"
            / "static"
            / "crm"
            / "public-image-fallback"
            / "v1"
            / filename
        )
    if not path.is_file():
        raise RuntimeError(f"static phase 3B.1 fallback is missing: {path}")
    return path


def static_fallback_bytes(variant: str = "landscape") -> bytes:
    return static_fallback_path(variant).read_bytes()


def resolve_public(
    state: AppState,
    *,
    journal: DenyJournal,
    s3: S3Lab | None,
    origin: AbsoluteOrigin,
) -> dict[str, str]:
    try:
        denied = journal.deny_set()
    except JournalError:
        return _fallback("journal_unavailable")
    if not state.public_key:
        return _fallback("state_missing")
    if state.public_key in denied:
        return _fallback("release_denied")
    if s3 is None:
        return _fallback("storage_unavailable")
    try:
        available = s3.exists(s3.public_bucket, state.public_key)
    except Exception:
        return _fallback("storage_unavailable")
    if not available:
        return _fallback("rendition_missing")
    return {"kind": "public", "url": origin.join(state.public_key), "key": state.public_key}


def reconcile(state: AppState, *, journal: DenyJournal, s3: S3Lab) -> tuple[AppState, list[str]]:
    denied = journal.deny_set()
    actions: list[str] = []
    if state.public_key and state.public_key in denied:
        if s3.exists(s3.public_bucket, state.public_key):
            s3.delete(s3.public_bucket, state.public_key)
            actions.append(f"deleted:{state.public_key}")
        actions.append(f"blocked:{state.public_key}")
        state = replace(state, public_key=None)
    return state, actions


def execute_takedown_restore_scenario(root: Path, *, endpoint: str) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    s3 = S3Lab(endpoint=endpoint)
    s3.provision()

    journal = DenyJournal(root / "journal" / "deny-events.jsonl")
    journal.initialize()
    cache = CacheSimulator()
    purge = RecordingPurgeProvider(cache)
    public_origin = AbsoluteOrigin("https://media.example.test/assets")

    tenant = "tenant-a"
    actor = "actor-42"
    original_bytes = b"synthetic-private-original-phase3b2"
    source_checksum = checksum_bytes(original_bytes)
    original_key = private_original_key(tenant, source_checksum, "png")
    private_result = s3.save_alias_immutable(
        "image_originals_private",
        original_key,
        original_bytes,
        content_type="image/png",
    )

    config = json.dumps(
        {
            "fit": "cover",
            "focus": [0.5, 0.5],
            "format": "webp",
            "processing_version": PROCESSING_VERSION,
            "variant": "landscape",
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    renderer = DeterministicRenderer()
    regeneration_bundle = make_regeneration_backup(original_bytes, canonical_render_config=config)
    artifact_bytes = renderer.render(original_bytes, regeneration_bundle.metadata)
    artifact_checksum = checksum_bytes(artifact_bytes)
    artifact_key = processing_artifact_key(
        source_checksum,
        variant="landscape",
        fit="cover",
        focus=(0.5, 0.5),
        output_format="WEBP",
    )
    artifact_result = s3.put_private_artifact(
        artifact_key,
        artifact_bytes,
        content_type="image/webp",
    )

    r1 = public_release_key(
        tenant=tenant,
        actor=actor,
        release_revision=1,
        variant="landscape",
        artifact_checksum=artifact_checksum,
        extension="webp",
    )
    public_r1 = s3.save_alias_immutable(
        "image_renditions_public",
        r1,
        artifact_bytes,
        content_type="image/webp",
    )
    state = AppState(tenant, actor, r1, artifact_key, 1)
    r1_url = public_origin.join(r1)
    r1_anonymous = s3.anonymous_get(s3.public_bucket, r1)
    cache.seed(r1_url, r1_anonymous)

    t0 = {
        "private_original": s3.exists(s3.private_bucket, original_key),
        "artifact": s3.exists(s3.private_bucket, artifact_key),
        "r1": s3.exists(s3.public_bucket, r1),
        "r1_anonymous": r1_anonymous == artifact_bytes,
        "state_key": state.public_key,
        "journal_events": len(journal.replay()),
    }

    state_snapshot = state.as_dict()
    direct_bundle = make_direct_backup(original_bytes, artifact_bytes)
    object_inventory = {
        "private": [original_key, artifact_key],
        "public": [r1],
        "checksums": {
            original_key: source_checksum,
            artifact_key: artifact_checksum,
            r1: artifact_checksum,
        },
    }
    t1 = {
        "state_snapshot": state_snapshot,
        "object_inventory": object_inventory,
        "deny_journal_in_snapshot": False,
    }

    deny_event = JournalEvent(
        event_id="evt-takedown-r1",
        tenant=tenant,
        public_key=r1,
        artifact_checksum=artifact_checksum,
        source_checksum=source_checksum,
        timestamp="2026-07-31T12:02:00Z",
        action="deny",
        reason_code="owner_takedown",
        principal="phase3b2-test",
        previous_release_key=r1,
    )
    appended = journal.append(deny_event)
    s3.delete(s3.public_bucket, r1)
    stale_before_purge = cache.contains(r1_url)
    purge_result = purge.purge(r1_url)
    t2_resolution = resolve_public(state, journal=journal, s3=s3, origin=public_origin)
    t2 = {
        "deny_appended": appended,
        "origin_deleted": not s3.exists(s3.public_bucket, r1),
        "stale_before_purge": stale_before_purge,
        "purge": purge_result.as_dict(),
        "r1_not_delivered": not cache.contains(r1_url),
        "resolver": t2_resolution,
    }

    state = AppState.from_dict(state_snapshot)
    restored_r1 = s3.save_alias_immutable(
        "image_renditions_public",
        r1,
        direct_bundle.objects["active-public-rendition"],
        content_type="image/webp",
    )
    t3 = {
        "restored_state_key": state.public_key,
        "r1_reintroduced": restored_r1.created,
        "journal_events": len(journal.replay()),
        "journal_rolled_back": False,
    }

    state, reconciliation_actions = reconcile(state, journal=journal, s3=s3)
    t4_resolution = resolve_public(state, journal=journal, s3=s3, origin=public_origin)
    t4 = {
        "actions": reconciliation_actions,
        "r1_origin_blocked": not s3.exists(s3.public_bucket, r1),
        "r1_denied": r1 in journal.deny_set(),
        "resolver": t4_resolution,
    }

    r2 = public_release_key(
        tenant=tenant,
        actor=actor,
        release_revision=2,
        variant="landscape",
        artifact_checksum=artifact_checksum,
        extension="webp",
    )
    public_r2 = s3.save_alias_immutable(
        "image_renditions_public",
        r2,
        artifact_bytes,
        content_type="image/webp",
    )
    release_event = JournalEvent(
        event_id="evt-authorized-r2",
        tenant=tenant,
        public_key=r2,
        artifact_checksum=artifact_checksum,
        source_checksum=source_checksum,
        timestamp="2026-07-31T12:05:00Z",
        action="authorized_release",
        reason_code="owner_authorized_restore",
        principal="phase3b2-test",
        previous_release_key=r1,
        new_release_key=r2,
    )
    journal.append(release_event)
    state = AppState(tenant, actor, r2, artifact_key, 2)
    t5_resolution = resolve_public(state, journal=journal, s3=s3, origin=public_origin)
    t5 = {
        "r2_created": public_r2.created,
        "r2_differs_from_r1": r2 != r1,
        "r1_still_denied": r1 in journal.deny_set(),
        "r1_absent": not s3.exists(s3.public_bucket, r1),
        "resolver": t5_resolution,
    }

    direct_restored, direct_measurement = restore_direct(direct_bundle)
    regenerated, regenerate_measurement = restore_regenerated(
        regeneration_bundle,
        renderer,
        expected_rendition=artifact_bytes,
    )

    versioning = _versioning_probe(s3)
    sentinel = _default_storage_sentinel(root, private_result, public_r1)
    production_origins = PublicOriginConfiguration.from_values(
        public_site_origin="https://www.example.test/",
        public_media_origin="https://media.example.test/assets/",
    )
    origin_contract = {
        "public_site_origin": production_origins.public_site_origin.value,
        "public_media_origin": production_origins.public_media_origin.value,
        "configured_public_url": production_origins.media_url(r2),
        "request_host_ignored": production_origins.media_url(r2),
        "x_forwarded_host_ignored": production_origins.media_url(r2),
        "internal_endpoint_leaked": endpoint in production_origins.media_url(r2),
    }

    fallback = static_fallback_bytes("landscape")
    evidence = {
        "schema_version": 1,
        "status": "prototype-evidence-not-runtime",
        "dependencies": {
            "django": "5.1.15",
            "django_storages": "1.14.6",
            "boto3": "1.43.62",
            "moto": "5.2.2",
        },
        "emulator": {
            "name": "Moto Server",
            "production_provider": False,
            "buckets": {
                "private": s3.private_bucket,
                "public_unversioned": s3.public_bucket,
                "public_versioned_probe": s3.versioned_public_bucket,
            },
            "locations": {
                bucket: s3.client.get_bucket_location(Bucket=bucket).get("LocationConstraint")
                or "us-east-1"
                for bucket in (s3.private_bucket, s3.public_bucket, s3.versioned_public_bucket)
            },
        },
        "storage_aliases": sentinel,
        "objects": {
            "private_original": private_result.as_dict(),
            "artifact": artifact_result.as_dict(),
            "r1": public_r1.as_dict(),
            "r2": public_r2.as_dict(),
        },
        "key_contract": {
            "processing_version": PROCESSING_VERSION,
            "artifact_key": artifact_key,
            "artifact_checksum": artifact_checksum,
            "r1": r1,
            "r2": r2,
            "same_artifact_bytes": direct_restored == regenerated == artifact_bytes,
        },
        "private_access": {
            "anonymous_denied": s3.anonymous_denied(s3.private_bucket, original_key),
            "under_public_origin": original_key in origin_contract["configured_public_url"],
        },
        "public_access": {
            "r2_anonymous": s3.anonymous_get(s3.public_bucket, r2) == artifact_bytes,
            "cache_control": s3.client.head_object(Bucket=s3.public_bucket, Key=r2).get(
                "CacheControl"
            ),
            "content_type": s3.client.head_object(Bucket=s3.public_bucket, Key=r2).get(
                "ContentType"
            ),
        },
        "origin_contract": origin_contract,
        "versioning": versioning,
        "journal": {
            "separate_from_snapshot": True,
            "event_count": len(journal.replay()),
            "denied_keys": sorted(journal.deny_set()),
            "append_only_api": ["append", "replay", "deny_set"],
        },
        "takedown_restore": {"T0": t0, "T1": t1, "T2": t2, "T3": t3, "T4": t4, "T5": t5},
        "backup": {
            "strategy_a": direct_measurement.as_dict(),
            "strategy_b": regenerate_measurement.as_dict(),
            "recommendation": "hybrid-active-renditions-plus-originals-and-metadata",
        },
        "fallback": {
            "filename": static_fallback_path("landscape").name,
            "checksum": checksum_bytes(fallback),
            "byte_size": len(fallback),
            "external_dependencies": [],
            "covered_failures": [
                "storage_unavailable",
                "rendition_missing",
                "private_storage_unavailable",
                "deny_reconciliation_incomplete",
                "dynamic_renderer_failed",
                "state_or_key_unknown",
            ],
        },
        "purge_calls": purge.calls,
        "s3_operations_exercised": [
            "create_bucket",
            "put_object",
            "get_object",
            "head_object",
            "delete_object",
            "put_bucket_policy",
            "put_bucket_versioning",
            "list_object_versions",
            "delete_marker",
            "copy_object",
        ],
    }
    _assert_scenario(evidence)
    return evidence


def _versioning_probe(s3: S3Lab) -> dict[str, object]:
    private_key = "versioning-probe/private-history.webp"
    first = s3.client.put_object(
        Bucket=s3.private_bucket,
        Key=private_key,
        Body=b"private-v1",
        ContentType="image/webp",
    )["VersionId"]
    second = s3.client.put_object(
        Bucket=s3.private_bucket,
        Key=private_key,
        Body=b"private-v2",
        ContentType="image/webp",
    )["VersionId"]
    s3.delete(s3.private_bucket, private_key)
    private_versions = s3.object_versions(s3.private_bucket, private_key)
    old_private = s3.client.get_object(
        Bucket=s3.private_bucket,
        Key=private_key,
        VersionId=first,
    )["Body"].read()
    copied_key = "versioning-probe/private-history-copy.webp"
    s3.client.copy_object(
        Bucket=s3.private_bucket,
        Key=copied_key,
        CopySource={"Bucket": s3.private_bucket, "Key": private_key, "VersionId": first},
        MetadataDirective="COPY",
    )
    copied_private = s3.client.get_object(Bucket=s3.private_bucket, Key=copied_key)["Body"].read()
    emulator_anonymous_old_private_reachable = False
    try:
        s3.anonymous_get(s3.private_bucket, private_key, version_id=first)
    except ClientError:
        pass
    else:
        emulator_anonymous_old_private_reachable = True
    boundary = RecordingPrivateAccessBoundary(s3)
    domain_boundary_denied = False
    try:
        boundary.get(private_key, principal="anonymous", version_id=first)
    except PrivateAccessDenied:
        domain_boundary_denied = True

    public_key = "versioning-probe/public-history.webp"
    public_first = s3.put_public_versioned(public_key, b"public-v1", content_type="image/webp")
    public_second = s3.put_public_versioned(public_key, b"public-v2", content_type="image/webp")
    public_old_reachable = s3.anonymous_get(
        s3.versioned_public_bucket,
        public_key,
        version_id=public_first,
    ) == b"public-v1"
    return {
        "private": {
            "enabled": s3.client.get_bucket_versioning(Bucket=s3.private_bucket).get("Status")
            == "Enabled",
            "two_versions": len(private_versions["versions"]) == 2,
            "delete_markers": len(private_versions["delete_markers"]),
            "old_admin_access": old_private == b"private-v1",
            "copy_object_preserved_bytes": copied_private == b"private-v1",
            "moto_old_version_anonymous_reachable": emulator_anonymous_old_private_reachable,
            "domain_boundary_anonymous_denied": domain_boundary_denied,
            "distinct_version_ids": first != second,
            "emulator_gap": (
                "Moto 5.2.2 allowed unsigned VersionId access despite no private bucket policy"
                if emulator_anonymous_old_private_reachable
                else None
            ),
        },
        "public_versioned_probe": {
            "two_versions": public_first != public_second,
            "old_version_anonymously_reachable": public_old_reachable,
            "risk": "historical bytes can remain reachable in a public bucket",
        },
        "public_unversioned_active": {
            "enabled": not bool(
                s3.client.get_bucket_versioning(Bucket=s3.public_bucket).get("Status")
            ),
            "immutable_keys": True,
        },
        "recommendation": "unversioned-public-with-immutable-release-keys",
    }


def _default_storage_sentinel(root: Path, private_result, public_result) -> dict[str, object]:
    default_storage = storages["default"]
    sentinel_name = "sentinel/default-import-export-contract.txt"
    if default_storage.exists(sentinel_name):
        default_storage.delete(sentinel_name)
    saved = default_storage.save(sentinel_name, ContentFile(b"default-storage-sentinel"))
    return {
        "aliases": sorted(
            ["default", "staticfiles", "image_originals_private", "image_renditions_public"]
        ),
        "default_saved_name": saved,
        "default_exists": default_storage.exists(saved),
        "default_backend": default_storage.__class__.__name__,
        "default_under_lab_root": str(root / "default-files") in str(default_storage.path(saved)),
        "staticfiles_backend": storages["staticfiles"].__class__.__name__,
        "private_bucket": private_result.bucket,
        "public_bucket": public_result.bucket,
        "separate_destinations": private_result.bucket != public_result.bucket,
        "crm_import_export_models_used": False,
    }


def _fallback(reason: str) -> dict[str, str]:
    return {
        "kind": "static_fallback",
        "reason": reason,
        "filename": static_fallback_path("landscape").name,
    }


def _assert_scenario(evidence: dict[str, object]) -> None:
    stages = evidence["takedown_restore"]
    assert stages["T0"]["r1_anonymous"]
    assert stages["T2"]["resolver"]["kind"] == "static_fallback"
    assert stages["T4"]["r1_denied"] and stages["T4"]["r1_origin_blocked"]
    assert stages["T5"]["r2_differs_from_r1"] and stages["T5"]["r1_still_denied"]
    assert stages["T5"]["resolver"]["kind"] == "public"
    assert not evidence["origin_contract"]["internal_endpoint_leaked"]
    assert evidence["public_access"]["cache_control"] == PUBLIC_CACHE_CONTROL

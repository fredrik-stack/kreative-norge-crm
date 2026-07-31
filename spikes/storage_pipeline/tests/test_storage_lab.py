from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest

from botocore.exceptions import ClientError

from storage_lab.backup import (
    BackupError,
    DeterministicRenderer,
    StorageUnavailable,
    make_direct_backup,
    make_regeneration_backup,
    restore_direct,
    restore_regenerated,
)
from storage_lab.contracts import (
    AbsoluteOrigin,
    AppState,
    ContractError,
    ImmutableConflict,
    PROCESSING_VERSION,
    PublicOriginConfiguration,
    checksum_bytes,
    private_original_key,
    processing_artifact_key,
    public_release_key,
    validate_key,
)
from storage_lab.journal import (
    DenyJournal,
    DuplicateEventConflict,
    JournalCorrupt,
    JournalEvent,
    JournalUnavailable,
)
from storage_lab.purge import CacheSimulator, RecordingPurgeProvider
from storage_lab.storage import (
    PUBLIC_CACHE_CONTROL,
    PrivateAccessDenied,
    RecordingPrivateAccessBoundary,
    S3Lab,
    configure_django_environment,
    reset_moto,
)


ENDPOINT = os.environ.get("PHASE3B2_S3_ENDPOINT", "http://localhost:5000")
SUITE_ROOT = Path(tempfile.mkdtemp(prefix="phase3b2-tests-"))
configure_django_environment(SUITE_ROOT, endpoint=ENDPOINT)

import django

django.setup()


SOURCE_BYTES = b"phase3b2-synthetic-original"
SOURCE_CHECKSUM = checksum_bytes(SOURCE_BYTES)
ARTIFACT_BYTES = b"phase3b2-synthetic-artifact"
ARTIFACT_CHECKSUM = checksum_bytes(ARTIFACT_BYTES)


def release_key(revision: int = 1, *, tenant: str = "tenant-a") -> str:
    return public_release_key(
        tenant=tenant,
        actor="actor-42",
        release_revision=revision,
        variant="landscape",
        artifact_checksum=ARTIFACT_CHECKSUM,
        extension="webp",
    )


def deny_event(event_id: str = "evt-1", key: str | None = None) -> JournalEvent:
    return JournalEvent(
        event_id=event_id,
        tenant="tenant-a",
        public_key=key or release_key(),
        artifact_checksum=ARTIFACT_CHECKSUM,
        source_checksum=SOURCE_CHECKSUM,
        timestamp="2026-07-31T12:00:00Z",
        action="deny",
        reason_code="test_takedown",
        principal="phase3b2-test",
        previous_release_key=key or release_key(),
    )


class ContractTests(unittest.TestCase):
    def test_phase3b1_artifact_identity_is_reused_and_deterministic(self):
        kwargs = {
            "variant": "landscape",
            "fit": "cover",
            "focus": (0.72, 0.44),
            "output_format": "WEBP",
        }
        first = processing_artifact_key(SOURCE_CHECKSUM, **kwargs)
        second = processing_artifact_key(SOURCE_CHECKSUM, **kwargs)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith(f"renditions/{PROCESSING_VERSION}/"))
        self.assertNotIn("actor", first)

    def test_encoder_settings_are_bound_to_processing_version(self):
        expected = processing_artifact_key(
            SOURCE_CHECKSUM,
            variant="landscape",
            fit="cover",
            focus=(0.5, 0.5),
            output_format="WEBP",
            encoder_settings={"quality": 82, "method": 6, "exact_alpha": True},
        )
        self.assertIn(PROCESSING_VERSION, expected)
        with self.assertRaises(ContractError):
            processing_artifact_key(
                SOURCE_CHECKSUM,
                variant="landscape",
                fit="cover",
                focus=(0.5, 0.5),
                output_format="WEBP",
                encoder_settings={"quality": 80, "method": 6, "exact_alpha": True},
            )

    def test_public_release_changes_without_reencoding(self):
        r1 = release_key(1)
        r2 = release_key(2)
        self.assertNotEqual(r1, r2)
        self.assertIn(ARTIFACT_CHECKSUM[:20], r1)
        self.assertIn(ARTIFACT_CHECKSUM[:20], r2)

    def test_direct_artifact_public_key_is_compared_with_scoped_release_key(self):
        artifact = processing_artifact_key(
            SOURCE_CHECKSUM,
            variant="landscape",
            fit="cover",
            focus=(0.5, 0.5),
            output_format="WEBP",
        )
        separate_release = release_key()
        self.assertFalse(artifact.startswith("public/tenant-a/actor-42/"))
        self.assertTrue(separate_release.startswith("public/tenant-a/actor-42/r1/"))
        self.assertNotEqual(artifact, separate_release)

    def test_tenant_and_actor_scope_are_explicit(self):
        tenant_a = release_key(1, tenant="tenant-a")
        tenant_b = release_key(1, tenant="tenant-b")
        self.assertNotEqual(tenant_a, tenant_b)
        with self.assertRaises(ContractError):
            validate_key(tenant_a, expected_tenant="tenant-b")

    def test_unsafe_keys_are_rejected(self):
        unsafe = [
            "../public/x",
            "public//x",
            "public/tenant-a/../x",
            "public/tenant-a/x\n.webp",
            "public/tenant-a/access-token.webp",
            "public/tenant-a/x.webp?signature=abc",
            "/public/tenant-a/x.webp",
            "public\\tenant-a\\x.webp",
        ]
        for key in unsafe:
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_key(key)

    def test_private_key_is_checksum_scoped_and_immutable_in_shape(self):
        key = private_original_key("tenant-a", SOURCE_CHECKSUM, "png")
        self.assertIn(SOURCE_CHECKSUM, key)
        self.assertNotIn("actor name", key)


class OriginTests(unittest.TestCase):
    def test_https_origin_is_normalized_and_joined_without_double_slash(self):
        origin = AbsoluteOrigin("https://media.example.test/assets/")
        url = origin.join(release_key())
        self.assertTrue(url.startswith("https://media.example.test/assets/public/"))
        self.assertNotIn("//public", url)
        self.assertNotIn("?", url)

    def test_credentials_query_fragment_and_external_http_are_rejected(self):
        invalid = [
            "https://user:pass@media.example.test",
            "https://media.example.test?token=x",
            "https://media.example.test#fragment",
            "http://media.example.test",
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ContractError):
                AbsoluteOrigin(value)

    def test_localhost_http_requires_explicit_lab_mode(self):
        with self.assertRaises(ContractError):
            AbsoluteOrigin("http://localhost:5000")
        self.assertEqual(
            AbsoluteOrigin("http://localhost:5000/", allow_http_localhost=True).value,
            "http://localhost:5000",
        )

    def test_request_headers_cannot_influence_configured_origin(self):
        origin = AbsoluteOrigin("https://media.example.test")
        request_headers = {
            "Host": "evil.example",
            "X-Forwarded-Host": "internal-moto:5000",
        }
        first = origin.join(release_key())
        second = origin.join(release_key())
        self.assertEqual(first, second)
        self.assertNotIn(request_headers["Host"], first)
        self.assertNotIn(request_headers["X-Forwarded-Host"], first)

    def test_site_and_media_origins_are_explicit_and_separate(self):
        origins = PublicOriginConfiguration.from_values(
            public_site_origin="https://www.example.test/",
            public_media_origin="https://media.example.test/assets/",
        )
        self.assertEqual(origins.public_site_origin.value, "https://www.example.test")
        self.assertTrue(origins.media_url(release_key()).startswith("https://media.example.test/"))
        with self.assertRaises(ContractError):
            origins.media_url(private_original_key("tenant-a", SOURCE_CHECKSUM, "png"))


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "separate-journal" / "deny.jsonl"
        self.journal = DenyJournal(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_append_replay_and_deny_set(self):
        self.assertTrue(self.journal.append(deny_event()))
        self.assertEqual([item.event_id for item in self.journal.replay()], ["evt-1"])
        self.assertEqual(self.journal.deny_set(), {release_key()})

    def test_same_duplicate_is_idempotent_and_different_payload_is_rejected(self):
        event = deny_event()
        self.assertTrue(self.journal.append(event))
        self.assertFalse(self.journal.append(event))
        with self.assertRaises(DuplicateEventConflict):
            self.journal.append(replace(event, reason_code="different"))

    def test_replay_is_repeatable_and_has_no_update_or_delete_api(self):
        self.journal.append(deny_event())
        self.assertEqual(self.journal.replay(), self.journal.replay())
        self.assertFalse(hasattr(self.journal, "update"))
        self.assertFalse(hasattr(self.journal, "delete"))

    def test_missing_and_corrupt_journal_fail_closed(self):
        with self.assertRaises(JournalUnavailable):
            self.journal.replay()
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not-json}\n", encoding="utf-8")
        with self.assertRaises(JournalCorrupt):
            self.journal.replay()

    def test_authorized_release_does_not_erase_old_denial(self):
        self.journal.append(deny_event())
        r2 = release_key(2)
        self.journal.append(
            JournalEvent(
                event_id="evt-r2",
                tenant="tenant-a",
                public_key=r2,
                artifact_checksum=ARTIFACT_CHECKSUM,
                source_checksum=SOURCE_CHECKSUM,
                timestamp="2026-07-31T12:05:00Z",
                action="authorized_release",
                reason_code="authorized",
                principal="phase3b2-test",
                previous_release_key=release_key(),
                new_release_key=r2,
            )
        )
        self.assertEqual(self.journal.deny_set(), {release_key()})


class PurgeTests(unittest.TestCase):
    def test_cache_remains_stale_until_idempotent_purge(self):
        cache = CacheSimulator()
        provider = RecordingPurgeProvider(cache)
        target = "https://media.example.test/public/tenant-a/r1/image.webp"
        cache.seed(target, b"stale")
        self.assertEqual(cache.get(target), b"stale")
        first = provider.purge(target)
        second = provider.purge(target)
        self.assertTrue(first.purged)
        self.assertFalse(cache.contains(target))
        self.assertTrue(second.idempotent_replay)
        self.assertEqual(first.request_id, second.request_id)

    def test_purge_failure_reports_retryability_and_retry_succeeds(self):
        cache = CacheSimulator()
        provider = RecordingPurgeProvider(cache)
        target = "https://media.example.test/public/tenant-a/r1/image.webp"
        cache.seed(target, b"stale")
        provider.fail_next(target, error="timeout", retryable=True)
        failure = provider.purge(target)
        success = provider.purge(target)
        self.assertEqual(failure.status, "failed")
        self.assertTrue(failure.retryable)
        self.assertEqual(success.status, "success")
        self.assertFalse(cache.contains(target))


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.renderer = DeterministicRenderer()
        self.config = '{"fit":"cover","format":"webp"}'
        self.regeneration = make_regeneration_backup(
            SOURCE_BYTES,
            canonical_render_config=self.config,
        )
        self.expected = self.renderer.render(SOURCE_BYTES, self.regeneration.metadata)
        self.direct = make_direct_backup(SOURCE_BYTES, self.expected)

    def test_direct_and_regeneration_strategies_are_measured_and_byte_identical(self):
        direct_bytes, direct = restore_direct(self.direct)
        regenerated_bytes, regenerated = restore_regenerated(
            self.regeneration,
            self.renderer,
            expected_rendition=self.expected,
        )
        self.assertEqual(direct_bytes, regenerated_bytes)
        self.assertTrue(direct.byte_identical)
        self.assertTrue(regenerated.byte_identical)
        self.assertGreater(direct.object_count, regenerated.object_count)
        self.assertFalse(direct.processing_version_required)
        self.assertTrue(regenerated.processing_version_required)

    def test_missing_rendition_and_missing_original_are_rejected(self):
        missing_rendition = replace(
            self.direct,
            objects={"private-original": SOURCE_BYTES},
            checksums={"private-original": SOURCE_CHECKSUM},
        )
        with self.assertRaises(BackupError):
            restore_direct(missing_rendition)
        missing_original = replace(self.regeneration, objects={}, checksums={})
        with self.assertRaises(BackupError):
            restore_regenerated(missing_original, self.renderer, expected_rendition=self.expected)

    def test_bad_checksum_unknown_version_partial_and_unavailable_restore_are_rejected(self):
        corrupt = replace(
            self.direct,
            objects={**self.direct.objects, "active-public-rendition": b"corrupt"},
        )
        with self.assertRaises(BackupError):
            restore_direct(corrupt)
        unknown = replace(
            self.regeneration,
            metadata={**self.regeneration.metadata, "processing_version": "missing-version"},
        )
        with self.assertRaises(BackupError):
            restore_regenerated(unknown, self.renderer, expected_rendition=self.expected)
        with self.assertRaises(StorageUnavailable):
            restore_direct(self.direct, storage_available=False)
        with self.assertRaises(StorageUnavailable):
            restore_regenerated(
                self.regeneration,
                self.renderer,
                expected_rendition=self.expected,
                storage_available=False,
            )


class S3StorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_moto(ENDPOINT)
        cls.s3 = S3Lab(endpoint=ENDPOINT)
        cls.s3.provision()

    def test_separate_django_aliases_preserve_default_and_staticfiles(self):
        from django.core.files.base import ContentFile
        from django.core.files.storage import storages

        default = storages["default"]
        name = default.save("sentinel/import-export.txt", ContentFile(b"default"))
        self.assertTrue(default.exists(name))
        self.assertEqual(default.__class__.__name__, "FileSystemStorage")
        self.assertEqual(storages["staticfiles"].__class__.__name__, "StaticFilesStorage")
        self.assertNotEqual(
            storages["image_originals_private"].bucket_name,
            storages["image_renditions_public"].bucket_name,
        )

    def test_private_original_is_immutable_and_anonymous_access_is_denied(self):
        key = private_original_key("tenant-a", SOURCE_CHECKSUM, "png")
        first = self.s3.save_alias_immutable(
            "image_originals_private", key, SOURCE_BYTES, content_type="image/png"
        )
        second = self.s3.save_alias_immutable(
            "image_originals_private", key, SOURCE_BYTES, content_type="image/png"
        )
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertTrue(self.s3.anonymous_denied(self.s3.private_bucket, key))
        with self.assertRaises(ImmutableConflict):
            self.s3.save_alias_immutable(
                "image_originals_private", key, b"different", content_type="image/png"
            )

    def test_public_rendition_is_anonymous_and_has_explicit_headers(self):
        key = release_key(11)
        stored = self.s3.save_alias_immutable(
            "image_renditions_public", key, ARTIFACT_BYTES, content_type="image/webp"
        )
        self.assertEqual(self.s3.anonymous_get(self.s3.public_bucket, key), ARTIFACT_BYTES)
        head = self.s3.client.head_object(Bucket=self.s3.public_bucket, Key=key)
        self.assertEqual(head["ContentType"], "image/webp")
        self.assertEqual(head["CacheControl"], PUBLIC_CACHE_CONTROL)
        self.assertEqual(stored.checksum, ARTIFACT_CHECKSUM)

    def test_duplicate_public_key_different_bytes_and_alias_confusion_are_rejected(self):
        key = release_key(12)
        self.s3.save_alias_immutable(
            "image_renditions_public", key, ARTIFACT_BYTES, content_type="image/webp"
        )
        with self.assertRaises(ImmutableConflict):
            self.s3.save_alias_immutable(
                "image_renditions_public", key, b"different", content_type="image/webp"
            )
        with self.assertRaises(ContractError):
            self.s3.save_alias_immutable(
                "image_originals_private", release_key(13), ARTIFACT_BYTES, content_type="image/webp"
            )

    def test_partial_upload_checksum_mismatch_wrong_content_type_and_missing_object(self):
        partial = "renditions/partial/probe.webp"
        self.s3.client.put_object(
            Bucket=self.s3.private_bucket,
            Key=partial,
            Body=b"partial",
            ContentType="image/webp",
            Metadata={"upload-state": "partial", "sha256": checksum_bytes(b"complete")},
        )
        with self.assertRaises(ContractError):
            self.s3.verified_read(self.s3.private_bucket, partial, checksum_bytes(b"partial"))
        complete = "renditions/checksum/probe.webp"
        self.s3.client.put_object(
            Bucket=self.s3.private_bucket,
            Key=complete,
            Body=b"actual",
            ContentType="image/webp",
            Metadata={"upload-state": "complete"},
        )
        with self.assertRaises(ContractError):
            self.s3.verified_read(self.s3.private_bucket, complete, checksum_bytes(b"expected"))
        with self.assertRaises(ContractError):
            self.s3.save_alias_immutable(
                "image_renditions_public",
                release_key(14),
                ARTIFACT_BYTES,
                content_type="image/png",
            )
        self.assertFalse(self.s3.exists(self.s3.public_bucket, "public/tenant-a/missing.webp"))
        from storage_lab.scenario import resolve_public

        with tempfile.TemporaryDirectory() as temporary:
            journal = DenyJournal(Path(temporary) / "deny.jsonl")
            journal.initialize()
            missing = AppState(
                "tenant-a",
                "actor-42",
                "public/tenant-a/actor-42/r99/missing.webp",
                None,
                99,
            )
            result = resolve_public(
                missing,
                journal=journal,
                s3=self.s3,
                origin=AbsoluteOrigin("https://media.example.test"),
            )
        self.assertEqual(result["reason"], "rendition_missing")

    def test_private_versioning_records_moto_gap_and_domain_boundary_denies_history(self):
        key = "versioning/private-probe.webp"
        first = self.s3.client.put_object(Bucket=self.s3.private_bucket, Key=key, Body=b"v1")[
            "VersionId"
        ]
        second = self.s3.client.put_object(Bucket=self.s3.private_bucket, Key=key, Body=b"v2")[
            "VersionId"
        ]
        self.s3.delete(self.s3.private_bucket, key)
        versions = self.s3.object_versions(self.s3.private_bucket, key)
        self.assertEqual(len(versions["versions"]), 2)
        self.assertEqual(len(versions["delete_markers"]), 1)
        self.assertNotEqual(first, second)
        old = self.s3.client.get_object(
            Bucket=self.s3.private_bucket, Key=key, VersionId=first
        )["Body"].read()
        self.assertEqual(old, b"v1")
        # Moto 5.2.2 does not fully enforce the absence of a public policy when
        # an unsigned request supplies VersionId. Preserve this observation;
        # enforce the intended domain contract with an explicit recording fake.
        self.assertEqual(
            self.s3.anonymous_get(self.s3.private_bucket, key, version_id=first), b"v1"
        )
        boundary = RecordingPrivateAccessBoundary(self.s3)
        with self.assertRaises(PrivateAccessDenied):
            boundary.get(key, principal="anonymous", version_id=first)
        self.assertEqual(boundary.get(key, principal="storage-admin", version_id=first), b"v1")

    def test_public_versioned_history_is_anonymously_reachable_in_emulator(self):
        key = "versioning/public-probe.webp"
        first = self.s3.put_public_versioned(key, b"v1", content_type="image/webp")
        second = self.s3.put_public_versioned(key, b"v2", content_type="image/webp")
        self.assertNotEqual(first, second)
        self.assertEqual(
            self.s3.anonymous_get(self.s3.versioned_public_bucket, key, version_id=first), b"v1"
        )

    def test_retry_delete_and_restore_are_idempotent(self):
        key = release_key(15)
        self.s3.save_alias_immutable(
            "image_renditions_public", key, ARTIFACT_BYTES, content_type="image/webp"
        )
        self.s3.delete(self.s3.public_bucket, key)
        self.s3.delete(self.s3.public_bucket, key)
        restored = self.s3.save_alias_immutable(
            "image_renditions_public", key, ARTIFACT_BYTES, content_type="image/webp"
        )
        retry = self.s3.save_alias_immutable(
            "image_renditions_public", key, ARTIFACT_BYTES, content_type="image/webp"
        )
        self.assertTrue(restored.created)
        self.assertFalse(retry.created)

    def test_delete_before_deny_event_still_blocks_reintroduced_old_snapshot(self):
        from storage_lab.scenario import reconcile

        key = release_key(16)
        self.s3.save_alias_immutable(
            "image_renditions_public", key, ARTIFACT_BYTES, content_type="image/webp"
        )
        state_snapshot = AppState("tenant-a", "actor-42", key, "renditions/a.webp", 16)
        self.s3.delete(self.s3.public_bucket, key)
        with tempfile.TemporaryDirectory() as temporary:
            journal = DenyJournal(Path(temporary) / "deny.jsonl")
            journal.append(deny_event("evt-delete-first", key))
            self.s3.save_alias_immutable(
                "image_renditions_public", key, ARTIFACT_BYTES, content_type="image/webp"
            )
            reconciled, actions = reconcile(state_snapshot, journal=journal, s3=self.s3)
        self.assertIsNone(reconciled.public_key)
        self.assertIn(f"blocked:{key}", actions)
        self.assertFalse(self.s3.exists(self.s3.public_bucket, key))


class ResolverAndFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = DenyJournal(self.root / "journal.jsonl")
        self.journal.initialize()
        self.state = AppState("tenant-a", "actor-42", release_key(), "renditions/artifact.webp", 1)
        self.origin = AbsoluteOrigin("https://media.example.test")

    def tearDown(self):
        self.temp.cleanup()

    def test_storage_unavailable_returns_static_fallback_without_storage_database_or_renderer(self):
        from storage_lab.scenario import resolve_public, static_fallback_bytes

        result = resolve_public(self.state, journal=self.journal, s3=None, origin=self.origin)
        self.assertEqual(result["kind"], "static_fallback")
        for variant in ("square", "landscape", "share"):
            with self.subTest(variant=variant):
                self.assertTrue(static_fallback_bytes(variant).startswith(b"\x89PNG"))

        def failing_dynamic_renderer():
            raise RuntimeError("renderer unavailable")

        with self.assertRaises(RuntimeError):
            failing_dynamic_renderer()
        self.assertEqual(
            resolve_public(self.state, journal=self.journal, s3=None, origin=self.origin)["kind"],
            "static_fallback",
        )

    def test_missing_state_and_unfinished_or_corrupt_reconciliation_return_fallback(self):
        from storage_lab.scenario import resolve_public

        no_state = replace(self.state, public_key=None)
        self.assertEqual(
            resolve_public(no_state, journal=self.journal, s3=None, origin=self.origin)["reason"],
            "state_missing",
        )
        missing_journal = DenyJournal(self.root / "missing.jsonl")
        self.assertEqual(
            resolve_public(self.state, journal=missing_journal, s3=None, origin=self.origin)["reason"],
            "journal_unavailable",
        )
        corrupt = DenyJournal(self.root / "corrupt.jsonl")
        corrupt.path.write_text("bad\n", encoding="utf-8")
        self.assertEqual(
            resolve_public(self.state, journal=corrupt, s3=None, origin=self.origin)["reason"],
            "journal_unavailable",
        )

    def test_old_snapshot_is_overridden_by_newer_deny_event(self):
        from storage_lab.scenario import resolve_public

        snapshot = self.state.as_dict()
        self.journal.append(deny_event())
        restored = AppState.from_dict(snapshot)
        result = resolve_public(restored, journal=self.journal, s3=None, origin=self.origin)
        self.assertEqual(result["reason"], "release_denied")


class RuntimeIsolationTests(unittest.TestCase):
    def test_storage_spike_is_not_imported_by_crm_or_config(self):
        resolved = Path(__file__).resolve()
        repo_root = next(
            (
                parent
                for parent in resolved.parents
                if (parent / "crm").is_dir() and (parent / "config").is_dir()
            ),
            None,
        )
        if repo_root is None:
            self.assertFalse(Path("/lab/crm").exists())
            self.assertFalse(Path("/lab/config").exists())
            return
        occurrences = []
        for runtime_root in (repo_root / "crm", repo_root / "config"):
            for path in runtime_root.rglob("*.py"):
                content = path.read_text(encoding="utf-8")
                if "storage_lab" in content or "spikes.storage_pipeline" in content:
                    occurrences.append(str(path.relative_to(repo_root)))
        self.assertEqual(occurrences, [])
        root_requirements = (repo_root / "requirements.txt").read_text(encoding="utf-8").lower()
        for dependency in ("django-storages", "boto3", "moto"):
            self.assertNotIn(dependency, root_requirements)


class ZFullScenarioTests(unittest.TestCase):
    def test_t0_through_t5_blocks_r1_after_old_restore_and_releases_r2(self):
        from storage_lab.scenario import execute_takedown_restore_scenario

        reset_moto(ENDPOINT)
        with tempfile.TemporaryDirectory() as temporary:
            evidence = execute_takedown_restore_scenario(Path(temporary), endpoint=ENDPOINT)
        stages = evidence["takedown_restore"]
        self.assertTrue(stages["T0"]["r1_anonymous"])
        self.assertEqual(stages["T0"]["journal_events"], 0)
        self.assertTrue(stages["T2"]["stale_before_purge"])
        self.assertTrue(stages["T2"]["r1_not_delivered"])
        self.assertTrue(stages["T3"]["r1_reintroduced"])
        self.assertTrue(stages["T4"]["r1_denied"])
        self.assertTrue(stages["T4"]["r1_origin_blocked"])
        self.assertTrue(stages["T5"]["r2_differs_from_r1"])
        self.assertTrue(stages["T5"]["r1_still_denied"])
        self.assertEqual(stages["T5"]["resolver"]["kind"], "public")
        self.assertFalse(evidence["origin_contract"]["internal_endpoint_leaked"])


if __name__ == "__main__":
    unittest.main()

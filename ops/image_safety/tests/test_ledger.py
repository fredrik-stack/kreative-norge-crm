from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock, patch

from image_safety.anchor import (
    AnchorBackendError,
    BorgAnchorConfig,
    BorgAnchorBackend,
    anchor_current_head,
    restore_latest_anchor,
)
from image_safety.ledger import (
    EventConflictError,
    InvalidLedgerError,
    InvalidTransitionError,
    PublicImageSafetyLedger,
    ReservationRendition,
)


REPOSITORY_ID = "a" * 64
OTHER_REPOSITORY_ID = "b" * 64


class MemoryAnchor:
    def __init__(self, repository_id: str = REPOSITORY_ID):
        self.repository_id = repository_id
        self.archives: dict[str, bytes] = {}
        self.fail_create = False

    def verified_repository_id(self) -> str:
        return self.repository_id

    def read(self, archive_name: str) -> bytes | None:
        return self.archives.get(archive_name)

    def create(self, archive_name: str, content: bytes) -> None:
        if self.fail_create:
            raise AnchorBackendError("synthetic network failure")
        if archive_name in self.archives:
            raise AssertionError("create must not overwrite")
        self.archives[archive_name] = content

    def list_archives(self, prefix: str) -> list[str]:
        return sorted(name for name in self.archives if name.startswith(prefix))


class LedgerFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.path = self.root / "state" / "ledger.sqlite3"
        self.ledger = PublicImageSafetyLedger(self.path)
        self.ledger.initialize(ledger_id="11111111-1111-4111-8111-111111111111")
        self.release_id = "22222222-2222-4222-8222-222222222222"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def renditions(prefix: str = "one") -> tuple[ReservationRendition, ...]:
        return (
            ReservationRendition("square", "webp", f"tenants/1/{prefix}/square.webp", "a" * 64),
            ReservationRendition("landscape", "png", f"tenants/1/{prefix}/landscape.png", "b" * 64),
            ReservationRendition("share", "jpeg", f"tenants/1/{prefix}/share.jpg", "c" * 64),
        )

    def reserve(self, *, event_id: str = "reservation.one", release_id: str | None = None):
        return self.ledger.reserve_release(
            event_id=event_id,
            release_id=release_id or self.release_id,
            tenant_id=1,
            organization_id=2,
            selection_id=3,
            selection_revision=4,
            rendition_set_id=5,
            renditions=self.renditions(),
        )

    def anchor(self, backend: MemoryAnchor | None = None) -> MemoryAnchor:
        backend = backend or MemoryAnchor()
        anchor_current_head(
            self.ledger, backend, expected_repository_id=REPOSITORY_ID
        )
        return backend


class LedgerContractTests(LedgerFixture):
    def test_reservation_generates_canonical_keys_and_binding_snapshot(self):
        event = self.reserve()

        state = self.ledger.release_state(self.release_id)
        self.assertEqual(event.sequence, 1)
        self.assertEqual(state["state"], "reserved")
        self.assertEqual(state["reservation"]["tenant_id"], 1)
        self.assertEqual(state["reservation"]["organization_id"], 2)
        self.assertEqual(state["reservation"]["selection_id"], 3)
        self.assertEqual(state["reservation"]["selection_revision"], 4)
        self.assertEqual(
            state["reservation"]["variants"]["share"]["public_storage_key"],
            f"releases/{self.release_id}/share.jpg",
        )

    def test_reservation_input_cannot_supply_public_keys(self):
        with self.assertRaises(TypeError):
            ReservationRendition(
                "square", "webp", "artifact.webp", "a" * 64,
                public_storage_key="caller/key.webp",
            )

    def test_same_event_and_payload_is_retry_but_different_payload_conflicts(self):
        first = self.reserve()
        second = self.reserve()

        self.assertFalse(first.idempotent_retry)
        self.assertTrue(second.idempotent_retry)
        with self.assertRaises(EventConflictError):
            self.ledger.reserve_release(
                event_id="reservation.one",
                release_id=self.release_id,
                tenant_id=9,
                organization_id=2,
                selection_id=3,
                selection_revision=4,
                rendition_set_id=5,
                renditions=self.renditions(),
            )

    def test_release_and_keys_cannot_be_reserved_as_a_new_event(self):
        self.reserve()
        with self.assertRaises(InvalidTransitionError):
            self.reserve(event_id="reservation.two")

    def test_terminal_releases_never_activate(self):
        self.reserve()
        self.ledger.deny_release(
            event_id="deny.one", release_id=self.release_id, reason_code="operator_deny"
        )

        with self.assertRaises(InvalidTransitionError):
            self.ledger.activate_release(
                event_id="activate.after.deny", release_id=self.release_id
            )
        self.assertEqual(self.ledger.release_state(self.release_id)["state"], "denied")

    def test_retired_release_is_also_terminal(self):
        self.reserve()
        self.ledger.activate_release(event_id="activate.one", release_id=self.release_id)
        self.ledger.retire_release(
            event_id="retire.one", release_id=self.release_id, reason_code="replacement"
        )
        with self.assertRaises(InvalidTransitionError):
            self.ledger.activate_release(
                event_id="activate.after.retire", release_id=self.release_id
            )

    def test_database_triggers_reject_event_update_and_delete(self):
        self.reserve()
        connection = sqlite3.connect(self.path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE ledger_events SET event_id = 'changed'")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM ledger_events")
        finally:
            connection.close()

    def test_concurrent_same_event_has_one_append_and_one_retry(self):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker():
            try:
                barrier.wait()
                results.append(self.reserve())
            except Exception as error:  # pragma: no cover - asserted below
                errors.append(error)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(sorted(item.idempotent_retry for item in results), [False, True])
        self.assertEqual(self.ledger.head().sequence, 1)

    def test_sqlite_transaction_failure_rolls_back_event_and_read_model(self):
        original = self.ledger._apply_to_database

        def fail_after_state(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("synthetic process death boundary")

        with patch.object(self.ledger, "_apply_to_database", side_effect=fail_after_state):
            with self.assertRaises(RuntimeError):
                self.reserve()
        self.assertEqual(self.ledger.head().sequence, 0)
        self.assertIsNone(self.ledger.release_state(self.release_id))


class HealthAndReplayTests(LedgerFixture):
    def test_health_requires_current_verified_anchor(self):
        self.reserve()
        health = self.ledger.health(expected_repository_id=REPOSITORY_ID)
        self.assertFalse(health.ready)
        self.assertEqual(health.code, "anchor_missing")

        backend = self.anchor()
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)
        self.ledger.activate_release(event_id="activate.one", release_id=self.release_id)
        stale = self.ledger.health(expected_repository_id=REPOSITORY_ID)
        self.assertFalse(stale.ready)
        self.assertEqual(stale.code, "anchor_cursor_stale")
        self.anchor(backend)
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)

    def test_repository_identity_mismatch_fails_closed(self):
        self.reserve()
        self.anchor()
        health = self.ledger.health(expected_repository_id=OTHER_REPOSITORY_ID)
        self.assertFalse(health.ready)
        self.assertEqual(health.code, "repository_identity_mismatch")

    def test_stale_cursor_and_read_model_mismatch_fail_closed_then_rebuild(self):
        self.reserve()
        backend = self.anchor()
        connection = sqlite3.connect(self.path)
        connection.execute("UPDATE read_cursor SET event_sequence = 0")
        connection.commit()
        connection.close()
        self.assertEqual(
            self.ledger.health(expected_repository_id=REPOSITORY_ID).code,
            "read_cursor_stale",
        )
        self.ledger.rebuild()
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)

        connection = sqlite3.connect(self.path)
        connection.execute("UPDATE release_state SET state = 'active'")
        connection.commit()
        connection.close()
        self.assertEqual(
            self.ledger.health(expected_repository_id=REPOSITORY_ID).code,
            "read_model_mismatch",
        )
        self.ledger.rebuild()
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)
        self.assertIsNotNone(backend)

    def test_corrupt_event_chain_and_unknown_schema_fail_closed(self):
        self.reserve()
        self.anchor()
        connection = sqlite3.connect(self.path)
        connection.execute("DROP TRIGGER ledger_events_no_update")
        connection.execute("UPDATE ledger_events SET payload_sha256 = ?", ("f" * 64,))
        connection.commit()
        connection.close()
        self.assertEqual(
            self.ledger.health(expected_repository_id=REPOSITORY_ID).code,
            "ledger_invalid",
        )

        other_path = self.root / "unknown.sqlite3"
        other = PublicImageSafetyLedger(other_path)
        other.initialize()
        connection = sqlite3.connect(other_path)
        connection.execute("PRAGMA user_version = 99")
        connection.close()
        self.assertEqual(
            other.health(expected_repository_id=REPOSITORY_ID).code, "ledger_invalid"
        )

    def test_missing_and_non_sqlite_files_fail_closed(self):
        missing = PublicImageSafetyLedger(self.root / "missing.sqlite3")
        self.assertEqual(
            missing.health(expected_repository_id=REPOSITORY_ID).code, "ledger_missing"
        )
        corrupt_path = self.root / "corrupt.sqlite3"
        corrupt_path.write_bytes(b"not sqlite")
        self.assertEqual(
            PublicImageSafetyLedger(corrupt_path)
            .health(expected_repository_id=REPOSITORY_ID)
            .code,
            "ledger_invalid",
        )


class AnchorCrashAndRestoreTests(LedgerFixture):
    def test_local_commit_remote_failure_leaves_not_ready_and_retry_repairs(self):
        self.reserve()
        backend = MemoryAnchor()
        backend.fail_create = True
        with self.assertRaises(AnchorBackendError):
            self.anchor(backend)
        self.assertEqual(self.ledger.head().sequence, 1)
        self.assertFalse(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)

        backend.fail_create = False
        self.anchor(backend)
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)

    def test_remote_success_local_ack_failure_is_idempotently_recovered(self):
        self.reserve()
        backend = MemoryAnchor()

        def die_after_remote_write():
            raise RuntimeError("synthetic death before local receipt")

        with self.assertRaises(RuntimeError):
            anchor_current_head(
                self.ledger,
                backend,
                expected_repository_id=REPOSITORY_ID,
                after_remote_write_hook=die_after_remote_write,
            )
        self.assertEqual(len(backend.archives), 1)
        result = anchor_current_head(
            self.ledger, backend, expected_repository_id=REPOSITORY_ID
        )
        self.assertTrue(result.reused_archive)
        self.assertEqual(len(backend.archives), 1)
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)

    def test_old_database_loses_to_newer_remote_ledger_on_restore(self):
        self.reserve()
        self.ledger.activate_release(event_id="activate.one", release_id=self.release_id)
        backend = self.anchor()
        old_database = self.root / "old-postgres-era-ledger.sqlite3"
        source_connection = sqlite3.connect(self.path)
        destination_connection = sqlite3.connect(old_database)
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
            source_connection.close()

        self.ledger.deny_release(
            event_id="deny.newer", release_id=self.release_id, reason_code="security_deny"
        )
        self.anchor(backend)
        self.assertEqual(
            PublicImageSafetyLedger(old_database).release_state(self.release_id)["state"],
            "active",
        )

        restored_path = self.root / "restored" / "ledger.sqlite3"
        restored_path.parent.mkdir()
        restored = restore_latest_anchor(
            backend,
            expected_repository_id=REPOSITORY_ID,
            destination=restored_path,
            recovery_mode="clean",
        )
        self.assertEqual(restored.release_state(self.release_id)["state"], "denied")
        self.assertTrue(restored.health(expected_repository_id=REPOSITORY_ID).ready)

    def test_replay_and_restore_require_no_postgres_or_django(self):
        self.reserve()
        backend = self.anchor()
        restored_path = self.root / "standalone.sqlite3"
        restored = restore_latest_anchor(
            backend,
            expected_repository_id=REPOSITORY_ID,
            destination=restored_path,
            recovery_mode="clean",
        )
        restored.rebuild()
        self.assertEqual(restored.bundle_bytes(), self.ledger.bundle_bytes())

    def test_incident_restore_rejects_stale_visible_head_after_newest_tombstone(self):
        self.reserve()
        backend = self.anchor()
        self.ledger.activate_release(event_id="activate.one", release_id=self.release_id)
        self.anchor(backend)
        self.ledger.deny_release(
            event_id="deny.newest", release_id=self.release_id, reason_code="security_deny"
        )
        self.anchor(backend)
        authoritative_head = self.ledger.head()
        newest_archive = max(
            backend.archives,
            key=lambda name: int(name.split("-")[-2]),
        )
        newest_bytes = backend.archives.pop(newest_archive)

        visible_names = backend.list_archives("image-safety-")
        self.assertNotIn(newest_archive, visible_names)
        stale_destination = self.root / "incident-stale.sqlite3"
        with self.assertRaisesRegex(
            AnchorBackendError, "authoritative incident recovery evidence"
        ):
            restore_latest_anchor(
                backend,
                expected_repository_id=REPOSITORY_ID,
                destination=stale_destination,
                recovery_mode="incident-recovered",
                expected_authoritative_cursor=authoritative_head.sequence,
                expected_authoritative_event_hash=authoritative_head.event_hash,
            )
        self.assertFalse(stale_destination.exists())

        clean_destination = self.root / "clean-visible.sqlite3"
        clean_visible = restore_latest_anchor(
            backend,
            expected_repository_id=REPOSITORY_ID,
            destination=clean_destination,
            recovery_mode="clean",
        )
        self.assertEqual(clean_visible.release_state(self.release_id)["state"], "active")

        backend.archives[newest_archive] = newest_bytes
        recovered_destination = self.root / "incident-recovered.sqlite3"
        recovered = restore_latest_anchor(
            backend,
            expected_repository_id=REPOSITORY_ID,
            destination=recovered_destination,
            recovery_mode="incident-recovered",
            expected_authoritative_cursor=authoritative_head.sequence,
            expected_authoritative_event_hash=authoritative_head.event_hash,
        )
        recovered.rebuild()
        self.assertEqual(recovered.head(), authoritative_head)
        self.assertEqual(recovered.release_state(self.release_id)["state"], "denied")
        self.assertTrue(recovered.health(expected_repository_id=REPOSITORY_ID).ready)

    def test_incident_restore_requires_independent_authoritative_head(self):
        self.reserve()
        backend = self.anchor()
        destination = self.root / "missing-incident-evidence.sqlite3"

        with self.assertRaisesRegex(AnchorBackendError, "authoritative cursor"):
            restore_latest_anchor(
                backend,
                expected_repository_id=REPOSITORY_ID,
                destination=destination,
                recovery_mode="incident-recovered",
            )
        self.assertFalse(destination.exists())

    def test_tampered_remote_archive_is_a_hard_conflict(self):
        self.reserve()
        backend = self.anchor()
        name = next(iter(backend.archives))
        decoded = json.loads(backend.archives[name])
        decoded["ledger_id"] = str(uuid.uuid4())
        backend.archives[name] = json.dumps(decoded).encode()
        with self.assertRaises(Exception):
            self.anchor(backend)


class CredentialAndPlacementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.secrets = []
        for name in ("writer", "known_hosts", "passphrase"):
            path = self.root / name
            path.write_text("synthetic-only\n", encoding="utf-8")
            path.chmod(0o600)
            self.secrets.append(path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def config(self) -> BorgAnchorConfig:
        return BorgAnchorConfig(
            repository="ssh://writer@example.invalid:23/./public-image-safety",
            expected_repository_id=REPOSITORY_ID,
            ssh_key=self.secrets[0],
            known_hosts=self.secrets[1],
            passphrase_file=self.secrets[2],
            state_root=self.root / "state",
            required_owner_uid=os.getuid(),
        )

    def test_installed_entrypoint_reports_expected_errors_without_traceback(self):
        repository_root = Path(__file__).resolve().parents[3]
        install_root = self.root / "installed"
        shutil.copytree(repository_root / "image_safety", install_root / "image_safety")
        shutil.copy2(repository_root / "ops/image_safety/run.py", install_root / "run.py")

        result = subprocess.run(
            [sys.executable, "-I", str(install_root / "run.py"), "health"],
            env={"IMAGE_SAFETY_LEDGER_PATH": str(self.root / "missing.sqlite3")},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("image-safety: ERROR:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_private_dedicated_credential_paths_are_accepted(self):
        self.config().validate()

    def test_group_readable_secret_and_state_symlink_are_rejected(self):
        self.secrets[0].chmod(0o640)
        with self.assertRaises(AnchorBackendError):
            self.config().validate()
        self.secrets[0].chmod(0o600)
        target = self.root / "target"
        target.mkdir()
        (self.root / "state").symlink_to(target)
        with self.assertRaises(AnchorBackendError):
            self.config().validate()

    def test_compose_and_images_do_not_receive_ledger_or_borg_credential(self):
        repository_root = Path(__file__).resolve().parents[3]
        compose = (repository_root / "docker-compose.staging.yml").read_text(
            encoding="utf-8"
        )
        dockerfiles = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (repository_root / "Dockerfile", repository_root / "Dockerfile.web")
        )
        for forbidden in (
            "kreative-norge-image-safety",
            "IMAGE_SAFETY_LEDGER_PATH",
            "IMAGE_SAFETY_BORG_SSH_KEY",
            "borg-passphrase",
        ):
            self.assertNotIn(forbidden, compose)
            self.assertNotIn(forbidden, dockerfiles)

    def test_repository_bootstrap_requires_pending_identity_and_append_only(self):
        backend = object.__new__(BorgAnchorBackend)
        backend.config = SimpleNamespace(
            expected_repository_id="0" * 64,
            remote_path="borg-1.2",
            repository="ssh://writer@example.invalid:23/./public-image-safety",
        )
        backend._run = Mock(
            side_effect=(
                subprocess.CompletedProcess([], 0, b"borg 1.2.8\n", b""),
                subprocess.CompletedProcess([], 0, b"", b""),
                subprocess.CompletedProcess(
                    [], 0, json.dumps({"repository": {"id": REPOSITORY_ID}}).encode(), b""
                ),
            )
        )

        self.assertEqual(backend.initialize_repository(), REPOSITORY_ID)
        init_arguments = backend._run.call_args_list[1].args[0]
        self.assertIn("--append-only", init_arguments)
        self.assertIn("--encryption=repokey-blake2", init_arguments)
        self.assertIn("borg-1.2", init_arguments)

        backend.config.expected_repository_id = REPOSITORY_ID
        with self.assertRaises(AnchorBackendError):
            backend.initialize_repository()

    def test_supported_borg_versions_match_adr_008_contract(self):
        for output in (b"borg 1.2.8\n", b"borg 1.2.9\n", b"borg 1.2.10\n"):
            with self.subTest(output=output):
                backend = object.__new__(BorgAnchorBackend)
                backend._run = Mock(
                    return_value=subprocess.CompletedProcess([], 0, output, b"")
                )

                backend._validate_version()

    def test_unsupported_or_malformed_borg_versions_fail_closed(self):
        for output in (
            b"borg 1.2.7\n",
            b"borg 1.3.0\n",
            b"borg 2.0.0\n",
            b"borg 1.2.8rc1\n",
            b"borg 1.2\n",
            b"unknown\n",
            b"borg 01.2.8\n",
        ):
            with self.subTest(output=output):
                backend = object.__new__(BorgAnchorBackend)
                backend._run = Mock(
                    return_value=subprocess.CompletedProcess([], 0, output, b"")
                )

                with self.assertRaises(AnchorBackendError):
                    backend._validate_version()

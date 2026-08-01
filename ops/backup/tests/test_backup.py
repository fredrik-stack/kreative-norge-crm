#!/usr/bin/env python3
"""Synthetic tests for the prepared backup foundation; no server access required."""

from __future__ import annotations

import json
import hashlib
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ID = "a" * 64
OTHER_REPOSITORY_ID = "b" * 64
ARCHIVE = "kreative-norge-staging-20260801T023000Z"


FAKE_COMMAND = r'''#!/usr/bin/env python3
import hashlib
import json
import os
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
log = os.environ.get("FAKE_CALL_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(name + " " + " ".join(args) + "\n")

if name == "borg":
    if args == ["--version"]:
        print("borg " + os.environ.get("FAKE_BORG_VERSION", "1.2.8"))
        raise SystemExit(0)
    command = args[0] if args else ""
    if command == "info":
        if os.environ.get("FAKE_BORG_AUTH_FAIL") == "1" or os.environ.get("FAKE_BORG_UNAVAILABLE") == "1":
            raise SystemExit(2)
        print(json.dumps({"repository": {"id": os.environ.get("FAKE_REPOSITORY_ID", "a" * 64)}}))
        raise SystemExit(0)
    if command == "list":
        if "--json" in args:
            archives = [] if os.environ.get("FAKE_NO_ARCHIVES") == "1" else [{"name": os.environ.get("FAKE_ARCHIVE", "kreative-norge-staging-20260801T023000Z")}]
            print(json.dumps({"archives": archives}))
        else:
            print(os.environ.get("FAKE_MEMBER_LIST", ""), end="")
        raise SystemExit(0)
    if command == "extract" and "--stdout" not in args:
        staged = Path(args[-1])
        destination = Path.cwd() / staged
        destination.mkdir(parents=True, exist_ok=True)
        dump = b"synthetic-custom-format-dump\n"
        (destination / "database.dump").write_bytes(dump)
        checksum = hashlib.sha256(dump).hexdigest()
        (destination / "checksums.sha256").write_text(checksum + "  database.dump\n", encoding="utf-8")
        archive = os.environ.get("FAKE_ARCHIVE", "kreative-norge-staging-20260801T023000Z")
        (destination / "manifest.txt").write_text(
            "format_version=1\ndatabase_dump_sha256=" + checksum + "\npg_restore_verification=passed\nborg_archive=" + archive + "\nsample_path_token=\nsample_checksum=\n",
            encoding="utf-8",
        )
        raise SystemExit(0)
    failures = {
        "create": "FAKE_CREATE_FAIL",
        "check": "FAKE_CHECK_FAIL",
        "prune": "FAKE_PRUNE_FAIL",
        "compact": "FAKE_COMPACT_FAIL",
        "extract": "FAKE_EXTRACT_FAIL",
    }
    if os.environ.get(failures.get(command, "")) == "1":
        raise SystemExit(2)
    raise SystemExit(0)

if name == "docker":
    if args[:2] == ["compose", "version"]:
        print("Docker Compose version v2")
        raise SystemExit(0)
    if args and args[0] == "compose":
        if "ps" in args:
            service = args[-1]
            print("db-container" if service == "db" else "api-container")
            raise SystemExit(0)
        if "exec" in args:
            joined = " ".join(args)
            if "pg_database_size" in joined:
                print(os.environ.get("FAKE_DATABASE_SIZE", "1024"))
                raise SystemExit(0)
            if "pg_dump" in joined:
                if os.environ.get("FAKE_DUMP_FAIL") == "1":
                    raise SystemExit(2)
                sys.stdout.buffer.write(b"synthetic-custom-format-dump\n")
                raise SystemExit(0)
            if "pg_restore" in joined:
                if os.environ.get("FAKE_DUMP_VERIFY_FAIL") == "1":
                    raise SystemExit(2)
                raise SystemExit(0)
            if "postgres --version" in joined:
                print("postgres (PostgreSQL) 16.9")
                raise SystemExit(0)
        raise SystemExit(0)
    if args and args[0] == "run":
        if "pg_restore" in args:
            raise SystemExit(1 if os.environ.get("FAKE_RESTORE_LIST_FAIL") == "1" else 0)
        print("restore-container-id")
        raise SystemExit(0)
    if args and args[0] == "exec":
        joined = " ".join(args)
        if "api-container test -d" in joined:
            # Current container-layer media is deliberately absent in the default fixture.
            raise SystemExit(1)
        if "pg_isready" in joined or "pg_restore" in joined:
            raise SystemExit(0)
        if "to_regclass" in joined:
            print("t")
            raise SystemExit(0)
        if "SELECT count" in joined:
            print("0")
            raise SystemExit(0)
        raise SystemExit(0)
    if args and args[0] == "rm":
        raise SystemExit(0)
    raise SystemExit(0)

if name == "git":
    if "rev-parse" in args:
        print("1" * 40)
    raise SystemExit(0)

if name == "ssh-keygen":
    raise SystemExit(1 if os.environ.get("FAKE_HOST_KEY_MISSING") == "1" else 0)

if name == "flock":
    raise SystemExit(1 if os.environ.get("FAKE_LOCKED") == "1" else 0)

if name == "df":
    available = os.environ.get("FAKE_AVAILABLE_BYTES", "999999999999")
    print("Filesystem 1-blocks Used Available Capacity Mounted on")
    print("synthetic 999999999999 1 " + available + " 1% /tmp")
    raise SystemExit(0)

raise SystemExit("unsupported fake command: " + name)
'''


class BackupFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        dispatcher = self.fake_bin / "fake-command"
        dispatcher.write_text(FAKE_COMMAND, encoding="utf-8")
        dispatcher.chmod(dispatcher.stat().st_mode | stat.S_IXUSR)
        for command in ("borg", "docker", "git", "ssh-keygen", "flock", "df"):
            (self.fake_bin / command).symlink_to(dispatcher)

        self.app = self.root / "app"
        (self.app / ".git").mkdir(parents=True)
        self.compose = self.app / "docker-compose.staging.yml"
        self.compose.write_text("services: {}\n", encoding="utf-8")
        self.compose_env = self.app / ".env"
        self.compose_env.write_text("POSTGRES_DB=synthetic\n", encoding="utf-8")
        self.secret = self.root / "borg-passphrase"
        self.key = self.root / "storage-box-key"
        self.known_hosts = self.root / "known_hosts"
        for file_path in (self.secret, self.key, self.known_hosts):
            file_path.write_text("synthetic-test-only\n", encoding="utf-8")
            file_path.chmod(0o600)
        self.work = self.root / "work"
        self.status = self.root / "status.json"
        self.lock = self.root / "backup.lock"
        self.config = self.root / "backup.env"
        self.config.write_text(
            textwrap.dedent(
                f"""\
                BACKUP_ENVIRONMENT=staging
                APP_ROOT={self.app}
                COMPOSE_FILE={self.compose}
                COMPOSE_ENV_FILE={self.compose_env}
                DATABASE_SERVICE=db
                API_SERVICE=api
                WORK_ROOT={self.work}
                STATUS_FILE={self.status}
                LOCK_FILE={self.lock}
                RESTORE_GATE_FILE={self.root / 'restore-smoke.ok'}
                BORG_BIN=borg
                BORG_REPOSITORY=ssh://u@box:23/./repo
                BORG_REPOSITORY_ID={REPOSITORY_ID}
                BORG_REMOTE_PATH=borg-1.2
                BORG_EXPECTED_MAJOR_MINOR=1.2
                BORG_PASSPHRASE_FILE={self.secret}
                BORG_SSH_KEY={self.key}
                BORG_KNOWN_HOSTS={self.known_hosts}
                STORAGE_BOX_HOST=box
                HOST_MEDIA_PATHS={self.root / 'missing-media'}
                API_CONTAINER_MEDIA_PATHS=/app/imports:/app/exports
                SERVER_CONFIG_PATHS={self.compose_env}:{self.compose}
                MIN_FREE_BYTES=1024
                RETENTION_DAILY=14
                RETENTION_WEEKLY=8
                RETENTION_MONTHLY=12
                EXPECTED_DATABASE_TABLES=django_migrations,crm_organization,crm_person
                ARCHIVE_PREFIX=kreative-norge
                """
            ),
            encoding="utf-8",
        )
        self.config.chmod(0o600)
        self.call_log = self.root / "calls.log"
        self.env = os.environ.copy()
        self.env.update(
            {
                "PATH": f"{self.fake_bin}:{self.env['PATH']}",
                "BACKUP_TEST_MODE": "1",
                "BACKUP_ENV_FILE": str(self.config),
                "FAKE_CALL_LOG": str(self.call_log),
            }
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_script(self, script: str, *arguments: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        env = self.env.copy()
        env.update(extra_env)
        return subprocess.run(
            ["bash", str(MODULE_DIR / script), *arguments],
            cwd=MODULE_DIR,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def status_value(self) -> dict[str, object]:
        return json.loads(self.status.read_text(encoding="utf-8"))

    def assert_failed_at(self, result: subprocess.CompletedProcess[str], stage: str) -> None:
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.status_value()["last_error"]["stage"], stage)
        self.assertEqual(list(self.work.glob("run.*")), [])

    def test_missing_configuration_is_rejected(self) -> None:
        result = self.run_script("backup.sh", BACKUP_ENV_FILE=str(self.root / "absent"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("backup environment file is missing", result.stderr)

    def test_missing_pinned_host_key_is_rejected(self) -> None:
        result = self.run_script("backup.sh", "--preflight", FAKE_HOST_KEY_MISSING="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absent from the dedicated known_hosts", result.stderr)

    def test_storage_box_auth_failure_is_rejected(self) -> None:
        result = self.run_script("backup.sh", "--preflight", FAKE_BORG_AUTH_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository is unavailable or authentication failed", result.stderr)

    def test_unavailable_storage_box_is_rejected(self) -> None:
        result = self.run_script("backup.sh", "--preflight", FAKE_BORG_UNAVAILABLE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository is unavailable or authentication failed", result.stderr)

    def test_missing_storage_box_setting_is_rejected(self) -> None:
        configured = self.config.read_text(encoding="utf-8")
        self.config.write_text(configured.replace("STORAGE_BOX_HOST=box\n", "STORAGE_BOX_HOST=\n"), encoding="utf-8")
        result = self.run_script("backup.sh", "--preflight")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required configuration is missing: STORAGE_BOX_HOST", result.stderr)

    def test_repository_identity_mismatch_is_rejected(self) -> None:
        result = self.run_script("backup.sh", "--preflight", FAKE_REPOSITORY_ID=OTHER_REPOSITORY_ID)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identity does not match", result.stderr)

    def test_overlap_is_rejected_before_work(self) -> None:
        result = self.run_script("backup.sh", FAKE_LOCKED="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already running", result.stderr)
        self.assertFalse(self.status.exists())

    def test_insufficient_disk_is_recorded_and_cleaned(self) -> None:
        result = self.run_script("backup.sh", FAKE_AVAILABLE_BYTES="100")
        self.assert_failed_at(result, "disk")

    def test_pg_dump_failure_is_recorded_and_cleaned(self) -> None:
        result = self.run_script("backup.sh", FAKE_DUMP_FAIL="1")
        self.assert_failed_at(result, "dump")

    def test_pg_restore_list_failure_is_recorded_and_cleaned(self) -> None:
        result = self.run_script("backup.sh", FAKE_DUMP_VERIFY_FAIL="1")
        self.assert_failed_at(result, "dump_verify")

    def test_archive_create_failure_is_recorded_and_cleaned(self) -> None:
        result = self.run_script("backup.sh", FAKE_CREATE_FAIL="1")
        self.assert_failed_at(result, "create")

    def test_repository_check_failure_blocks_prune(self) -> None:
        result = self.run_script("backup.sh", FAKE_CHECK_FAIL="1")
        self.assert_failed_at(result, "repository")
        calls = self.call_log.read_text(encoding="utf-8")
        self.assertNotIn("borg prune", calls)
        self.assertNotIn("borg compact", calls)

    def test_missing_media_directories_are_nonfatal(self) -> None:
        result = self.run_script("backup.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = self.status_value()
        self.assertRegex(str(value["archive"]), r"^kreative-norge-staging-\d{8}T\d{6}Z$")
        self.assertEqual(value["dump_verification"], "passed")
        self.assertEqual(value["repository_verification"], "passed")
        self.assertEqual(list(self.work.glob("run.*")), [])

    def test_weekly_verify_updates_status(self) -> None:
        result = self.run_script("verify.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.status_value()["repository_verification"], "passed")
        self.assertIn("borg check --remote-path borg-1.2 --verify-data", self.call_log.read_text(encoding="utf-8"))

    def test_weekly_verify_failure_is_recorded(self) -> None:
        result = self.run_script("verify.sh", FAKE_CHECK_FAIL="1")
        self.assert_failed_at(result, "weekly_verify")

    def test_restore_rejects_missing_archive(self) -> None:
        result = self.run_script("restore-smoke.sh", FAKE_NO_ARCHIVES="1")
        self.assert_failed_at(result, "restore")

    def test_restore_smoke_completes_in_isolated_fixture(self) -> None:
        members = "\n".join(
            (
                "var/lib/kreative-norge-backup/work/run.test/database.dump",
                "var/lib/kreative-norge-backup/work/run.test/manifest.txt",
                "var/lib/kreative-norge-backup/work/run.test/checksums.sha256",
                "",
            )
        )
        result = self.run_script("restore-smoke.sh", FAKE_MEMBER_LIST=members)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = self.status_value()
        self.assertIsNotNone(value["last_restore_success"])
        self.assertEqual(value["archive"], ARCHIVE)
        self.assertIn(f"archive={ARCHIVE}\n", (self.root / "restore-smoke.ok").read_text(encoding="utf-8"))
        self.assertEqual(list(self.work.glob("restore.*")), [])


class StatusTests(unittest.TestCase):
    def test_activation_requires_all_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            base = ["python3", str(MODULE_DIR / "status.py"), "update", "--path", str(status_path)]
            subprocess.run(base + ["--event", "start", "--timestamp", "2026-08-01T00:00:00Z"], check=True)
            blocked = subprocess.run(
                ["python3", str(MODULE_DIR / "status.py"), "activation-ready", "--path", str(status_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            subprocess.run(base + ["--event", "success", "--timestamp", "2026-08-01T01:00:00Z", "--archive", ARCHIVE], check=True)
            subprocess.run(base + ["--event", "restore-success", "--timestamp", "2026-08-01T02:00:00Z", "--archive", ARCHIVE], check=True)
            ready = subprocess.run(
                ["python3", str(MODULE_DIR / "status.py"), "activation-ready", "--path", str(status_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertEqual(ready.stdout.strip(), ARCHIVE)
            other_archive = "kreative-norge-staging-20260802T023000Z"
            subprocess.run(base + ["--event", "restore-success", "--timestamp", "2026-08-02T02:00:00Z", "--archive", other_archive], check=True)
            mismatched = subprocess.run(
                ["python3", str(MODULE_DIR / "status.py"), "activation-ready", "--path", str(status_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(mismatched.returncode, 0)


class ParserSecurityTests(unittest.TestCase):
    def test_restore_members_rejects_parent_traversal(self) -> None:
        result = subprocess.run(
            ["python3", str(MODULE_DIR / "status.py"), "restore-members"],
            input="../database.dump\n../manifest.txt\n../checksums.sha256\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_checksum_manifest_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checksums = Path(temporary) / "checksums.sha256"
            checksums.write_text("a" * 64 + "  ../../outside\n", encoding="utf-8")
            result = subprocess.run(
                ["python3", str(MODULE_DIR / "status.py"), "validate-checksums", "--path", str(checksums)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)


class DocumentationTests(unittest.TestCase):
    def test_new_local_markdown_links_exist(self) -> None:
        import re
        from urllib.parse import unquote

        repository_root = MODULE_DIR.parents[1]
        documents = (
            MODULE_DIR / "README.md",
            repository_root / "docs/README.md",
            repository_root / "docs/operations/BACKUP_AND_RESTORE.md",
            repository_root / "docs/decisions/README.md",
            repository_root / "docs/decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md",
            repository_root / "docs/decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md",
            repository_root / "docs/architecture/DEPLOYMENT.md",
            repository_root / "docs/status/PROJECT_STATUS_CURRENT.md",
            repository_root / "docs/status/ROADMAP.md",
            repository_root / "docs/status/CHANGELOG.md",
        )
        for document in documents:
            for raw_target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                target = raw_target.strip("<>").split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (document.parent / unquote(target)).resolve()
                self.assertTrue(resolved.exists(), f"broken local link in {document}: {raw_target}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

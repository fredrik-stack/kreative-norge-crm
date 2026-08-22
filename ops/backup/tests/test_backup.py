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
    if os.environ.get("FAKE_REQUIRE_SECURE_BORG_ENV") == "1":
        borg_rsh = os.environ.get("BORG_RSH", "")
        required_rsh = (
            " -i ",
            "IdentitiesOnly=yes",
            "BatchMode=yes",
            "StrictHostKeyChecking=yes",
            "UserKnownHostsFile=",
            "ConnectTimeout=15",
        )
        if not os.environ.get("BORG_PASSCOMMAND", "").startswith("cat /") or any(
            value not in f" {borg_rsh}" for value in required_rsh
        ):
            raise SystemExit(9)
    if command == "info":
        if os.environ.get("FAKE_BORG_AUTH_FAIL") == "1" or os.environ.get("FAKE_BORG_UNAVAILABLE") == "1":
            raise SystemExit(2)
        print(json.dumps({"repository": {"id": os.environ.get("FAKE_REPOSITORY_ID", "a" * 64)}}))
        raise SystemExit(0)
    if command == "list":
        if "--json" in args:
            archives = [] if os.environ.get("FAKE_NO_ARCHIVES") == "1" else [{
                "name": os.environ.get("FAKE_ARCHIVE", "kreative-norge-staging-20260801T023000Z"),
                "comment": os.environ.get("FAKE_BORG_SENSITIVE", ""),
            }]
            print(json.dumps({"archives": archives}))
        else:
            print(os.environ.get("FAKE_MEMBER_LIST", ""), end="")
        raise SystemExit(0)
    if command == "key":
        if "export" not in args or os.environ.get("FAKE_KEY_EXPORT_FAIL") == "1":
            raise SystemExit(2)
        destination = Path(args[-1])
        if os.environ.get("FAKE_EMPTY_KEY_EXPORT") == "1":
            destination.write_bytes(b"")
        else:
            destination.write_text(
                os.environ.get("FAKE_KEY_MATERIAL", "synthetic-encrypted-repository-key\n"),
                encoding="utf-8",
            )
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
        if "pg_restore" in joined:
            raise SystemExit(1 if os.environ.get("FAKE_RESTORE_DB_FAIL") == "1" else 0)
        if "pg_isready" in joined:
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
        self.root = Path(self.temporary.name).resolve()
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
        self.state_root = self.root / "state" / "kreative-norge-backup"
        self.work = self.state_root / "work"
        self.status = self.state_root / "status.json"
        self.lock = self.root / "run" / "kreative-norge-backup.lock"
        self.host_media_root = self.root / "kreative-norge" / "media"
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
                BACKUP_STATE_ROOT={self.state_root}
                WORK_ROOT={self.work}
                STATUS_FILE={self.status}
                LOCK_FILE={self.lock}
                RESTORE_GATE_FILE={self.state_root / 'restore-smoke.ok'}
                BORG_BIN=borg
                BORG_REPOSITORY=ssh://u@box:23/./repo
                BORG_REPOSITORY_ID={REPOSITORY_ID}
                BORG_REMOTE_PATH=borg-1.2
                BORG_EXPECTED_MAJOR_MINOR=1.2
                BORG_PASSPHRASE_FILE={self.secret}
                BORG_SSH_KEY={self.key}
                BORG_KNOWN_HOSTS={self.known_hosts}
                STORAGE_BOX_HOST=box
                HOST_MEDIA_ROOT={self.host_media_root}
                HOST_MEDIA_PATHS={self.host_media_root / 'missing-media'}
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
        for variable in ("BORG_CACHE_DIR", "BORG_CONFIG_DIR", "BORG_SECURITY_DIR"):
            self.env.pop(variable, None)
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

    def run_install(self, *arguments: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        env = self.env.copy()
        env.update(
            {
                "BACKUP_INSTALL_DIR": str(MODULE_DIR),
                "BACKUP_ENV_FILE": str(self.config),
            }
        )
        env.update(extra_env)
        return subprocess.run(
            ["bash", str(MODULE_DIR / "install.sh"), *arguments],
            cwd=MODULE_DIR,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def set_config_value(self, name: str, value: str) -> None:
        prefix = f"{name}="
        lines = self.config.read_text(encoding="utf-8").splitlines()
        self.config.write_text(
            "\n".join(f"{prefix}{value}" if line.startswith(prefix) else line for line in lines) + "\n",
            encoding="utf-8",
        )

    def assert_config_rejected_before_work(
        self,
        result: subprocess.CompletedProcess[str],
        expected_error: str,
    ) -> None:
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn(expected_error, result.stderr)
        self.assertFalse(self.work.exists())
        self.assertFalse(self.status.exists())
        calls = self.call_log.read_text(encoding="utf-8") if self.call_log.exists() else ""
        self.assertNotIn("borg info", calls)
        self.assertNotIn("borg create", calls)
        self.assertNotIn("docker ", calls)

    @staticmethod
    def restore_members() -> str:
        return "\n".join(
            (
                "var/lib/kreative-norge-backup/work/run.test/database.dump",
                "var/lib/kreative-norge-backup/work/run.test/manifest.txt",
                "var/lib/kreative-norge-backup/work/run.test/checksums.sha256",
                "",
            )
        )

    def status_value(self) -> dict[str, object]:
        return json.loads(self.status.read_text(encoding="utf-8"))

    def assert_failed_at(self, result: subprocess.CompletedProcess[str], stage: str) -> None:
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.status_value()["last_error"]["stage"], stage)
        self.assertEqual(list(self.work.glob("run.*")), [])

    def test_borg_versions_below_1_2_8_and_outside_1_2_are_rejected(self) -> None:
        for version in ("1.2.0", "1.2.4", "1.2.7", "1.3.0", "2.0.0"):
            with self.subTest(version=version):
                result = self.run_script("backup.sh", "--preflight", FAKE_BORG_VERSION=version)
                self.assert_config_rejected_before_work(result, "at least 1.2.8 and lower than 1.3.0")

    def test_supported_borg_1_2_patch_versions_are_accepted(self) -> None:
        for version in ("1.2.8", "1.2.9", "1.2.10"):
            with self.subTest(version=version):
                result = self.run_script("backup.sh", "--preflight", FAKE_BORG_VERSION=version)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_borg_prerelease_and_malformed_versions_are_rejected(self) -> None:
        for version in ("1.2.8rc1", "1.2", "unknown", "1.2.8 extra", "01.2.8"):
            with self.subTest(version=version):
                result = self.run_script("backup.sh", "--preflight", FAKE_BORG_VERSION=version)
                self.assert_config_rejected_before_work(result, "malformed or is a prerelease")

    def test_every_repository_command_uses_the_same_borg_version_gate(self) -> None:
        commands = (
            ("script", ("backup.sh", "--preflight")),
            ("script", ("verify.sh",)),
            ("script", ("restore-smoke.sh",)),
            ("install", ("export-recovery-key", str(self.root / "recovery-key-export"))),
            ("install", ("inspect-repository",)),
            ("install", ("init-repository",)),
        )
        for runner, arguments in commands:
            with self.subTest(command=arguments[0]):
                if self.call_log.exists():
                    self.call_log.unlink()
                if self.status.exists():
                    self.status.unlink()
                if runner == "script":
                    result = self.run_script(*arguments, FAKE_BORG_VERSION="1.2.7")
                else:
                    result = self.run_install(*arguments, FAKE_BORG_VERSION="1.2.7")
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertIn("at least 1.2.8 and lower than 1.3.0", result.stderr)
                calls = self.call_log.read_text(encoding="utf-8") if self.call_log.exists() else ""
                self.assertIn("borg --version", calls)
                self.assertNotIn("borg info", calls)
                for operation in ("create", "key", "list", "check", "prune", "compact", "extract", "init"):
                    self.assertNotIn(f"borg {operation} ", calls)
                self.assertFalse(self.work.exists())

    def test_root_paths_are_rejected_for_every_writable_host_path_family(self) -> None:
        original = self.config.read_text(encoding="utf-8")
        for variable in ("BACKUP_STATE_ROOT", "WORK_ROOT", "STATUS_FILE", "RESTORE_GATE_FILE", "LOCK_FILE"):
            with self.subTest(variable=variable):
                self.config.write_text(original, encoding="utf-8")
                self.set_config_value(variable, "/")
                result = self.run_script("backup.sh", "--preflight")
                self.assert_config_rejected_before_work(result, "not a normalized non-root path")

    def test_ambient_borg_directories_cannot_escape_the_work_root(self) -> None:
        for variable in ("BORG_CACHE_DIR", "BORG_CONFIG_DIR", "BORG_SECURITY_DIR"):
            with self.subTest(variable=variable):
                result = self.run_script("backup.sh", "--preflight", **{variable: "/"})
                self.assert_config_rejected_before_work(result, f"{variable} must use its dedicated backup work path")

    def test_broad_or_overlapping_host_media_paths_are_rejected(self) -> None:
        original = self.config.read_text(encoding="utf-8")
        for path in ("/", "/etc", "/root", "/var", str(self.app), str(self.work)):
            with self.subTest(path=path):
                self.config.write_text(original, encoding="utf-8")
                self.set_config_value("HOST_MEDIA_PATHS", path)
                result = self.run_script("backup.sh", "--preflight")
                expected = "not a normalized non-root path" if path == "/" else "below HOST_MEDIA_ROOT"
                self.assert_config_rejected_before_work(result, expected)

    def test_container_media_paths_must_be_explicit_app_subdirectories(self) -> None:
        original = self.config.read_text(encoding="utf-8")
        for path in ("/", "/app"):
            with self.subTest(path=path):
                self.config.write_text(original, encoding="utf-8")
                self.set_config_value("API_CONTAINER_MEDIA_PATHS", path)
                result = self.run_script("backup.sh", "--preflight")
                expected = "not a normalized non-root path" if path == "/" else "explicit subdirectories below /app"
                self.assert_config_rejected_before_work(result, expected)

    def test_last_entry_in_each_colon_separated_path_list_is_validated(self) -> None:
        original = self.config.read_text(encoding="utf-8")
        cases = (
            (
                "HOST_MEDIA_PATHS",
                f"{self.host_media_root / 'allowed'}:/etc",
                "below HOST_MEDIA_ROOT",
            ),
            (
                "API_CONTAINER_MEDIA_PATHS",
                "/app/imports:/app",
                "explicit subdirectories below /app",
            ),
            (
                "SERVER_CONFIG_PATHS",
                f"{self.compose_env}:/invalid//server-config",
                "not a normalized non-root path",
            ),
        )
        for variable, value, expected in cases:
            with self.subTest(variable=variable):
                self.config.write_text(original, encoding="utf-8")
                self.set_config_value(variable, value)
                result = self.run_script("backup.sh", "--preflight")
                self.assert_config_rejected_before_work(result, expected)

    def test_host_media_cannot_contain_secret_or_ssh_files(self) -> None:
        original = self.config.read_text(encoding="utf-8")
        for variable in ("BORG_PASSPHRASE_FILE", "BORG_SSH_KEY", "BORG_KNOWN_HOSTS"):
            with self.subTest(variable=variable):
                self.config.write_text(original, encoding="utf-8")
                media_path = self.host_media_root / variable.lower()
                media_path.mkdir(parents=True, exist_ok=True)
                protected_file = media_path / "protected-file"
                protected_file.write_text("synthetic-test-only\n", encoding="utf-8")
                protected_file.chmod(0o600)
                self.set_config_value("HOST_MEDIA_PATHS", str(media_path))
                self.set_config_value(variable, str(protected_file))
                result = self.run_script("backup.sh", "--preflight")
                self.assert_config_rejected_before_work(result, "overlaps a protected path")

    def test_host_media_cannot_contain_server_configuration(self) -> None:
        media_path = self.host_media_root / "server-config-overlap"
        media_path.mkdir(parents=True)
        protected_file = media_path / "protected.conf"
        protected_file.write_text("synthetic=true\n", encoding="utf-8")
        self.set_config_value("HOST_MEDIA_PATHS", str(media_path))
        self.set_config_value("SERVER_CONFIG_PATHS", str(protected_file))
        result = self.run_script("backup.sh", "--preflight")
        self.assert_config_rejected_before_work(result, "overlaps a protected path")

    def test_work_root_symlink_to_root_is_rejected_before_mutation(self) -> None:
        self.state_root.mkdir(parents=True)
        self.work.symlink_to("/")
        result = self.run_script("backup.sh", "--preflight")
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("must not contain symlink components", result.stderr)
        self.assertFalse(self.status.exists())
        calls = self.call_log.read_text(encoding="utf-8") if self.call_log.exists() else ""
        self.assertNotIn("borg ", calls)
        self.assertNotIn("docker ", calls)

    def test_host_media_symlink_to_protected_path_is_rejected(self) -> None:
        self.host_media_root.mkdir(parents=True)
        media_path = self.host_media_root / "root-link"
        media_path.symlink_to("/")
        self.set_config_value("HOST_MEDIA_PATHS", str(media_path))
        result = self.run_script("backup.sh", "--preflight")
        self.assert_config_rejected_before_work(result, "must not contain symlink components")

    def test_export_and_inspect_share_the_semantic_path_gate(self) -> None:
        self.set_config_value("HOST_MEDIA_PATHS", "/")
        destination = self.root / "recovery-key-export"
        for arguments in (("export-recovery-key", str(destination)), ("inspect-repository",)):
            with self.subTest(command=arguments[0]):
                result = self.run_install(*arguments)
                self.assert_config_rejected_before_work(result, "not a normalized non-root path")
        self.assertFalse(destination.exists())

    def test_current_approved_path_layout_passes_preflight(self) -> None:
        result = self.run_script("backup.sh", "--preflight")
        self.assertEqual(result.returncode, 0, result.stderr)

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

    def test_weekly_verify_lock_contention_does_not_create_status(self) -> None:
        result = self.run_script("verify.sh", FAKE_LOCKED="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already running", result.stderr)
        self.assertFalse(self.status.exists())

    def test_weekly_verify_lock_contention_preserves_existing_status_bytes(self) -> None:
        original = b'{"format_version":1,"sentinel":"unchanged"}\n'
        self.status.parent.mkdir(parents=True)
        self.status.write_bytes(original)
        result = self.run_script("verify.sh", FAKE_LOCKED="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already running", result.stderr)
        self.assertEqual(self.status.read_bytes(), original)

    def test_restore_lock_contention_does_not_create_status_or_resources(self) -> None:
        result = self.run_script("restore-smoke.sh", FAKE_LOCKED="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already running", result.stderr)
        self.assertFalse(self.status.exists())
        self.assertEqual(list(self.work.glob("restore.*")), [])
        calls = self.call_log.read_text(encoding="utf-8")
        self.assertNotIn("docker run", calls)
        self.assertNotIn("docker rm", calls)

    def test_restore_lock_contention_preserves_existing_status_bytes_and_resources(self) -> None:
        original = b'{"format_version":1,"sentinel":"unchanged"}\n'
        self.status.parent.mkdir(parents=True)
        self.status.write_bytes(original)
        result = self.run_script("restore-smoke.sh", FAKE_LOCKED="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already running", result.stderr)
        self.assertEqual(self.status.read_bytes(), original)
        self.assertEqual(list(self.work.glob("restore.*")), [])
        calls = self.call_log.read_text(encoding="utf-8")
        self.assertNotIn("docker run", calls)
        self.assertNotIn("docker rm", calls)

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
        result = self.run_script("restore-smoke.sh", FAKE_MEMBER_LIST=self.restore_members())
        self.assertEqual(result.returncode, 0, result.stderr)
        value = self.status_value()
        self.assertIsNotNone(value["last_restore_success"])
        self.assertEqual(value["archive"], ARCHIVE)
        self.assertIn(f"archive={ARCHIVE}\n", (self.state_root / "restore-smoke.ok").read_text(encoding="utf-8"))
        self.assertEqual(list(self.work.glob("restore.*")), [])

    def test_restore_failure_after_lock_records_status_and_cleans_resources(self) -> None:
        result = self.run_script(
            "restore-smoke.sh",
            FAKE_MEMBER_LIST=self.restore_members(),
            FAKE_RESTORE_DB_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.status_value()["last_error"]["stage"], "restore")
        self.assertEqual(list(self.work.glob("restore.*")), [])
        calls = self.call_log.read_text(encoding="utf-8")
        self.assertIn("docker rm -f kreative-norge-restore-", calls)

    def test_recovery_key_export_succeeds_without_leaking_key_material(self) -> None:
        destination = self.root / "recovery-key-export"
        key_material = "synthetic-secret-key-material"
        result = self.run_install(
            "export-recovery-key",
            str(destination),
            FAKE_KEY_MATERIAL=key_material,
            FAKE_REQUIRE_SECURE_BORG_ENV="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(destination.is_file())
        self.assertGreater(destination.stat().st_size, 0)
        self.assertNotIn(key_material, result.stdout)
        self.assertNotIn(key_material, result.stderr)
        self.assertIn(f"repository_id={REPOSITORY_ID}", result.stdout)
        self.assertIn(f"destination={destination}", result.stdout)

    def test_recovery_key_export_requires_backup_environment(self) -> None:
        destination = self.root / "recovery-key-export"
        result = self.run_install(
            "export-recovery-key",
            str(destination),
            BACKUP_ENV_FILE=str(self.root / "absent.env"),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("backup.env is missing", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_rejects_missing_required_configuration(self) -> None:
        configured = self.config.read_text(encoding="utf-8")
        self.config.write_text(configured.replace(f"BORG_SSH_KEY={self.key}\n", "BORG_SSH_KEY=\n"), encoding="utf-8")
        destination = self.root / "recovery-key-export"
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required configuration is missing: BORG_SSH_KEY", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_rejects_repository_identity_mismatch(self) -> None:
        destination = self.root / "recovery-key-export"
        result = self.run_install(
            "export-recovery-key",
            str(destination),
            FAKE_REPOSITORY_ID=OTHER_REPOSITORY_ID,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identity does not match", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_rejects_unavailable_repository(self) -> None:
        destination = self.root / "recovery-key-export"
        result = self.run_install(
            "export-recovery-key",
            str(destination),
            FAKE_BORG_UNAVAILABLE="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository is unavailable", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_rejects_relative_destination(self) -> None:
        result = self.run_install("export-recovery-key", "relative-key")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be an absolute path", result.stderr)

    def test_recovery_key_export_rejects_unsafe_destination_characters(self) -> None:
        result = self.run_install("export-recovery-key", str(self.root / "unsafe key"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe shell characters", result.stderr)

    def test_recovery_key_export_rejects_parent_traversal(self) -> None:
        result = self.run_install("export-recovery-key", str(self.root / "subdir" / ".." / "recovery-key"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("parent-directory component", result.stderr)

    def test_recovery_key_export_rejects_group_or_world_writable_parent(self) -> None:
        destination_parent = self.root / "shared-export-parent"
        destination_parent.mkdir()
        destination_parent.chmod(0o777)
        destination = destination_parent / "recovery-key-export"
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("group- or world-writable", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_rejects_directory_target(self) -> None:
        destination = self.root / "recovery-key-export"
        destination.mkdir()
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(list(destination.iterdir()), [])

    def test_recovery_key_export_rejects_broken_symlink_target(self) -> None:
        destination = self.root / "recovery-key-export"
        destination.symlink_to(self.root / "missing-target")
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not contain symlink components", result.stderr)
        self.assertTrue(destination.is_symlink())

    def test_recovery_key_export_rejects_symlink_parent(self) -> None:
        actual_parent = self.root / "actual-export-parent"
        actual_parent.mkdir()
        symlink_parent = self.root / "linked-export-parent"
        symlink_parent.symlink_to(actual_parent, target_is_directory=True)
        destination = symlink_parent / "recovery-key-export"
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not contain symlink components", result.stderr)
        self.assertFalse((actual_parent / "recovery-key-export").exists())

    def test_recovery_key_export_refuses_existing_destination(self) -> None:
        destination = self.root / "recovery-key-export"
        original = b"keep-existing-bytes\n"
        destination.write_bytes(original)
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(destination.read_bytes(), original)

    def test_recovery_key_export_rejects_application_repository_destination(self) -> None:
        destination = self.app / "recovery-key-export"
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the application repository", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_rejects_backup_work_destination(self) -> None:
        self.work.mkdir(parents=True)
        destination = self.work / "recovery-key-export"
        result = self.run_install("export-recovery-key", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside backup work paths", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_rejects_empty_export(self) -> None:
        destination = self.root / "recovery-key-export"
        result = self.run_install(
            "export-recovery-key",
            str(destination),
            FAKE_EMPTY_KEY_EXPORT="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("export is empty", result.stderr)
        self.assertFalse(destination.exists())

    def test_recovery_key_export_sets_mode_0600(self) -> None:
        destination = self.root / "recovery-key-export"
        result = self.run_install("export-recovery-key", str(destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)

    def test_recovery_key_export_uses_expected_borg_contract_without_mutation(self) -> None:
        destination = self.root / "recovery-key-export"
        result = self.run_install("export-recovery-key", str(destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.call_log.read_text(encoding="utf-8")
        self.assertIn(
            "borg key export --remote-path borg-1.2 ssh://u@box:23/./repo ",
            calls,
        )
        for command in ("create", "prune", "compact", "delete", "extract", "init"):
            self.assertNotIn(f"borg {command} ", calls)

    def test_initialize_repository_still_uses_repokey_blake2_contract(self) -> None:
        result = self.run_install("init-repository")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.call_log.read_text(encoding="utf-8")
        self.assertIn(
            "borg init --remote-path borg-1.2 --encryption=repokey-blake2 ssh://u@box:23/./repo",
            calls,
        )
        self.assertIn("Next mandatory recovery step", result.stdout)

    def test_repository_inspection_reports_only_safe_summary(self) -> None:
        sensitive = "synthetic-member-or-secret-value"
        result = self.run_install(
            "inspect-repository",
            FAKE_BORG_SENSITIVE=sensitive,
            FAKE_REQUIRE_SECURE_BORG_ENV="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Repository is available and identity is verified", result.stdout)
        self.assertIn(f"repository_id={REPOSITORY_ID}", result.stdout)
        self.assertIn("archive_count=1", result.stdout)
        self.assertIn(f"latest_archive={ARCHIVE}", result.stdout)
        self.assertNotIn(sensitive, result.stdout)
        self.assertNotIn(sensitive, result.stderr)

    def test_repository_inspection_rejects_identity_mismatch(self) -> None:
        result = self.run_install("inspect-repository", FAKE_REPOSITORY_ID=OTHER_REPOSITORY_ID)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identity does not match", result.stderr)

    def test_repository_inspection_rejects_unavailable_repository(self) -> None:
        result = self.run_install("inspect-repository", FAKE_BORG_UNAVAILABLE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository is unavailable", result.stderr)

    def test_repository_inspection_rejects_empty_repository(self) -> None:
        result = self.run_install("inspect-repository", FAKE_NO_ARCHIVES="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no Borg archives found", result.stderr)

    def test_repository_inspection_rejects_unsafe_archive_name(self) -> None:
        result = self.run_install("inspect-repository", FAKE_ARCHIVE="../unsafe-archive")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe archive name", result.stderr)

    def test_repository_inspection_does_not_mutate_repository(self) -> None:
        result = self.run_install("inspect-repository")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.call_log.read_text(encoding="utf-8")
        self.assertIn("borg info --remote-path borg-1.2 --json ssh://u@box:23/./repo", calls)
        self.assertIn("borg list --remote-path borg-1.2 --json", calls)
        for command in ("key", "create", "prune", "compact", "delete", "extract", "init"):
            self.assertNotIn(f"borg {command} ", calls)


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
    def test_atomic_link_no_clobber_rejects_directory_and_symlink_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source-key"
            source.write_bytes(b"synthetic-encrypted-key\n")

            directory_target = root / "directory-target"
            directory_target.mkdir()
            directory_result = subprocess.run(
                [
                    "python3",
                    str(MODULE_DIR / "status.py"),
                    "link-no-clobber",
                    "--source",
                    str(source),
                    "--destination",
                    str(directory_target),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(directory_result.returncode, 0)
            self.assertTrue(directory_target.is_dir())

            victim = root / "victim"
            victim.write_bytes(b"keep-victim-bytes\n")
            symlink_target = root / "symlink-target"
            symlink_target.symlink_to(victim)
            symlink_result = subprocess.run(
                [
                    "python3",
                    str(MODULE_DIR / "status.py"),
                    "link-no-clobber",
                    "--source",
                    str(source),
                    "--destination",
                    str(symlink_target),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(symlink_result.returncode, 0)
            self.assertTrue(symlink_target.is_symlink())
            self.assertEqual(victim.read_bytes(), b"keep-victim-bytes\n")

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
    def test_staging_example_uses_verified_compose_environment_path(self) -> None:
        example = (MODULE_DIR / "backup.env.example").read_text(encoding="utf-8")
        values = dict(
            line.split("=", 1)
            for line in example.splitlines()
            if line and not line.startswith("#") and "=" in line
        )
        verified_path = "/srv/kreative-norge-crm/.env.staging"
        self.assertIn(f"COMPOSE_ENV_FILE={verified_path}\n", example)
        server_paths = next(
            line for line in example.splitlines() if line.startswith("SERVER_CONFIG_PATHS=")
        )
        self.assertIn(verified_path, server_paths.split("=", 1)[1].split(":"))
        self.assertNotIn("/srv/kreative-norge-crm/.env", server_paths.split("=", 1)[1].split(":"))
        self.assertEqual(values["BACKUP_STATE_ROOT"], "/var/lib/kreative-norge-backup")
        self.assertEqual(values["WORK_ROOT"], f"{values['BACKUP_STATE_ROOT']}/work")
        self.assertEqual(values["STATUS_FILE"], f"{values['BACKUP_STATE_ROOT']}/status.json")
        self.assertEqual(values["RESTORE_GATE_FILE"], f"{values['BACKUP_STATE_ROOT']}/restore-smoke.ok")
        self.assertEqual(values["HOST_MEDIA_ROOT"], "/srv/kreative-norge/media")
        self.assertIn(
            "/srv/kreative-norge/media/public-delivery",
            values["HOST_MEDIA_PATHS"].split(":"),
        )
        self.assertTrue(
            all(
                path.startswith(f"{values['HOST_MEDIA_ROOT']}/")
                for path in values["HOST_MEDIA_PATHS"].split(":")
            )
        )
        self.assertTrue(
            all(
                path.startswith("/app/")
                for path in values["API_CONTAINER_MEDIA_PATHS"].split(":")
            )
        )

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
            repository_root / "docs/status/STAGING_BACKUP_BASELINE_2026-08-01.md",
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

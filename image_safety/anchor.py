from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Protocol

from .ledger import AnchorConflictError, PublicImageSafetyLedger


REPOSITORY_ID_RE = re.compile(r"^[0-9a-f]{64}$")
BORG_STABLE_VERSION_RE = re.compile(
    r"^borg ([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)$"
)
MINIMUM_BORG_VERSION = (1, 2, 8)
MAXIMUM_BORG_VERSION = (1, 3, 0)


class AnchorBackendError(Exception):
    pass


class AnchorBackend(Protocol):
    def verified_repository_id(self) -> str: ...
    def read(self, archive_name: str) -> bytes | None: ...
    def create(self, archive_name: str, content: bytes) -> None: ...
    def list_archives(self, prefix: str) -> list[str]: ...


@dataclass(frozen=True)
class AnchorResult:
    archive_name: str
    cursor: int
    event_hash: str
    repository_id: str
    bundle_sha256: str
    reused_archive: bool


def archive_name_for(*, ledger_id: str, cursor: int, event_hash: str) -> str:
    return f"image-safety-{ledger_id}-{cursor:020d}-{event_hash[:16]}"


def anchor_current_head(
    ledger: PublicImageSafetyLedger,
    backend: AnchorBackend,
    *,
    expected_repository_id: str,
    after_remote_write_hook=None,
) -> AnchorResult:
    repository_id = backend.verified_repository_id().lower()
    if not REPOSITORY_ID_RE.fullmatch(expected_repository_id.lower()):
        raise AnchorBackendError("Expected repository identity is invalid.")
    if repository_id != expected_repository_id.lower():
        raise AnchorBackendError("Off-server repository identity mismatch.")
    head = ledger.head()
    content = ledger.bundle_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    archive_name = archive_name_for(
        ledger_id=head.ledger_id, cursor=head.sequence, event_hash=head.event_hash
    )
    existing = backend.read(archive_name)
    reused = existing is not None
    if existing is not None and existing != content:
        raise AnchorConflictError(
            "Existing off-server archive name contains different ledger bytes."
        )
    if existing is None:
        try:
            backend.create(archive_name, content)
        except AnchorBackendError:
            # A concurrent same-head writer may have won after our read. Only
            # the exact expected bytes turn that create failure into a retry.
            if backend.read(archive_name) != content:
                raise
    verified = backend.read(archive_name)
    if verified != content:
        raise AnchorBackendError("Off-server anchor read-back verification failed.")
    if after_remote_write_hook is not None:
        after_remote_write_hook()
    ledger.record_anchor_receipt(
        cursor=head.sequence,
        event_hash=head.event_hash,
        archive_name=archive_name,
        repository_id=repository_id,
        bundle_sha256=checksum,
    )
    return AnchorResult(
        archive_name=archive_name,
        cursor=head.sequence,
        event_hash=head.event_hash,
        repository_id=repository_id,
        bundle_sha256=checksum,
        reused_archive=reused,
    )


def restore_latest_anchor(
    backend: AnchorBackend,
    *,
    expected_repository_id: str,
    destination: str | os.PathLike[str],
) -> PublicImageSafetyLedger:
    repository_id = backend.verified_repository_id().lower()
    if repository_id != expected_repository_id.lower():
        raise AnchorBackendError("Off-server repository identity mismatch.")
    archives = backend.list_archives("image-safety-")
    candidates: list[tuple[int, str, str, str]] = []
    for name in archives:
        match = re.fullmatch(
            r"image-safety-([0-9a-f-]{36})-([0-9]{20})-([0-9a-f]{16})", name
        )
        if match:
            candidates.append((int(match.group(2)), name, match.group(1), match.group(3)))
    if not candidates:
        raise AnchorBackendError("No image safety anchors are available.")
    ledger_ids = {item[2] for item in candidates}
    if len(ledger_ids) != 1:
        raise AnchorBackendError("Dedicated anchor repository contains multiple ledger identities.")
    max_cursor = max(item[0] for item in candidates)
    latest = [item for item in candidates if item[0] == max_cursor]
    if len(latest) != 1:
        raise AnchorBackendError("Latest anchor cursor has conflicting archive identities.")
    _, archive_name, archive_ledger_id, archive_hash_prefix = latest[0]
    content = backend.read(archive_name)
    if content is None:
        raise AnchorBackendError("Latest image safety anchor disappeared during restore.")
    try:
        summary = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnchorBackendError("Latest anchor is not valid JSON.") from error
    if (
        not isinstance(summary, dict)
        or summary.get("ledger_id") != archive_ledger_id
        or summary.get("event_cursor") != max_cursor
        or not str(summary.get("event_head_hash", "")).startswith(archive_hash_prefix)
    ):
        raise AnchorBackendError("Anchor archive name does not match its bundle metadata.")
    restored = PublicImageSafetyLedger.restore_bundle(
        bundle=content,
        destination=destination,
        archive_name=archive_name,
        repository_id=repository_id,
    )
    head = restored.head()
    if (
        head.ledger_id != archive_ledger_id
        or head.sequence != max_cursor
        or not head.event_hash.startswith(archive_hash_prefix)
    ):
        raise AnchorBackendError("Anchor archive name does not match its verified bundle.")
    return restored


@dataclass(frozen=True)
class BorgAnchorConfig:
    repository: str
    expected_repository_id: str
    ssh_key: Path
    known_hosts: Path
    passphrase_file: Path
    state_root: Path
    borg_bin: str = "borg"
    remote_path: str = "borg-1.2"
    required_owner_uid: int = 0

    @classmethod
    def from_environment(cls) -> "BorgAnchorConfig":
        required = {
            key: os.environ.get(key, "")
            for key in (
                "IMAGE_SAFETY_BORG_REPOSITORY",
                "IMAGE_SAFETY_BORG_REPOSITORY_ID",
                "IMAGE_SAFETY_BORG_SSH_KEY",
                "IMAGE_SAFETY_BORG_KNOWN_HOSTS",
                "IMAGE_SAFETY_BORG_PASSPHRASE_FILE",
                "IMAGE_SAFETY_STATE_ROOT",
            )
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise AnchorBackendError(
                "Missing image safety anchor configuration: " + ", ".join(missing)
            )
        return cls(
            repository=required["IMAGE_SAFETY_BORG_REPOSITORY"],
            expected_repository_id=required["IMAGE_SAFETY_BORG_REPOSITORY_ID"].lower(),
            ssh_key=Path(required["IMAGE_SAFETY_BORG_SSH_KEY"]),
            known_hosts=Path(required["IMAGE_SAFETY_BORG_KNOWN_HOSTS"]),
            passphrase_file=Path(required["IMAGE_SAFETY_BORG_PASSPHRASE_FILE"]),
            state_root=Path(required["IMAGE_SAFETY_STATE_ROOT"]),
            borg_bin=os.environ.get("IMAGE_SAFETY_BORG_BIN", "borg"),
            remote_path=os.environ.get("IMAGE_SAFETY_BORG_REMOTE_PATH", "borg-1.2"),
        )

    def validate(self) -> None:
        if not self.repository.startswith("ssh://"):
            raise AnchorBackendError("Image safety Borg repository must use SSH.")
        if not REPOSITORY_ID_RE.fullmatch(self.expected_repository_id):
            raise AnchorBackendError("Expected repository identity is invalid.")
        for path, label in (
            (self.ssh_key, "SSH key"),
            (self.known_hosts, "known_hosts"),
            (self.passphrase_file, "Borg passphrase"),
        ):
            if not path.is_absolute() or not path.is_file() or path.is_symlink():
                raise AnchorBackendError(f"{label} file is missing or unsafe.")
            if path.stat().st_mode & 0o077:
                raise AnchorBackendError(f"{label} file must not be group/world accessible.")
            if path.stat().st_uid != self.required_owner_uid:
                raise AnchorBackendError(f"{label} file must be root-owned.")
            if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(path)):
                raise AnchorBackendError(f"{label} path contains unsafe characters.")
        if not self.state_root.is_absolute():
            raise AnchorBackendError("Image safety state root must be absolute.")
        if self.state_root.is_symlink():
            raise AnchorBackendError("Image safety state root must not be a symlink.")
        if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(self.state_root)):
            raise AnchorBackendError("Image safety state root contains unsafe characters.")


class BorgAnchorBackend:
    """Borg 1.2 backend using a dedicated restricted writer repository."""

    def __init__(self, config: BorgAnchorConfig):
        config.validate()
        self.config = config
        for name in ("cache", "config", "security"):
            (config.state_root / "borg" / name).mkdir(
                parents=True, exist_ok=True, mode=0o700
            )

    def verified_repository_id(self) -> str:
        self._validate_version()
        repository_id = self._repository_id_unchecked()
        if repository_id != self.config.expected_repository_id:
            raise AnchorBackendError("Off-server repository identity mismatch.")
        return repository_id

    def _validate_version(self) -> None:
        try:
            version = self._run(["--version"]).stdout.decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise AnchorBackendError(
                "Image safety Borg version output is malformed or is a prerelease."
            ) from error
        match = BORG_STABLE_VERSION_RE.fullmatch(version)
        if not match:
            raise AnchorBackendError(
                "Image safety Borg version output is malformed or is a prerelease."
            )
        parsed = tuple(int(part) for part in match.groups())
        if not MINIMUM_BORG_VERSION <= parsed < MAXIMUM_BORG_VERSION:
            raise AnchorBackendError(
                "Image safety anchor requires Borg >=1.2.8 and <1.3.0."
            )

    def initialize_repository(self) -> str:
        if self.config.expected_repository_id != "0" * 64:
            raise AnchorBackendError(
                "Repository initialization requires the explicit all-zero pending identity."
            )
        self._validate_version()
        self._run(
            [
                "init",
                "--append-only",
                "--encryption=repokey-blake2",
                "--remote-path",
                self.config.remote_path,
                self.config.repository,
            ]
        )
        return self._repository_id_unchecked()

    def export_recovery_key(self, destination: Path) -> str:
        self.verified_repository_id()
        if not destination.is_absolute() or destination.exists() or destination.is_symlink():
            raise AnchorBackendError(
                "Recovery key destination must be a new absolute non-symlink path."
            )
        parent = destination.parent
        if not parent.is_dir() or parent.is_symlink() or parent.stat().st_mode & 0o022:
            raise AnchorBackendError("Recovery key destination parent is unsafe.")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".image-safety-recovery.", dir=parent
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        temporary_path.unlink()
        try:
            self._run(
                [
                    "key",
                    "export",
                    "--remote-path",
                    self.config.remote_path,
                    self.config.repository,
                    str(temporary_path),
                ]
            )
            if not temporary_path.is_file() or temporary_path.is_symlink():
                raise AnchorBackendError("Borg recovery key export is missing or unsafe.")
            if temporary_path.stat().st_size == 0:
                raise AnchorBackendError("Borg recovery key export is empty.")
            temporary_path.chmod(0o600)
            os.link(temporary_path, destination)
            return hashlib.sha256(destination.read_bytes()).hexdigest()
        except FileExistsError as error:
            raise AnchorBackendError("Recovery key destination already exists.") from error
        finally:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    def _repository_id_unchecked(self) -> str:
        result = self._run(
            ["info", "--remote-path", self.config.remote_path, "--json", self.config.repository]
        )
        try:
            repository_id = json.loads(result.stdout)["repository"]["id"].lower()
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise AnchorBackendError("Borg repository identity could not be parsed.") from error
        if not REPOSITORY_ID_RE.fullmatch(repository_id):
            raise AnchorBackendError("Borg repository identity is invalid.")
        return repository_id

    def read(self, archive_name: str) -> bytes | None:
        self._require_archive_name(archive_name)
        listed = self._run(
            [
                "list", "--remote-path", self.config.remote_path, "--json",
                "--glob-archives", archive_name, self.config.repository,
            ]
        )
        try:
            archives = json.loads(listed.stdout).get("archives", [])
        except (AttributeError, json.JSONDecodeError) as error:
            raise AnchorBackendError("Borg archive list could not be parsed.") from error
        if not archives:
            return None
        if [archive.get("name") for archive in archives] != [archive_name]:
            raise AnchorBackendError("Borg archive lookup was not exact.")
        result = self._run(
            [
                "extract", "--remote-path", self.config.remote_path, "--stdout",
                f"{self.config.repository}::{archive_name}", "anchor.json",
            ]
        )
        return result.stdout

    def create(self, archive_name: str, content: bytes) -> None:
        self._require_archive_name(archive_name)
        with tempfile.TemporaryDirectory(
            prefix="image-safety-anchor-", dir=self.config.state_root
        ) as temporary:
            temporary_path = Path(temporary)
            anchor_path = temporary_path / "anchor.json"
            anchor_path.write_bytes(content)
            anchor_path.chmod(0o600)
            self._run(
                [
                    "create", "--remote-path", self.config.remote_path,
                    f"{self.config.repository}::{archive_name}", "anchor.json",
                ],
                cwd=temporary_path,
            )

    def list_archives(self, prefix: str) -> list[str]:
        result = self._run(
            [
                "list", "--remote-path", self.config.remote_path, "--json",
                "--glob-archives", f"{prefix}*", self.config.repository,
            ]
        )
        try:
            return [item["name"] for item in json.loads(result.stdout).get("archives", [])]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise AnchorBackendError("Borg archive list could not be parsed.") from error

    def _run(
        self, arguments: list[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        environment = {
            "HOME": "/nonexistent",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "BORG_CACHE_DIR": str(self.config.state_root / "borg" / "cache"),
            "BORG_CONFIG_DIR": str(self.config.state_root / "borg" / "config"),
            "BORG_SECURITY_DIR": str(self.config.state_root / "borg" / "security"),
            "BORG_PASSCOMMAND": f"cat {self.config.passphrase_file}",
            "BORG_RSH": (
                f"ssh -i {self.config.ssh_key} -o IdentitiesOnly=yes "
                "-o BatchMode=yes -o StrictHostKeyChecking=yes "
                f"-o UserKnownHostsFile={self.config.known_hosts} "
                "-o ConnectTimeout=15 -p 23"
            ),
        }
        try:
            return subprocess.run(
                [self.config.borg_bin, *arguments],
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=300,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise AnchorBackendError("Borg anchor operation failed.") from error

    @staticmethod
    def _require_archive_name(value: str) -> None:
        if not re.fullmatch(r"image-safety-[A-Za-z0-9_.-]{1,240}", value):
            raise AnchorBackendError("Unsafe Borg archive name.")

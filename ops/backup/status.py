#!/usr/bin/env python3
"""Write the non-sensitive backup status file and parse Borg JSON safely."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath


SAFE_ARCHIVE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_STAGE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def load_status(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "format_version": 1,
            "last_start": None,
            "last_success": None,
            "last_error": None,
            "archive": None,
            "dump_verification": "unknown",
            "repository_verification": "unknown",
            "last_restore_success": None,
            "last_success_archive": None,
            "last_restore_archive": None,
            "backup_state": "unknown",
            "restore_state": "unknown",
        }
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict) or value.get("format_version") != 1:
        raise SystemExit("unsupported backup status format")
    return value


def atomic_write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".status.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def update_status(args: argparse.Namespace) -> None:
    path = Path(args.path)
    value = load_status(path)
    if args.event == "start":
        value["last_start"] = args.timestamp
        value["last_error"] = None
        value["dump_verification"] = "pending"
        value["repository_verification"] = "pending"
        value["backup_state"] = "pending"
    elif args.event == "success":
        if not SAFE_ARCHIVE.fullmatch(args.archive or ""):
            raise SystemExit("unsafe archive name")
        value["last_success"] = args.timestamp
        value["last_error"] = None
        value["archive"] = args.archive
        value["last_success_archive"] = args.archive
        value["dump_verification"] = "passed"
        value["repository_verification"] = "passed"
        value["backup_state"] = "passed"
    elif args.event == "error":
        if not SAFE_STAGE.fullmatch(args.stage or ""):
            raise SystemExit("unsafe error stage")
        value["last_error"] = {"at": args.timestamp, "stage": args.stage}
        if args.stage == "restore":
            value["restore_state"] = "failed"
        elif args.stage != "weekly_verify":
            value["backup_state"] = "failed"
        if args.stage in {"dump", "dump_verify"}:
            value["dump_verification"] = "failed"
        if args.stage in {"repository", "weekly_verify", "create", "prune", "compact"}:
            value["repository_verification"] = "failed"
    elif args.event == "repository-verified":
        value["repository_verification"] = "passed"
        if isinstance(value.get("last_error"), dict) and value["last_error"].get("stage") == "weekly_verify":
            value["last_error"] = None
    elif args.event == "restore-success":
        if not SAFE_ARCHIVE.fullmatch(args.archive or ""):
            raise SystemExit("unsafe archive name")
        value["last_restore_success"] = args.timestamp
        value["archive"] = args.archive
        value["last_restore_archive"] = args.archive
        value["restore_state"] = "passed"
        if isinstance(value.get("last_error"), dict) and value["last_error"].get("stage") == "restore":
            value["last_error"] = None
    atomic_write(path, value)


def repository_id() -> None:
    value = json.load(os.sys.stdin)
    repository = value.get("repository")
    if not isinstance(repository, dict):
        raise SystemExit("Borg output did not contain repository metadata")
    result = repository.get("id")
    if not isinstance(result, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", result):
        raise SystemExit("Borg output did not contain a valid repository id")
    print(result.lower())


def latest_archive() -> None:
    value = json.load(os.sys.stdin)
    archives = value.get("archives")
    if not isinstance(archives, list) or not archives:
        raise SystemExit("no Borg archives found")
    names = [item.get("name") for item in archives if isinstance(item, dict)]
    names = [name for name in names if isinstance(name, str) and SAFE_ARCHIVE.fullmatch(name)]
    if not names:
        raise SystemExit("no safe Borg archive name found")
    print(max(names))


def repository_summary() -> None:
    value = json.load(os.sys.stdin)
    if not isinstance(value, dict):
        raise SystemExit("Borg repository metadata is invalid")
    archives = value.get("archives")
    if not isinstance(archives, list) or not archives:
        raise SystemExit("no Borg archives found")
    names: list[str] = []
    for item in archives:
        if not isinstance(item, dict):
            raise SystemExit("Borg archive metadata is invalid")
        name = item.get("name")
        if not isinstance(name, str) or not SAFE_ARCHIVE.fullmatch(name):
            raise SystemExit("Borg repository contains an unsafe archive name")
        names.append(name)
    print("repository_available=yes")
    print(f"archive_count={len(names)}")
    print(f"latest_archive={max(names)}")


def safe_member(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and "\\" not in value


def restore_members() -> None:
    members = {line.rstrip("\n") for line in os.sys.stdin}
    if not members or any(not safe_member(member) for member in members):
        raise SystemExit("archive member list is empty or unsafe")
    candidates: list[PurePosixPath] = []
    for member in members:
        path = PurePosixPath(member)
        if path.name != "database.dump":
            continue
        parent = path.parent
        required = {
            str(parent / "database.dump"),
            str(parent / "manifest.txt"),
            str(parent / "checksums.sha256"),
        }
        if required.issubset(members):
            candidates.append(parent)
    if len(candidates) != 1:
        raise SystemExit("archive does not contain exactly one safe staged backup set")
    parent = candidates[0]
    print(parent / "database.dump")
    print(parent / "manifest.txt")
    print(parent / "checksums.sha256")


def validate_checksums(path: Path) -> None:
    filenames: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            match = re.fullmatch(r"[0-9a-fA-F]{64} [ *]([^/\\\n]+)\n?", line)
            if not match or match.group(1) in {".", ".."}:
                raise SystemExit("unsafe checksum manifest")
            filenames.add(match.group(1))
    if "database.dump" not in filenames:
        raise SystemExit("checksum manifest does not cover database.dump")


def activation_ready(path: Path) -> None:
    value = load_status(path)
    archive = value.get("archive")
    if not isinstance(archive, str) or not SAFE_ARCHIVE.fullmatch(archive):
        raise SystemExit("no safe successful archive is recorded")
    if not value.get("last_success"):
        raise SystemExit("no successful backup is recorded")
    if not value.get("last_restore_success"):
        raise SystemExit("no successful isolated restore is recorded")
    if value.get("dump_verification") != "passed":
        raise SystemExit("database dump verification has not passed")
    if value.get("repository_verification") != "passed":
        raise SystemExit("repository verification has not passed")
    if value.get("backup_state") != "passed":
        raise SystemExit("latest backup attempt has not passed")
    if value.get("restore_state") != "passed":
        raise SystemExit("latest isolated restore has not passed")
    if value.get("last_success_archive") != archive or value.get("last_restore_archive") != archive:
        raise SystemExit("backup and restore do not refer to the same archive")
    if value.get("last_error"):
        raise SystemExit("the latest recorded operation has an unresolved error")
    print(archive)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    update = subparsers.add_parser("update")
    update.add_argument("--path", required=True)
    update.add_argument(
        "--event",
        required=True,
        choices=("start", "success", "error", "repository-verified", "restore-success"),
    )
    update.add_argument("--timestamp", required=True)
    update.add_argument("--archive")
    update.add_argument("--stage")

    subparsers.add_parser("repository-id")
    subparsers.add_parser("latest-archive")
    subparsers.add_parser("repository-summary")
    subparsers.add_parser("restore-members")
    checksums = subparsers.add_parser("validate-checksums")
    checksums.add_argument("--path", required=True)
    activation = subparsers.add_parser("activation-ready")
    activation.add_argument("--path", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "update":
        update_status(args)
    elif args.command == "repository-id":
        repository_id()
    elif args.command == "latest-archive":
        latest_archive()
    elif args.command == "repository-summary":
        repository_summary()
    elif args.command == "restore-members":
        restore_members()
    elif args.command == "validate-checksums":
        validate_checksums(Path(args.path))
    elif args.command == "activation-ready":
        activation_ready(Path(args.path))


if __name__ == "__main__":
    main()

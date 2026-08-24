from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from .anchor import (
    BorgAnchorBackend,
    BorgAnchorConfig,
    RESTORE_MODES,
    anchor_current_head,
    restore_latest_anchor,
)
from .bridge import SafetyBridgeOperations, SafetyBridgeServer, systemd_listener
from .ledger import (
    PublicImageSafetyLedger,
    ReservationRendition,
    activation_event_id,
    reservation_event_id,
)


def _ledger_path() -> Path:
    value = os.environ.get("IMAGE_SAFETY_LEDGER_PATH", "")
    if not value or not Path(value).is_absolute():
        raise ValueError("IMAGE_SAFETY_LEDGER_PATH must be an absolute path.")
    return Path(value)


def _backend() -> tuple[BorgAnchorConfig, BorgAnchorBackend]:
    config = BorgAnchorConfig.from_environment()
    return config, BorgAnchorBackend(config)


def _anchor(ledger: PublicImageSafetyLedger) -> dict[str, object]:
    config, backend = _backend()
    return asdict(
        anchor_current_head(
            ledger, backend, expected_repository_id=config.expected_repository_id
        )
    )


def _load_reservation(path: str) -> dict[str, object]:
    reservation_path = Path(path)
    if not reservation_path.is_absolute() or not reservation_path.is_file():
        raise ValueError("Reservation input must be an existing absolute file.")
    if reservation_path.is_symlink() or reservation_path.stat().st_mode & 0o077:
        raise ValueError("Reservation input must be a private non-symlink file.")
    value = json.loads(reservation_path.read_text(encoding="utf-8"))
    required = {
        "tenant_id",
        "organization_id",
        "selection_id",
        "selection_revision",
        "rendition_set_id",
        "renditions",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Reservation input has an unknown schema.")
    if not isinstance(value["renditions"], list):
        raise ValueError("Reservation renditions must be a list.")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kreative-norge-image-safety")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    subparsers.add_parser("repository-init")
    recovery = subparsers.add_parser("repository-key-export")
    recovery.add_argument("--destination", required=True)
    reserve = subparsers.add_parser("reserve")
    reserve.add_argument("--event-id")
    reserve.add_argument("--reservation-file", required=True)
    for name in ("activate", "retire", "deny"):
        transition = subparsers.add_parser(name)
        transition.add_argument("--event-id", required=True)
        transition.add_argument("--release-id", required=True)
        if name in {"retire", "deny"}:
            transition.add_argument("--reason-code", required=True)
    subparsers.add_parser("anchor")
    subparsers.add_parser("health")
    subparsers.add_parser("rebuild")
    subparsers.add_parser("upgrade-v2")
    restore = subparsers.add_parser("restore-latest")
    restore.add_argument("--destination", required=True)
    restore.add_argument(
        "--recovery-mode",
        choices=sorted(RESTORE_MODES),
        required=True,
        help=(
            "Required assurance: incident-recovered is valid only after separate "
            "append-only transaction recovery."
        ),
    )
    restore.add_argument(
        "--expected-authoritative-cursor",
        type=int,
        help="Required recovered cursor for incident-recovered mode.",
    )
    restore.add_argument(
        "--expected-authoritative-event-hash",
        help="Required recovered full event head hash for incident-recovered mode.",
    )
    subparsers.add_parser("bridge")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    ledger = PublicImageSafetyLedger(_ledger_path())
    if arguments.command == "repository-init":
        _, backend = _backend()
        result = {"repository_id": backend.initialize_repository()}
    elif arguments.command == "repository-key-export":
        _, backend = _backend()
        destination = Path(arguments.destination)
        result = {
            "destination": str(destination),
            "repository_id": backend.verified_repository_id(),
            "sha256": backend.export_recovery_key(destination),
        }
    elif arguments.command == "init":
        ledger.initialize()
        result = _anchor(ledger)
    elif arguments.command == "reserve":
        data = _load_reservation(arguments.reservation_file)
        expected_event_id = reservation_event_id(
            tenant_id=data["tenant_id"],
            organization_id=data["organization_id"],
            selection_id=data["selection_id"],
            selection_revision=data["selection_revision"],
        )
        if arguments.event_id is not None and arguments.event_id != expected_event_id:
            raise ValueError("Reservation event ID must match the canonical selection identity.")
        event = ledger.reserve_or_get(
            tenant_id=data["tenant_id"],
            organization_id=data["organization_id"],
            selection_id=data["selection_id"],
            selection_revision=data["selection_revision"],
            rendition_set_id=data["rendition_set_id"],
            renditions=(ReservationRendition(**item) for item in data["renditions"]),
        )
        result = {"event": asdict(event), "anchor": _anchor(ledger)}
    elif arguments.command == "activate":
        expected_event_id = activation_event_id(arguments.release_id)
        if arguments.event_id != expected_event_id:
            raise ValueError("Activation event ID must match the canonical release identity.")
        event = ledger.activate_or_get(release_id=arguments.release_id)
        result = {"event": asdict(event), "anchor": _anchor(ledger)}
    elif arguments.command == "retire":
        event = ledger.retire_release(
            event_id=arguments.event_id,
            release_id=arguments.release_id,
            reason_code=arguments.reason_code,
        )
        print(json.dumps({"local_event": asdict(event)}, sort_keys=True), flush=True)
        result = _anchor(ledger)
    elif arguments.command == "deny":
        raise ValueError(
            "Legacy CLI deny is disabled; use the scoped Django formal takedown "
            "action so release and tenant checksum deny are atomic."
        )
    elif arguments.command == "anchor":
        result = _anchor(ledger)
    elif arguments.command == "health":
        config = BorgAnchorConfig.from_environment()
        health = ledger.health(expected_repository_id=config.expected_repository_id)
        print(json.dumps(asdict(health), sort_keys=True))
        return 0 if health.ready else 1
    elif arguments.command == "rebuild":
        result = asdict(ledger.rebuild())
    elif arguments.command == "upgrade-v2":
        before = ledger.head()
        after = ledger.upgrade_schema_v2()
        result = {
            "before": asdict(before),
            "after": asdict(after),
            "schema_version": ledger.schema_version(),
        }
    elif arguments.command == "restore-latest":
        config, backend = _backend()
        restored = restore_latest_anchor(
            backend,
            expected_repository_id=config.expected_repository_id,
            destination=arguments.destination,
            recovery_mode=arguments.recovery_mode,
            expected_authoritative_cursor=arguments.expected_authoritative_cursor,
            expected_authoritative_event_hash=(
                arguments.expected_authoritative_event_hash
            ),
        )
        result = {"recovery_mode": arguments.recovery_mode, **asdict(restored.head())}
    elif arguments.command == "bridge":
        config, backend = _backend()
        operations = SafetyBridgeOperations(
            ledger=ledger,
            anchor_backend=backend,
            expected_repository_id=config.expected_repository_id,
        )
        server = SafetyBridgeServer(
            listener=systemd_listener(),
            operations=operations,
        )
        server.serve_forever()
        return 0
    else:  # pragma: no cover
        raise AssertionError("unreachable command")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"image-safety: ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

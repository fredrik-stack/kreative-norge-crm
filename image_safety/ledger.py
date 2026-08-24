from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any, Iterable, Mapping
import uuid

from .release_keys import (
    REQUIRED_RELEASE_VARIANTS,
    build_public_release_key,
    canonical_release_id,
)


SCHEMA_VERSION = 1
LATEST_LEDGER_SCHEMA_VERSION = 2
APPLICATION_ID = 0x4B4E4953  # "KNIS"
GENESIS_HASH = "0" * 64
EVENT_TYPES = frozenset(
    {
        "release_reserved",
        "release_activated",
        "release_retired",
        "release_denied",
    }
)
V2_EVENT_TYPES = frozenset({"tenant_checksum_denied"})
ALL_EVENT_TYPES = EVENT_TYPES | V2_EVENT_TYPES
TERMINAL_STATES = frozenset({"retired", "denied"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
REASON_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class ImageSafetyLedgerError(Exception):
    pass


class InvalidLedgerError(ImageSafetyLedgerError):
    pass


class EventConflictError(ImageSafetyLedgerError):
    pass


class InvalidTransitionError(ImageSafetyLedgerError):
    pass


class AnchorConflictError(ImageSafetyLedgerError):
    pass


@dataclass(frozen=True)
class ReservationRendition:
    variant: str
    output_format: str
    artifact_storage_key: str
    artifact_checksum_sha256: str


@dataclass(frozen=True)
class AppendedEvent:
    sequence: int
    event_id: str
    event_type: str
    release_id: str
    payload: Mapping[str, Any]
    event_hash: str
    idempotent_retry: bool


@dataclass(frozen=True)
class LedgerHead:
    ledger_id: str
    sequence: int
    event_hash: str


@dataclass(frozen=True)
class LedgerHealth:
    ready: bool
    code: str
    detail: str
    ledger_id: str | None = None
    event_cursor: int | None = None
    read_cursor: int | None = None
    anchor_cursor: int | None = None
    repository_id: str | None = None


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _require_positive_int(label: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidLedgerError(f"{label} must be a positive integer.")
    return value


def _require_event_id(value: str) -> str:
    if not isinstance(value, str) or not EVENT_ID_RE.fullmatch(value):
        raise InvalidLedgerError("Event ID is not canonical.")
    return value


def reservation_event_id(
    *, tenant_id: int, organization_id: int, selection_id: int, selection_revision: int
) -> str:
    values = (
        _require_positive_int("Tenant ID", tenant_id),
        _require_positive_int("Organization ID", organization_id),
        _require_positive_int("Selection ID", selection_id),
        _require_positive_int("Selection revision", selection_revision),
    )
    return _require_event_id(
        "release-reservation:v1:" + ":".join(str(value) for value in values)
    )


def activation_event_id(release_id: uuid.UUID | str) -> str:
    return _require_event_id(f"release-activation:v1:{canonical_release_id(release_id)}")


def release_denial_event_id(release_id: uuid.UUID | str) -> str:
    return _require_event_id(f"release-denial:v1:{canonical_release_id(release_id)}")


def tenant_checksum_denial_event_id(*, tenant_id: int, source_checksum_sha256: str) -> str:
    return _require_event_id(
        "tenant-checksum-denial:v1:"
        f"{_require_positive_int('Tenant ID', tenant_id)}:"
        f"{_require_sha256('Source checksum', source_checksum_sha256)}"
    )


def _require_sha256(label: str, value: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise InvalidLedgerError(f"{label} must be a lowercase SHA-256 digest.")
    return value


def _require_artifact_key(value: str) -> str:
    if not isinstance(value, str) or len(value) > 1024:
        raise InvalidLedgerError("Artifact storage key is invalid.")
    if value.startswith("/") or "\\" in value or "?" in value or "#" in value:
        raise InvalidLedgerError("Artifact storage key must be a relative storage key.")
    parts = value.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise InvalidLedgerError("Artifact storage key is not normalized.")
    return value


def _event_hash(
    *,
    sequence: int,
    event_id: str,
    event_type: str,
    release_id: str,
    payload_sha256: str,
    previous_event_hash: str,
    created_at_utc: str,
) -> str:
    return _sha256(
        _canonical_json(
            {
                "event_id": event_id,
                "event_type": event_type,
                "created_at_utc": created_at_utc,
                "payload_sha256": payload_sha256,
                "previous_event_hash": previous_event_hash,
                "release_id": release_id,
                "sequence": sequence,
            }
        )
    )


class PublicImageSafetyLedger:
    """Single-writer append-only ledger with a rebuildable local read model."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def initialize(self, *, ledger_id: uuid.UUID | str | None = None) -> LedgerHead:
        if self.path.exists():
            return self.head()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        value = canonical_release_id(ledger_id or uuid.uuid4())
        connection = sqlite3.connect(self.path, isolation_level=None)
        try:
            self._configure(connection)
            connection.executescript(_SCHEMA)
            connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                "INSERT INTO ledger_metadata(key, value) VALUES (?, ?)",
                (
                    ("schema_version", str(SCHEMA_VERSION)),
                    ("ledger_id", value),
                    ("created_at_utc", _utc_now()),
                ),
            )
            connection.execute(
                "INSERT INTO read_cursor(singleton, event_sequence, event_hash) "
                "VALUES (1, 0, ?)",
                (GENESIS_HASH,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            connection.close()
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            raise
        finally:
            if connection:
                connection.close()
        os.chmod(self.path, 0o600)
        return LedgerHead(value, 0, GENESIS_HASH)

    def schema_version(self) -> int:
        with self._connect(read_only=True) as connection:
            return self._database_schema_version(connection)

    def upgrade_schema_v2(self) -> LedgerHead:
        """Add v2 storage/read-models without rewriting any v1 ledger event."""
        with self._connect() as connection:
            version = self._database_schema_version(connection)
            if version == LATEST_LEDGER_SCHEMA_VERSION:
                return self.head()
            if version != SCHEMA_VERSION:
                raise InvalidLedgerError("Ledger schema cannot be upgraded safely.")
            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.execute(
                    "SELECT event_sequence, event_hash FROM read_cursor WHERE singleton = 1"
                ).fetchone()
                if cursor is None:
                    raise InvalidLedgerError("Read cursor is missing.")
                for statement in _SCHEMA_V2_STATEMENTS:
                    connection.execute(statement)
                # v1 could already contain a concrete release_denied event. The
                # new legacy guard is a derived read-model, so seed it from the
                # immutable reservation snapshots without touching old events.
                denied_rows = connection.execute(
                    "SELECT current_sequence, reservation_payload_json "
                    "FROM release_state WHERE state = 'denied'"
                ).fetchall()
                for row in denied_rows:
                    reservation = json.loads(row["reservation_payload_json"])
                    connection.execute(
                        "INSERT INTO legacy_blocked_organizations("
                        "tenant_id, organization_id, first_denial_sequence"
                        ") VALUES (?, ?, ?)",
                        (
                            reservation["tenant_id"],
                            reservation["organization_id"],
                            row["current_sequence"],
                        ),
                    )
                connection.executemany(
                    "INSERT INTO ledger_metadata(key, value) VALUES (?, ?)",
                    (
                        ("v1_event_cursor", str(cursor["event_sequence"])),
                        ("upgraded_to_v2_at_utc", _utc_now()),
                    ),
                )
                connection.execute(
                    "UPDATE ledger_metadata SET value = ? WHERE key = 'schema_version'",
                    (str(LATEST_LEDGER_SCHEMA_VERSION),),
                )
                connection.execute(
                    f"PRAGMA user_version = {LATEST_LEDGER_SCHEMA_VERSION}"
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self.head()

    def reserve_release(
        self,
        *,
        event_id: str,
        release_id: uuid.UUID | str,
        tenant_id: int,
        organization_id: int,
        selection_id: int,
        selection_revision: int,
        rendition_set_id: int,
        renditions: Iterable[ReservationRendition],
    ) -> AppendedEvent:
        canonical_id = canonical_release_id(release_id)
        payload = self._reservation_payload(
            release_id=canonical_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            selection_id=selection_id,
            selection_revision=selection_revision,
            rendition_set_id=rendition_set_id,
            renditions=renditions,
        )
        return self.append_event(
            event_id=event_id,
            event_type="release_reserved",
            release_id=canonical_id,
            payload=payload,
        )

    def reserve_or_get(
        self,
        *,
        tenant_id: int,
        organization_id: int,
        selection_id: int,
        selection_revision: int,
        rendition_set_id: int,
        renditions: Iterable[ReservationRendition],
    ) -> AppendedEvent:
        event_id = reservation_event_id(
            tenant_id=tenant_id,
            organization_id=organization_id,
            selection_id=selection_id,
            selection_revision=selection_revision,
        )
        canonical_renditions = tuple(renditions)
        # Validate the complete caller snapshot before entering the writer path.
        # The fixed UUID is validation-only; the permanent UUID is generated
        # below while the SQLite writer lock is held.
        self._reservation_payload(
            release_id="00000000-0000-4000-8000-000000000000",
            tenant_id=tenant_id,
            organization_id=organization_id,
            selection_id=selection_id,
            selection_revision=selection_revision,
            rendition_set_id=rendition_set_id,
            renditions=canonical_renditions,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = self._event_row_by_id(connection, event_id)
                release_id = (
                    existing["release_id"] if existing is not None else str(uuid.uuid4())
                )
                payload = self._reservation_payload(
                    release_id=release_id,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    selection_id=selection_id,
                    selection_revision=selection_revision,
                    rendition_set_id=rendition_set_id,
                    renditions=canonical_renditions,
                )
                event = self._append_event_in_transaction(
                    connection,
                    event_id=event_id,
                    event_type="release_reserved",
                    release_id=release_id,
                    payload=payload,
                )
                connection.commit()
                return event
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _reservation_payload(
        *,
        release_id: uuid.UUID | str,
        tenant_id: int,
        organization_id: int,
        selection_id: int,
        selection_revision: int,
        rendition_set_id: int,
        renditions: Iterable[ReservationRendition],
    ) -> dict[str, Any]:
        canonical_id = canonical_release_id(release_id)
        variants: dict[str, dict[str, str]] = {}
        for rendition in renditions:
            if rendition.variant in variants:
                raise InvalidLedgerError("Reservation contains a duplicate variant.")
            variants[rendition.variant] = {
                "artifact_checksum_sha256": _require_sha256(
                    "Artifact checksum", rendition.artifact_checksum_sha256
                ),
                "artifact_storage_key": _require_artifact_key(
                    rendition.artifact_storage_key
                ),
                "output_format": rendition.output_format,
                "public_storage_key": build_public_release_key(
                    canonical_id, rendition.variant, rendition.output_format
                ),
            }
        if set(variants) != REQUIRED_RELEASE_VARIANTS:
            raise InvalidLedgerError(
                "Reservation requires exactly square, landscape, and share renditions."
            )
        payload = {
            "organization_id": _require_positive_int(
                "Organization ID", organization_id
            ),
            "release_id": canonical_id,
            "rendition_set_id": _require_positive_int(
                "Rendition set ID", rendition_set_id
            ),
            "schema_version": SCHEMA_VERSION,
            "selection_id": _require_positive_int("Selection ID", selection_id),
            "selection_revision": _require_positive_int(
                "Selection revision", selection_revision
            ),
            "tenant_id": _require_positive_int("Tenant ID", tenant_id),
            "variants": variants,
        }
        return payload

    def activate_release(self, *, event_id: str, release_id: uuid.UUID | str) -> AppendedEvent:
        return self._append_transition(event_id, "release_activated", release_id)

    def activate_or_get(
        self,
        *,
        release_id: uuid.UUID | str,
        tenant_id: int | None = None,
        source_checksum_sha256: str | None = None,
    ) -> AppendedEvent:
        canonical_id = canonical_release_id(release_id)
        guarded_activation = tenant_id is not None or source_checksum_sha256 is not None
        if guarded_activation:
            tenant_id = _require_positive_int("Tenant ID", tenant_id)
            source_checksum_sha256 = _require_sha256(
                "Source checksum", source_checksum_sha256
            )
        event_id = activation_event_id(canonical_id)
        payload = {"release_id": canonical_id, "schema_version": SCHEMA_VERSION}
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                state = connection.execute(
                    "SELECT state, reservation_payload_json FROM release_state "
                    "WHERE release_id = ?",
                    (canonical_id,),
                ).fetchone()
                if state is None:
                    raise InvalidTransitionError("Release ID is unknown.")
                if state["state"] in TERMINAL_STATES:
                    raise InvalidTransitionError("Terminal releases cannot be activated.")
                if guarded_activation:
                    reservation = json.loads(state["reservation_payload_json"])
                    if reservation["tenant_id"] != tenant_id:
                        raise InvalidTransitionError(
                            "Release tenant does not match the activation request."
                        )
                    if self._database_schema_version(connection) >= LATEST_LEDGER_SCHEMA_VERSION:
                        denied = connection.execute(
                            "SELECT 1 FROM tenant_checksum_denials "
                            "WHERE tenant_id = ? AND source_checksum_sha256 = ?",
                            (tenant_id, source_checksum_sha256),
                        ).fetchone()
                        if denied is not None:
                            raise InvalidTransitionError(
                                "Denied source bytes cannot be activated."
                            )
                event = self._append_event_in_transaction(
                    connection,
                    event_id=event_id,
                    event_type="release_activated",
                    release_id=canonical_id,
                    payload=payload,
                )
                connection.commit()
                return event
            except Exception:
                connection.rollback()
                raise

    def retire_release(
        self, *, event_id: str, release_id: uuid.UUID | str, reason_code: str
    ) -> AppendedEvent:
        return self._append_transition(event_id, "release_retired", release_id, reason_code)

    def deny_release(
        self, *, event_id: str, release_id: uuid.UUID | str, reason_code: str
    ) -> AppendedEvent:
        return self._append_transition(event_id, "release_denied", release_id, reason_code)

    def deny_release_and_checksum(
        self,
        *,
        release_id: uuid.UUID | str,
        tenant_id: int,
        organization_id: int,
        source_checksum_sha256: str,
        reason_code: str,
    ) -> tuple[AppendedEvent, AppendedEvent]:
        """Atomically deny one release and its source bytes inside one tenant."""
        canonical_id = canonical_release_id(release_id)
        tenant_id = _require_positive_int("Tenant ID", tenant_id)
        organization_id = _require_positive_int("Organization ID", organization_id)
        source_checksum_sha256 = _require_sha256(
            "Source checksum", source_checksum_sha256
        )
        if not isinstance(reason_code, str) or not REASON_RE.fullmatch(reason_code):
            raise InvalidLedgerError("Reason code is not canonical.")
        release_event_id = release_denial_event_id(canonical_id)
        checksum_event_id = tenant_checksum_denial_event_id(
            tenant_id=tenant_id,
            source_checksum_sha256=source_checksum_sha256,
        )
        release_payload = {
            "release_id": canonical_id,
            "reason_code": reason_code,
            "schema_version": SCHEMA_VERSION,
        }
        checksum_payload = {
            "schema_version": LATEST_LEDGER_SCHEMA_VERSION,
            "source_checksum_sha256": source_checksum_sha256,
            "tenant_id": tenant_id,
        }
        with self._connect() as connection:
            if self._database_schema_version(connection) != LATEST_LEDGER_SCHEMA_VERSION:
                raise InvalidLedgerError("Ledger schema v2 is required for formal takedown.")
            connection.execute("BEGIN IMMEDIATE")
            try:
                state = connection.execute(
                    "SELECT state, reservation_payload_json FROM release_state "
                    "WHERE release_id = ?",
                    (canonical_id,),
                ).fetchone()
                if state is None:
                    raise InvalidTransitionError("Release ID is unknown.")
                reservation = json.loads(state["reservation_payload_json"])
                if (
                    reservation["tenant_id"] != tenant_id
                    or reservation["organization_id"] != organization_id
                ):
                    raise InvalidTransitionError("Release scope does not match the request.")
                release_event = self._append_event_in_transaction(
                    connection,
                    event_id=release_event_id,
                    event_type="release_denied",
                    release_id=canonical_id,
                    payload=release_payload,
                )
                existing_checksum = self._event_row_by_id(
                    connection, checksum_event_id
                )
                if existing_checksum is None:
                    checksum_event = self._append_event_in_transaction(
                        connection,
                        event_id=checksum_event_id,
                        event_type="tenant_checksum_denied",
                        release_id=canonical_id,
                        payload=checksum_payload,
                    )
                else:
                    if (
                        existing_checksum["event_type"] != "tenant_checksum_denied"
                        or existing_checksum["payload_json"]
                        != _canonical_json(checksum_payload)
                    ):
                        raise EventConflictError(
                            "Checksum denial identity has a different canonical payload."
                        )
                    checksum_event = AppendedEvent(
                        sequence=existing_checksum["sequence"],
                        event_id=checksum_event_id,
                        event_type="tenant_checksum_denied",
                        release_id=existing_checksum["release_id"],
                        payload=checksum_payload,
                        event_hash=existing_checksum["event_hash"],
                        idempotent_retry=True,
                    )
                connection.commit()
                return release_event, checksum_event
            except Exception:
                connection.rollback()
                raise

    def checksum_denied(
        self, *, tenant_id: int, source_checksum_sha256: str
    ) -> bool:
        tenant_id = _require_positive_int("Tenant ID", tenant_id)
        source_checksum_sha256 = _require_sha256(
            "Source checksum", source_checksum_sha256
        )
        with self._connect(read_only=True) as connection:
            if self._database_schema_version(connection) < LATEST_LEDGER_SCHEMA_VERSION:
                return False
            return connection.execute(
                "SELECT 1 FROM tenant_checksum_denials "
                "WHERE tenant_id = ? AND source_checksum_sha256 = ?",
                (tenant_id, source_checksum_sha256),
            ).fetchone() is not None

    def organization_legacy_blocked(
        self, *, tenant_id: int, organization_id: int
    ) -> bool:
        tenant_id = _require_positive_int("Tenant ID", tenant_id)
        organization_id = _require_positive_int("Organization ID", organization_id)
        with self._connect(read_only=True) as connection:
            if self._database_schema_version(connection) < LATEST_LEDGER_SCHEMA_VERSION:
                return False
            return connection.execute(
                "SELECT 1 FROM legacy_blocked_organizations "
                "WHERE tenant_id = ? AND organization_id = ?",
                (tenant_id, organization_id),
            ).fetchone() is not None

    def _append_transition(
        self,
        event_id: str,
        event_type: str,
        release_id: uuid.UUID | str,
        reason_code: str | None = None,
    ) -> AppendedEvent:
        canonical_id = canonical_release_id(release_id)
        payload: dict[str, Any] = {
            "release_id": canonical_id,
            "schema_version": SCHEMA_VERSION,
        }
        if reason_code is not None:
            if not isinstance(reason_code, str) or not REASON_RE.fullmatch(reason_code):
                raise InvalidLedgerError("Reason code is not canonical.")
            payload["reason_code"] = reason_code
        return self.append_event(
            event_id=event_id,
            event_type=event_type,
            release_id=canonical_id,
            payload=payload,
        )

    def append_event(
        self,
        *,
        event_id: str,
        event_type: str,
        release_id: uuid.UUID | str,
        payload: Mapping[str, Any],
    ) -> AppendedEvent:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                event = self._append_event_in_transaction(
                    connection,
                    event_id=event_id,
                    event_type=event_type,
                    release_id=release_id,
                    payload=payload,
                )
                connection.commit()
                return event
            except Exception:
                connection.rollback()
                raise

    def _append_event_in_transaction(
        self,
        connection: sqlite3.Connection,
        *,
        event_id: str,
        event_type: str,
        release_id: uuid.UUID | str,
        payload: Mapping[str, Any],
    ) -> AppendedEvent:
        _require_event_id(event_id)
        if event_type not in ALL_EVENT_TYPES:
            raise InvalidLedgerError("Unknown event type.")
        ledger_schema_version = self._database_schema_version(connection)
        if event_type in V2_EVENT_TYPES and ledger_schema_version < LATEST_LEDGER_SCHEMA_VERSION:
            raise InvalidLedgerError("Ledger schema v2 is required for this event type.")
        canonical_id = canonical_release_id(release_id)
        canonical_payload = _canonical_json(payload)
        decoded_payload = json.loads(canonical_payload)
        self._validate_payload(event_type, canonical_id, decoded_payload)
        payload_hash = _sha256(canonical_payload)
        existing = self._event_row_by_id(connection, event_id)
        if existing is not None:
            if (
                existing["event_type"] != event_type
                or existing["release_id"] != canonical_id
                or existing["payload_json"] != canonical_payload
            ):
                raise EventConflictError(
                    "Event ID already exists with a different canonical payload."
                )
            return AppendedEvent(
                sequence=existing["sequence"],
                event_id=event_id,
                event_type=event_type,
                release_id=canonical_id,
                payload=decoded_payload,
                event_hash=existing["event_hash"],
                idempotent_retry=True,
            )

        cursor = connection.execute(
            "SELECT event_sequence, event_hash FROM read_cursor WHERE singleton = 1"
        ).fetchone()
        if cursor is None:
            raise InvalidLedgerError("Read cursor is missing.")
        database_head = self._database_event_head(connection)
        if cursor["event_sequence"] != database_head:
            raise InvalidLedgerError("Read cursor is stale; rebuild is required.")
        sequence = database_head + 1
        created_at_utc = _utc_now()
        event_hash = _event_hash(
            sequence=sequence,
            event_id=event_id,
            event_type=event_type,
            release_id=canonical_id,
            payload_sha256=payload_hash,
            previous_event_hash=cursor["event_hash"],
            created_at_utc=created_at_utc,
        )
        self._apply_to_database(
            connection,
            sequence=sequence,
            event_type=event_type,
            release_id=canonical_id,
            payload=decoded_payload,
        )
        table = (
            "ledger_events_v2"
            if ledger_schema_version >= LATEST_LEDGER_SCHEMA_VERSION
            else "ledger_events"
        )
        connection.execute(
            f"INSERT INTO {table}("
            "sequence, event_id, event_type, release_id, payload_json, "
            "payload_sha256, previous_event_hash, event_hash, created_at_utc"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sequence,
                event_id,
                event_type,
                canonical_id,
                canonical_payload,
                payload_hash,
                cursor["event_hash"],
                event_hash,
                created_at_utc,
            ),
        )
        connection.execute(
            "UPDATE read_cursor SET event_sequence = ?, event_hash = ? "
            "WHERE singleton = 1",
            (sequence, event_hash),
        )
        return AppendedEvent(
            sequence=sequence,
            event_id=event_id,
            event_type=event_type,
            release_id=canonical_id,
            payload=decoded_payload,
            event_hash=event_hash,
            idempotent_retry=False,
        )

    def _event_row_by_id(
        self, connection: sqlite3.Connection, event_id: str
    ) -> sqlite3.Row | None:
        row = connection.execute(
            "SELECT sequence, event_id, event_type, release_id, payload_json, "
            "event_hash FROM ledger_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if row is not None or self._database_schema_version(connection) < LATEST_LEDGER_SCHEMA_VERSION:
            return row
        return connection.execute(
            "SELECT sequence, event_id, event_type, release_id, payload_json, "
            "event_hash FROM ledger_events_v2 WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    def _database_event_head(self, connection: sqlite3.Connection) -> int:
        v1_head = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM ledger_events"
        ).fetchone()[0]
        if self._database_schema_version(connection) < LATEST_LEDGER_SCHEMA_VERSION:
            return v1_head
        v2_head = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM ledger_events_v2"
        ).fetchone()[0]
        return max(v1_head, v2_head)

    def _event_rows(self, connection: sqlite3.Connection):
        fields = (
            "sequence, event_id, event_type, release_id, payload_json, "
            "payload_sha256, previous_event_hash, event_hash, created_at_utc"
        )
        if self._database_schema_version(connection) < LATEST_LEDGER_SCHEMA_VERSION:
            return connection.execute(
                f"SELECT {fields} FROM ledger_events ORDER BY sequence"
            ).fetchall()
        return connection.execute(
            f"SELECT {fields} FROM ledger_events "
            f"UNION ALL SELECT {fields} FROM ledger_events_v2 ORDER BY sequence"
        ).fetchall()

    def head(self) -> LedgerHead:
        with self._connect(read_only=True) as connection:
            ledger_id = self._metadata(connection, "ledger_id")
            row = connection.execute(
                "SELECT event_sequence, event_hash FROM read_cursor WHERE singleton = 1"
            ).fetchone()
            if row is None:
                raise InvalidLedgerError("Read cursor is missing.")
            return LedgerHead(ledger_id, row["event_sequence"], row["event_hash"])

    def record_anchor_receipt(
        self,
        *,
        cursor: int,
        event_hash: str,
        archive_name: str,
        repository_id: str,
        bundle_sha256: str,
    ) -> None:
        _require_sha256("Event hash", event_hash)
        _require_sha256("Repository ID", repository_id)
        _require_sha256("Bundle checksum", bundle_sha256)
        if not isinstance(cursor, int) or cursor < 0:
            raise InvalidLedgerError("Anchor cursor is invalid.")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", archive_name):
            raise InvalidLedgerError("Anchor archive name is invalid.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            head = connection.execute(
                "SELECT event_sequence, event_hash FROM read_cursor WHERE singleton = 1"
            ).fetchone()
            if head is None or head["event_sequence"] != cursor or head["event_hash"] != event_hash:
                raise AnchorConflictError("Anchor receipt does not match the local ledger head.")
            existing = connection.execute(
                "SELECT event_hash, archive_name, repository_id, bundle_sha256 "
                "FROM anchor_receipts WHERE event_sequence = ?",
                (cursor,),
            ).fetchone()
            values = (event_hash, archive_name, repository_id, bundle_sha256)
            if existing is not None:
                if tuple(existing) != values:
                    raise AnchorConflictError(
                        "Anchor cursor already has a different immutable receipt."
                    )
                connection.rollback()
                return
            connection.execute(
                "INSERT INTO anchor_receipts("
                "event_sequence, event_hash, archive_name, repository_id, "
                "bundle_sha256, verified_at_utc"
                ") VALUES (?, ?, ?, ?, ?, ?)",
                (cursor, *values, _utc_now()),
            )
            connection.commit()

    def bundle_bytes(self) -> bytes:
        with self._connect(read_only=True) as connection:
            self._validate_database_identity(connection)
            ledger_id = self._metadata(connection, "ledger_id")
            rows = self._event_rows(connection)
            events = [dict(row) for row in rows]
            head = events[-1]["event_hash"] if events else GENESIS_HASH
            ledger_schema_version = self._database_schema_version(connection)
            has_v2_events = (
                ledger_schema_version >= LATEST_LEDGER_SCHEMA_VERSION
                and connection.execute(
                    "SELECT 1 FROM ledger_events_v2 LIMIT 1"
                ).fetchone()
                is not None
            )
            bundle: dict[str, Any] = {
                "bundle_schema_version": 2 if has_v2_events else 1,
                "event_cursor": len(events),
                "event_head_hash": head,
                "events": events,
                "ledger_id": ledger_id,
                "ledger_schema_version": (
                    LATEST_LEDGER_SCHEMA_VERSION if has_v2_events else SCHEMA_VERSION
                ),
            }
            if has_v2_events:
                bundle["v1_event_cursor"] = int(
                    self._metadata(connection, "v1_event_cursor")
                )
            self._validate_bundle(bundle)
            return (_canonical_json(bundle) + "\n").encode("utf-8")

    def write_bundle(self, destination: str | os.PathLike[str]) -> str:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        content = self.bundle_bytes()
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination_path.name}.", dir=destination_path.parent
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination_path)
            directory_descriptor = os.open(destination_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        return _sha256(content)

    @classmethod
    def restore_bundle(
        cls,
        *,
        bundle: bytes,
        destination: str | os.PathLike[str],
        archive_name: str,
        repository_id: str,
    ) -> "PublicImageSafetyLedger":
        try:
            decoded = json.loads(bundle.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidLedgerError("Anchor bundle is not canonical JSON.") from error
        cls._validate_bundle(decoded)
        if (_canonical_json(decoded) + "\n").encode("utf-8") != bundle:
            raise InvalidLedgerError("Anchor bundle encoding is not canonical.")
        destination_path = Path(destination)
        if destination_path.exists():
            raise InvalidLedgerError("Restore destination already exists.")
        ledger = cls(destination_path)
        ledger.initialize(ledger_id=decoded["ledger_id"])
        try:
            if decoded["ledger_schema_version"] == LATEST_LEDGER_SCHEMA_VERSION:
                ledger.upgrade_schema_v2()
            with ledger._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                if decoded["ledger_schema_version"] == LATEST_LEDGER_SCHEMA_VERSION:
                    connection.execute(
                        "UPDATE ledger_metadata SET value = ? "
                        "WHERE key = 'v1_event_cursor'",
                        (str(decoded["v1_event_cursor"]),),
                    )
                for event in decoded["events"]:
                    table = "ledger_events"
                    if (
                        decoded["ledger_schema_version"] == LATEST_LEDGER_SCHEMA_VERSION
                        and event["sequence"] > decoded["v1_event_cursor"]
                    ):
                        table = "ledger_events_v2"
                    connection.execute(
                        f"INSERT INTO {table}("
                        "sequence, event_id, event_type, release_id, payload_json, "
                        "payload_sha256, previous_event_hash, event_hash, created_at_utc"
                        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        tuple(event[key] for key in (
                            "sequence", "event_id", "event_type", "release_id",
                            "payload_json", "payload_sha256", "previous_event_hash",
                            "event_hash", "created_at_utc",
                        )),
                    )
                connection.commit()
            ledger.rebuild()
            ledger.record_anchor_receipt(
                cursor=decoded["event_cursor"],
                event_hash=decoded["event_head_hash"],
                archive_name=archive_name,
                repository_id=repository_id,
                bundle_sha256=_sha256(bundle),
            )
        except Exception:
            for suffix in ("", "-wal", "-shm"):
                try:
                    Path(f"{destination_path}{suffix}").unlink()
                except FileNotFoundError:
                    pass
            raise
        return ledger

    def rebuild(self) -> LedgerHead:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            states, checksum_denials, legacy_blocks, head_sequence, head_hash = self._replay(connection)
            connection.execute("DELETE FROM reserved_release_keys")
            connection.execute("DELETE FROM release_state")
            if self._database_schema_version(connection) >= LATEST_LEDGER_SCHEMA_VERSION:
                connection.execute("DELETE FROM tenant_checksum_denials")
                connection.execute("DELETE FROM legacy_blocked_organizations")
            for release_id, state in states.items():
                connection.execute(
                    "INSERT INTO release_state("
                    "release_id, state, reservation_payload_json, "
                    "reservation_sequence, current_sequence"
                    ") VALUES (?, ?, ?, ?, ?)",
                    (
                        release_id,
                        state["state"],
                        state["reservation_payload_json"],
                        state["reservation_sequence"],
                        state["current_sequence"],
                    ),
                )
                reservation = json.loads(state["reservation_payload_json"])
                connection.executemany(
                    "INSERT INTO reserved_release_keys(public_storage_key, release_id) "
                    "VALUES (?, ?)",
                    (
                        (rendition["public_storage_key"], release_id)
                        for rendition in reservation["variants"].values()
                    ),
                )
            if self._database_schema_version(connection) >= LATEST_LEDGER_SCHEMA_VERSION:
                connection.executemany(
                    "INSERT INTO tenant_checksum_denials("
                    "tenant_id, source_checksum_sha256, event_sequence"
                    ") VALUES (?, ?, ?)",
                    (
                        (tenant_id, checksum, sequence)
                        for (tenant_id, checksum), sequence in checksum_denials.items()
                    ),
                )
                connection.executemany(
                    "INSERT INTO legacy_blocked_organizations("
                    "tenant_id, organization_id, first_denial_sequence"
                    ") VALUES (?, ?, ?)",
                    (
                        (tenant_id, organization_id, sequence)
                        for (tenant_id, organization_id), sequence in legacy_blocks.items()
                    ),
                )
            connection.execute(
                "UPDATE read_cursor SET event_sequence = ?, event_hash = ? "
                "WHERE singleton = 1",
                (head_sequence, head_hash),
            )
            connection.commit()
            return LedgerHead(
                self._metadata(connection, "ledger_id"), head_sequence, head_hash
            )

    def health(self, *, expected_repository_id: str) -> LedgerHealth:
        if not self.path.is_file():
            return LedgerHealth(False, "ledger_missing", "Ledger file is missing.")
        try:
            expected_repository_id = _require_sha256(
                "Expected repository ID", expected_repository_id.lower()
            )
            with self._connect(read_only=True) as connection:
                self._validate_database_identity(connection)
                quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
                if quick_check != "ok":
                    raise InvalidLedgerError("SQLite quick_check failed.")
                ledger_id = self._metadata(connection, "ledger_id")
                states, checksum_denials, legacy_blocks, event_cursor, event_hash = self._replay(connection)
                cursor = connection.execute(
                    "SELECT event_sequence, event_hash FROM read_cursor WHERE singleton = 1"
                ).fetchone()
                if cursor is None or (
                    cursor["event_sequence"] != event_cursor
                    or cursor["event_hash"] != event_hash
                ):
                    return LedgerHealth(
                        False,
                        "read_cursor_stale",
                        "Derived cursor does not match replayed events.",
                        ledger_id,
                        event_cursor,
                        None if cursor is None else cursor["event_sequence"],
                    )
                database_states = {
                    row["release_id"]: {
                        "state": row["state"],
                        "reservation_payload_json": row["reservation_payload_json"],
                        "reservation_sequence": row["reservation_sequence"],
                        "current_sequence": row["current_sequence"],
                    }
                    for row in connection.execute(
                        "SELECT release_id, state, reservation_payload_json, "
                        "reservation_sequence, current_sequence FROM release_state"
                    )
                }
                if database_states != states:
                    return LedgerHealth(
                        False,
                        "read_model_mismatch",
                        "Derived release state does not match event replay.",
                        ledger_id,
                        event_cursor,
                        cursor["event_sequence"],
                    )
                if self._database_schema_version(connection) >= LATEST_LEDGER_SCHEMA_VERSION:
                    database_checksum_denials = {
                        (row["tenant_id"], row["source_checksum_sha256"]): row["event_sequence"]
                        for row in connection.execute(
                            "SELECT tenant_id, source_checksum_sha256, event_sequence "
                            "FROM tenant_checksum_denials"
                        )
                    }
                    if database_checksum_denials != checksum_denials:
                        return LedgerHealth(
                            False,
                            "read_model_mismatch",
                            "Derived checksum denial state does not match event replay.",
                            ledger_id,
                            event_cursor,
                            cursor["event_sequence"],
                        )
                    database_legacy_blocks = {
                        (row["tenant_id"], row["organization_id"]): row["first_denial_sequence"]
                        for row in connection.execute(
                            "SELECT tenant_id, organization_id, first_denial_sequence "
                            "FROM legacy_blocked_organizations"
                        )
                    }
                    if database_legacy_blocks != legacy_blocks:
                        return LedgerHealth(
                            False,
                            "read_model_mismatch",
                            "Derived legacy guard state does not match event replay.",
                            ledger_id,
                            event_cursor,
                            cursor["event_sequence"],
                        )
                receipt = connection.execute(
                    "SELECT event_sequence, event_hash, repository_id, bundle_sha256 "
                    "FROM anchor_receipts ORDER BY event_sequence DESC LIMIT 1"
                ).fetchone()
                if receipt is None:
                    return LedgerHealth(
                        False,
                        "anchor_missing",
                        "No verified off-server anchor receipt exists.",
                        ledger_id,
                        event_cursor,
                        cursor["event_sequence"],
                    )
                if receipt["repository_id"] != expected_repository_id:
                    return LedgerHealth(
                        False,
                        "repository_identity_mismatch",
                        "Verified receipt belongs to an unexpected repository.",
                        ledger_id,
                        event_cursor,
                        cursor["event_sequence"],
                        receipt["event_sequence"],
                        receipt["repository_id"],
                    )
                if (
                    receipt["event_sequence"] != event_cursor
                    or receipt["event_hash"] != event_hash
                ):
                    return LedgerHealth(
                        False,
                        "anchor_cursor_stale",
                        "Verified off-server cursor is behind the local ledger head.",
                        ledger_id,
                        event_cursor,
                        cursor["event_sequence"],
                        receipt["event_sequence"],
                        receipt["repository_id"],
                    )
                if receipt["bundle_sha256"] != _sha256(self.bundle_bytes()):
                    return LedgerHealth(
                        False,
                        "anchor_bundle_mismatch",
                        "Local ledger bytes no longer match the verified anchor receipt.",
                        ledger_id,
                        event_cursor,
                        cursor["event_sequence"],
                        receipt["event_sequence"],
                        receipt["repository_id"],
                    )
                return LedgerHealth(
                    True,
                    "ready",
                    "Ledger, replay, derived cursor, and off-server anchor agree.",
                    ledger_id,
                    event_cursor,
                    cursor["event_sequence"],
                    receipt["event_sequence"],
                    receipt["repository_id"],
                )
        except Exception as error:
            return LedgerHealth(False, "ledger_invalid", str(error))

    def release_state(self, release_id: uuid.UUID | str) -> Mapping[str, Any] | None:
        canonical_id = canonical_release_id(release_id)
        with self._connect(read_only=True) as connection:
            row = connection.execute(
                "SELECT state, reservation_payload_json, reservation_sequence, "
                "current_sequence FROM release_state WHERE release_id = ?",
                (canonical_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "state": row["state"],
                "reservation": json.loads(row["reservation_payload_json"]),
                "reservation_sequence": row["reservation_sequence"],
                "current_sequence": row["current_sequence"],
            }

    def event_by_id(self, event_id: str) -> AppendedEvent | None:
        _require_event_id(event_id)
        with self._connect(read_only=True) as connection:
            row = self._event_row_by_id(connection, event_id)
            if row is None:
                return None
            return AppendedEvent(
                sequence=row["sequence"],
                event_id=row["event_id"],
                event_type=row["event_type"],
                release_id=row["release_id"],
                payload=json.loads(row["payload_json"]),
                event_hash=row["event_hash"],
                idempotent_retry=True,
            )

    @staticmethod
    def _validate_bundle(bundle: Any) -> None:
        if not isinstance(bundle, dict):
            raise InvalidLedgerError("Anchor bundle has an unknown schema.")
        common_fields = {
            "bundle_schema_version", "event_cursor", "event_head_hash", "events",
            "ledger_id", "ledger_schema_version",
        }
        bundle_version = bundle.get("bundle_schema_version")
        expected_fields = common_fields | ({"v1_event_cursor"} if bundle_version == 2 else set())
        if set(bundle) != expected_fields:
            raise InvalidLedgerError("Anchor bundle has an unknown schema.")
        if (
            (bundle_version == 1 and bundle["ledger_schema_version"] != SCHEMA_VERSION)
            or (
                bundle_version == 2
                and bundle["ledger_schema_version"] != LATEST_LEDGER_SCHEMA_VERSION
            )
            or bundle_version not in {1, 2}
        ):
            raise InvalidLedgerError("Anchor bundle schema is unsupported.")
        if bundle_version == 2 and (
            isinstance(bundle["v1_event_cursor"], bool)
            or not isinstance(bundle["v1_event_cursor"], int)
            or bundle["v1_event_cursor"] < 0
            or bundle["v1_event_cursor"] >= bundle["event_cursor"]
        ):
            raise InvalidLedgerError("Anchor v1 event cursor is invalid.")
        canonical_release_id(bundle["ledger_id"])
        if not isinstance(bundle["events"], list):
            raise InvalidLedgerError("Anchor events must be a list.")
        if bundle["event_cursor"] != len(bundle["events"]):
            raise InvalidLedgerError("Anchor cursor does not match its event list.")
        previous_hash = GENESIS_HASH
        seen_event_ids: set[str] = set()
        states: dict[str, str] = {}
        reserved_keys: set[str] = set()
        for expected_sequence, event in enumerate(bundle["events"], start=1):
            required = {
                "sequence", "event_id", "event_type", "release_id", "payload_json",
                "payload_sha256", "previous_event_hash", "event_hash", "created_at_utc",
            }
            if not isinstance(event, dict) or set(event) != required:
                raise InvalidLedgerError("Anchor event has an unknown schema.")
            if event["sequence"] != expected_sequence:
                raise InvalidLedgerError("Anchor event sequence is not monotonic.")
            _require_event_id(event["event_id"])
            if event["event_id"] in seen_event_ids:
                raise InvalidLedgerError("Anchor contains a duplicate event ID.")
            seen_event_ids.add(event["event_id"])
            if event["event_type"] not in ALL_EVENT_TYPES:
                raise InvalidLedgerError("Anchor contains an unknown event type.")
            if event["event_type"] in V2_EVENT_TYPES and bundle_version != 2:
                raise InvalidLedgerError("Anchor v1 contains a v2 event type.")
            if (
                bundle_version == 2
                and expected_sequence <= bundle["v1_event_cursor"]
                and event["event_type"] in V2_EVENT_TYPES
            ):
                raise InvalidLedgerError("Anchor v2 event crosses the immutable v1 boundary.")
            release_id = canonical_release_id(event["release_id"])
            try:
                payload = json.loads(event["payload_json"])
            except json.JSONDecodeError as error:
                raise InvalidLedgerError("Anchor event payload is invalid JSON.") from error
            if _canonical_json(payload) != event["payload_json"]:
                raise InvalidLedgerError("Anchor event payload is not canonical.")
            payload_hash = _sha256(event["payload_json"])
            if payload_hash != event["payload_sha256"]:
                raise InvalidLedgerError("Anchor payload checksum mismatch.")
            if event["previous_event_hash"] != previous_hash:
                raise InvalidLedgerError("Anchor hash chain is broken.")
            expected_hash = _event_hash(
                sequence=expected_sequence,
                event_id=event["event_id"],
                event_type=event["event_type"],
                release_id=release_id,
                payload_sha256=payload_hash,
                previous_event_hash=previous_hash,
                created_at_utc=event["created_at_utc"],
            )
            if event["event_hash"] != expected_hash:
                raise InvalidLedgerError("Anchor event checksum mismatch.")
            PublicImageSafetyLedger._validate_payload(event["event_type"], release_id, payload)
            PublicImageSafetyLedger._apply_to_memory(
                states, reserved_keys, event["event_type"], release_id, payload
            )
            previous_hash = expected_hash
        if bundle["event_head_hash"] != previous_hash:
            raise InvalidLedgerError("Anchor head checksum mismatch.")

    @staticmethod
    def _validate_payload(event_type: str, release_id: str, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise InvalidLedgerError("Event payload schema is unsupported.")
        if event_type == "tenant_checksum_denied":
            if payload.get("schema_version") != LATEST_LEDGER_SCHEMA_VERSION:
                raise InvalidLedgerError("Checksum denial payload schema is unsupported.")
            if set(payload) != {
                "schema_version", "source_checksum_sha256", "tenant_id",
            }:
                raise InvalidLedgerError("Checksum denial payload has an unknown schema.")
            _require_positive_int("Tenant ID", payload["tenant_id"])
            _require_sha256("Source checksum", payload["source_checksum_sha256"])
            return
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise InvalidLedgerError("Event payload schema is unsupported.")
        if payload.get("release_id") != release_id:
            raise InvalidLedgerError("Event payload release ID does not match its envelope.")
        if event_type == "release_reserved":
            required = {
                "organization_id", "release_id", "rendition_set_id", "schema_version",
                "selection_id", "selection_revision", "tenant_id", "variants",
            }
            if set(payload) != required:
                raise InvalidLedgerError("Reservation payload has an unknown schema.")
            for key in (
                "organization_id", "rendition_set_id", "selection_id",
                "selection_revision", "tenant_id",
            ):
                _require_positive_int(key, payload[key])
            variants = payload["variants"]
            if not isinstance(variants, dict) or set(variants) != REQUIRED_RELEASE_VARIANTS:
                raise InvalidLedgerError("Reservation variants are incomplete.")
            for variant, rendition in variants.items():
                if not isinstance(rendition, dict) or set(rendition) != {
                    "artifact_checksum_sha256", "artifact_storage_key",
                    "output_format", "public_storage_key",
                }:
                    raise InvalidLedgerError("Reservation rendition schema is invalid.")
                _require_sha256("Artifact checksum", rendition["artifact_checksum_sha256"])
                _require_artifact_key(rendition["artifact_storage_key"])
                expected_key = build_public_release_key(
                    release_id, variant, rendition["output_format"]
                )
                if rendition["public_storage_key"] != expected_key:
                    raise InvalidLedgerError("Caller-controlled public key was rejected.")
        elif event_type == "release_activated":
            if set(payload) != {"release_id", "schema_version"}:
                raise InvalidLedgerError("Activation payload has an unknown schema.")
        else:
            if set(payload) != {"reason_code", "release_id", "schema_version"}:
                raise InvalidLedgerError("Terminal event payload has an unknown schema.")
            if not isinstance(payload["reason_code"], str) or not REASON_RE.fullmatch(payload["reason_code"]):
                raise InvalidLedgerError("Terminal reason code is not canonical.")

    @staticmethod
    def _apply_to_memory(
        states: dict[str, str],
        reserved_keys: set[str],
        event_type: str,
        release_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        if event_type == "tenant_checksum_denied":
            return
        current = states.get(release_id)
        if event_type == "release_reserved":
            if current is not None:
                raise InvalidTransitionError("Release ID was already reserved.")
            keys = {
                rendition["public_storage_key"]
                for rendition in payload["variants"].values()
            }
            if keys & reserved_keys:
                raise InvalidTransitionError("A canonical release key was already reserved.")
            reserved_keys.update(keys)
            states[release_id] = "reserved"
        elif event_type == "release_activated":
            if current != "reserved":
                raise InvalidTransitionError("Only a reserved release can be activated.")
            states[release_id] = "active"
        elif event_type in {"release_retired", "release_denied"}:
            if current not in {"reserved", "active"}:
                raise InvalidTransitionError(
                    "Only a reserved or active release can become terminal."
                )
            states[release_id] = event_type.removeprefix("release_")

    def _apply_to_database(
        self,
        connection: sqlite3.Connection,
        *,
        sequence: int,
        event_type: str,
        release_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        if event_type == "tenant_checksum_denied":
            connection.execute(
                "INSERT INTO tenant_checksum_denials("
                "tenant_id, source_checksum_sha256, event_sequence"
                ") VALUES (?, ?, ?)",
                (payload["tenant_id"], payload["source_checksum_sha256"], sequence),
            )
            return
        row = connection.execute(
            "SELECT state FROM release_state WHERE release_id = ?", (release_id,)
        ).fetchone()
        current = None if row is None else row["state"]
        if event_type == "release_reserved":
            if current is not None:
                raise InvalidTransitionError("Release ID was already reserved.")
            keys = [
                rendition["public_storage_key"]
                for rendition in payload["variants"].values()
            ]
            placeholders = ",".join("?" for _ in keys)
            collision = connection.execute(
                "SELECT release_id FROM reserved_release_keys "
                f"WHERE public_storage_key IN ({placeholders}) LIMIT 1",
                keys,
            ).fetchone()
            if collision is not None:
                raise InvalidTransitionError("A canonical release key was already reserved.")
            connection.execute(
                "INSERT INTO release_state("
                "release_id, state, reservation_payload_json, "
                "reservation_sequence, current_sequence"
                ") VALUES (?, 'reserved', ?, ?, ?)",
                (release_id, _canonical_json(payload), sequence, sequence),
            )
            connection.executemany(
                "INSERT INTO reserved_release_keys(public_storage_key, release_id) "
                "VALUES (?, ?)",
                ((key, release_id) for key in keys),
            )
        elif event_type == "release_activated":
            if current != "reserved":
                raise InvalidTransitionError("Only a reserved release can be activated.")
            connection.execute(
                "UPDATE release_state SET state = 'active', current_sequence = ? "
                "WHERE release_id = ?",
                (sequence, release_id),
            )
        else:
            if current not in {"reserved", "active"}:
                raise InvalidTransitionError(
                    "Only a reserved or active release can become terminal."
                )
            state = event_type.removeprefix("release_")
            connection.execute(
                "UPDATE release_state SET state = ?, current_sequence = ? "
                "WHERE release_id = ?",
                (state, sequence, release_id),
            )
            if (
                event_type == "release_denied"
                and self._database_schema_version(connection)
                >= LATEST_LEDGER_SCHEMA_VERSION
            ):
                reservation = json.loads(
                    connection.execute(
                        "SELECT reservation_payload_json FROM release_state "
                        "WHERE release_id = ?",
                        (release_id,),
                    ).fetchone()["reservation_payload_json"]
                )
                connection.execute(
                    "INSERT OR IGNORE INTO legacy_blocked_organizations("
                    "tenant_id, organization_id, first_denial_sequence"
                    ") VALUES (?, ?, ?)",
                    (
                        reservation["tenant_id"],
                        reservation["organization_id"],
                        sequence,
                    ),
                )

    def _replay(
        self, connection: sqlite3.Connection
    ) -> tuple[
        dict[str, dict[str, Any]],
        dict[tuple[int, str], int],
        dict[tuple[int, int], int],
        int,
        str,
    ]:
        states: dict[str, dict[str, Any]] = {}
        checksum_denials: dict[tuple[int, str], int] = {}
        legacy_blocks: dict[tuple[int, int], int] = {}
        simple_states: dict[str, str] = {}
        reserved_keys: set[str] = set()
        seen_event_ids: set[str] = set()
        seen_event_hashes: set[str] = set()
        previous_hash = GENESIS_HASH
        expected_sequence = 1
        if self._database_schema_version(connection) >= LATEST_LEDGER_SCHEMA_VERSION:
            v1_cursor = int(self._metadata(connection, "v1_event_cursor"))
            v1_head = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM ledger_events"
            ).fetchone()[0]
            invalid_v2_boundary = connection.execute(
                "SELECT 1 FROM ledger_events_v2 WHERE sequence <= ? LIMIT 1",
                (v1_cursor,),
            ).fetchone()
            if v1_head != v1_cursor or invalid_v2_boundary is not None:
                raise InvalidLedgerError("Ledger v1/v2 event boundary is invalid.")
        for row in self._event_rows(connection):
            if row["sequence"] != expected_sequence:
                raise InvalidLedgerError("Ledger event sequence is not monotonic.")
            _require_event_id(row["event_id"])
            if row["event_id"] in seen_event_ids or row["event_hash"] in seen_event_hashes:
                raise InvalidLedgerError("Ledger contains a duplicate event identity.")
            seen_event_ids.add(row["event_id"])
            seen_event_hashes.add(row["event_hash"])
            if row["event_type"] not in ALL_EVENT_TYPES:
                raise InvalidLedgerError("Ledger contains an unknown event type.")
            if canonical_release_id(row["release_id"]) != row["release_id"]:
                raise InvalidLedgerError("Ledger release ID is not canonical.")
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError as error:
                raise InvalidLedgerError("Ledger contains invalid event JSON.") from error
            if _canonical_json(payload) != row["payload_json"]:
                raise InvalidLedgerError("Ledger contains non-canonical event JSON.")
            payload_hash = _sha256(row["payload_json"])
            if payload_hash != row["payload_sha256"] or row["previous_event_hash"] != previous_hash:
                raise InvalidLedgerError("Ledger hash chain is invalid.")
            expected_hash = _event_hash(
                sequence=row["sequence"],
                event_id=row["event_id"],
                event_type=row["event_type"],
                release_id=row["release_id"],
                payload_sha256=payload_hash,
                previous_event_hash=previous_hash,
                created_at_utc=row["created_at_utc"],
            )
            if row["event_hash"] != expected_hash:
                raise InvalidLedgerError("Ledger event hash is invalid.")
            self._validate_payload(row["event_type"], row["release_id"], payload)
            self._apply_to_memory(
                simple_states, reserved_keys, row["event_type"], row["release_id"], payload
            )
            if row["event_type"] == "tenant_checksum_denied":
                key = (payload["tenant_id"], payload["source_checksum_sha256"])
                if key in checksum_denials:
                    raise InvalidTransitionError("Tenant checksum was already denied.")
                checksum_denials[key] = row["sequence"]
            elif row["event_type"] == "release_reserved":
                states[row["release_id"]] = {
                    "state": "reserved",
                    "reservation_payload_json": row["payload_json"],
                    "reservation_sequence": row["sequence"],
                    "current_sequence": row["sequence"],
                }
            else:
                states[row["release_id"]]["state"] = simple_states[row["release_id"]]
                states[row["release_id"]]["current_sequence"] = row["sequence"]
                if row["event_type"] == "release_denied":
                    reservation = json.loads(
                        states[row["release_id"]]["reservation_payload_json"]
                    )
                    legacy_blocks.setdefault(
                        (reservation["tenant_id"], reservation["organization_id"]),
                        row["sequence"],
                    )
            previous_hash = expected_hash
            expected_sequence += 1
        return (
            states,
            checksum_denials,
            legacy_blocks,
            expected_sequence - 1,
            previous_hash,
        )

    def _connect(self, *, read_only: bool = False) -> sqlite3.Connection:
        if read_only:
            uri = f"file:{self.path.resolve()}?mode=ro"
            connection = sqlite3.connect(uri, uri=True, timeout=10, isolation_level=None)
        else:
            connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        self._configure(connection, read_only=read_only)
        self._validate_database_identity(connection)
        return connection

    @staticmethod
    def _configure(connection: sqlite3.Connection, *, read_only: bool = False) -> None:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        if not read_only:
            # A tiny host-owned single-writer ledger does not need WAL. DELETE
            # mode keeps a cleanly committed SQLite file self-contained for
            # read-only health checks and isolated disaster recovery copies.
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = FULL")

    @staticmethod
    def _validate_database_identity(connection: sqlite3.Connection) -> None:
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id != APPLICATION_ID or user_version not in {
            SCHEMA_VERSION,
            LATEST_LEDGER_SCHEMA_VERSION,
        }:
            raise InvalidLedgerError("Ledger schema or application identity is unknown.")
        row = connection.execute(
            "SELECT value FROM ledger_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != str(user_version):
            raise InvalidLedgerError("Ledger schema metadata is inconsistent.")

    @staticmethod
    def _database_schema_version(connection: sqlite3.Connection) -> int:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in {SCHEMA_VERSION, LATEST_LEDGER_SCHEMA_VERSION}:
            raise InvalidLedgerError("Ledger schema version is unsupported.")
        return version

    @staticmethod
    def _metadata(connection: sqlite3.Connection, key: str) -> str:
        row = connection.execute(
            "SELECT value FROM ledger_metadata WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            raise InvalidLedgerError(f"Ledger metadata is missing: {key}.")
        return row["value"]


_SCHEMA = """
CREATE TABLE ledger_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;

CREATE TABLE ledger_events (
    sequence INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL CHECK(event_type IN (
        'release_reserved', 'release_activated', 'release_retired', 'release_denied'
    )),
    release_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    previous_event_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL UNIQUE,
    created_at_utc TEXT NOT NULL
) STRICT;

CREATE TABLE release_state (
    release_id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK(state IN ('reserved', 'active', 'retired', 'denied')),
    reservation_payload_json TEXT NOT NULL,
    reservation_sequence INTEGER NOT NULL,
    current_sequence INTEGER NOT NULL
) STRICT;

CREATE TABLE reserved_release_keys (
    public_storage_key TEXT PRIMARY KEY,
    release_id TEXT NOT NULL REFERENCES release_state(release_id)
) STRICT;

CREATE TABLE read_cursor (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    event_sequence INTEGER NOT NULL,
    event_hash TEXT NOT NULL
) STRICT;

CREATE TABLE anchor_receipts (
    event_sequence INTEGER PRIMARY KEY,
    event_hash TEXT NOT NULL,
    archive_name TEXT NOT NULL UNIQUE,
    repository_id TEXT NOT NULL,
    bundle_sha256 TEXT NOT NULL,
    verified_at_utc TEXT NOT NULL
) STRICT;

CREATE TRIGGER ledger_events_no_update
BEFORE UPDATE ON ledger_events BEGIN
    SELECT RAISE(ABORT, 'ledger events are append-only');
END;
CREATE TRIGGER ledger_events_no_delete
BEFORE DELETE ON ledger_events BEGIN
    SELECT RAISE(ABORT, 'ledger events are append-only');
END;
CREATE TRIGGER anchor_receipts_no_update
BEFORE UPDATE ON anchor_receipts BEGIN
    SELECT RAISE(ABORT, 'anchor receipts are append-only');
END;
CREATE TRIGGER anchor_receipts_no_delete
BEFORE DELETE ON anchor_receipts BEGIN
    SELECT RAISE(ABORT, 'anchor receipts are append-only');
END;
"""

_SCHEMA_V2_STATEMENTS = (
    """CREATE TABLE ledger_events_v2 (
        sequence INTEGER PRIMARY KEY,
        event_id TEXT NOT NULL UNIQUE,
        event_type TEXT NOT NULL CHECK(event_type IN (
            'release_reserved', 'release_activated', 'release_retired',
            'release_denied', 'tenant_checksum_denied'
        )),
        release_id TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL,
        previous_event_hash TEXT NOT NULL,
        event_hash TEXT NOT NULL UNIQUE,
        created_at_utc TEXT NOT NULL
    ) STRICT""",
    """CREATE TABLE tenant_checksum_denials (
        tenant_id INTEGER NOT NULL,
        source_checksum_sha256 TEXT NOT NULL,
        event_sequence INTEGER NOT NULL,
        PRIMARY KEY (tenant_id, source_checksum_sha256)
    ) STRICT""",
    """CREATE TABLE legacy_blocked_organizations (
        tenant_id INTEGER NOT NULL,
        organization_id INTEGER NOT NULL,
        first_denial_sequence INTEGER NOT NULL,
        PRIMARY KEY (tenant_id, organization_id)
    ) STRICT""",
    """CREATE TRIGGER ledger_events_v2_no_update
    BEFORE UPDATE ON ledger_events_v2 BEGIN
        SELECT RAISE(ABORT, 'ledger events are append-only');
    END""",
    """CREATE TRIGGER ledger_events_v2_no_delete
    BEFORE DELETE ON ledger_events_v2 BEGIN
        SELECT RAISE(ABORT, 'ledger events are append-only');
    END""",
)

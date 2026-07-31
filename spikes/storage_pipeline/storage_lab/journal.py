from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path

from .contracts import canonical_json, validate_key


class JournalError(RuntimeError):
    pass


class JournalUnavailable(JournalError):
    pass


class JournalCorrupt(JournalError):
    pass


class DuplicateEventConflict(JournalError):
    pass


@dataclass(frozen=True)
class JournalEvent:
    event_id: str
    tenant: str
    public_key: str
    artifact_checksum: str
    source_checksum: str
    timestamp: str
    action: str
    reason_code: str
    principal: str
    previous_release_key: str | None = None
    new_release_key: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_key(self.public_key, expected_tenant=self.tenant)
        if self.previous_release_key:
            validate_key(self.previous_release_key, expected_tenant=self.tenant)
        if self.new_release_key:
            validate_key(self.new_release_key, expected_tenant=self.tenant)
        if self.action not in {"deny", "authorized_release"}:
            raise JournalError("unsupported journal action")
        if self.schema_version != 1:
            raise JournalError("unsupported journal schema")

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class DenyJournal:
    """Append-only-oriented JSONL prototype outside application snapshots."""

    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, event: JournalEvent) -> bool:
        existing = {item.event_id: item for item in self.replay(require_exists=False)}
        if event.event_id in existing:
            if canonical_json(existing[event.event_id].as_dict()) == canonical_json(event.as_dict()):
                return False
            raise DuplicateEventConflict(f"event {event.event_id} has different payload")
        self.initialize()
        payload = canonical_json(event.as_dict()).encode("ascii") + b"\n"
        descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return True

    def replay(self, *, require_exists: bool = True) -> list[JournalEvent]:
        if not self.path.exists():
            if require_exists:
                raise JournalUnavailable("deny journal is missing")
            return []
        events: list[JournalEvent] = []
        seen: dict[str, JournalEvent] = {}
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                event = JournalEvent(**payload)
            except Exception as exc:
                raise JournalCorrupt(f"invalid journal line {line_number}") from exc
            previous = seen.get(event.event_id)
            if previous and canonical_json(previous.as_dict()) != canonical_json(event.as_dict()):
                raise DuplicateEventConflict(f"event {event.event_id} conflicts during replay")
            if previous is None:
                events.append(event)
                seen[event.event_id] = event
        return events

    def deny_set(self) -> set[str]:
        denied: set[str] = set()
        for event in self.replay():
            if event.action == "deny":
                denied.add(event.public_key)
        return denied

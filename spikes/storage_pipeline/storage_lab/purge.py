from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256


@dataclass(frozen=True)
class PurgeResult:
    request_id: str
    target: str
    status: str
    purged: bool
    idempotent_replay: bool
    retryable: bool
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class CacheSimulator:
    def __init__(self):
        self.entries: dict[str, bytes] = {}

    def seed(self, target: str, data: bytes) -> None:
        self.entries[target] = data

    def contains(self, target: str) -> bool:
        return target in self.entries

    def get(self, target: str) -> bytes | None:
        return self.entries.get(target)

    def evict(self, target: str) -> bool:
        return self.entries.pop(target, None) is not None


class RecordingPurgeProvider:
    def __init__(self, cache: CacheSimulator):
        self.cache = cache
        self.results: dict[str, PurgeResult] = {}
        self.calls: list[str] = []
        self.failures: dict[str, tuple[str, bool]] = {}

    def fail_next(self, target: str, *, error: str, retryable: bool) -> None:
        self.failures[target] = (error, retryable)

    def purge(self, target: str) -> PurgeResult:
        self.calls.append(target)
        request_id = f"purge-{sha256(target.encode('utf-8')).hexdigest()[:16]}"
        previous = self.results.get(target)
        if previous and previous.status == "success":
            return PurgeResult(
                request_id=previous.request_id,
                target=target,
                status="success",
                purged=False,
                idempotent_replay=True,
                retryable=False,
            )
        failure = self.failures.pop(target, None)
        if failure:
            result = PurgeResult(
                request_id=request_id,
                target=target,
                status="failed",
                purged=False,
                idempotent_replay=False,
                retryable=failure[1],
                error=failure[0],
            )
        else:
            result = PurgeResult(
                request_id=request_id,
                target=target,
                status="success",
                purged=self.cache.evict(target),
                idempotent_replay=False,
                retryable=False,
            )
        self.results[target] = result
        return result

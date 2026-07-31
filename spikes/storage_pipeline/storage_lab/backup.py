from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import time

from .contracts import PROCESSING_VERSION, checksum_bytes


class BackupError(RuntimeError):
    pass


class StorageUnavailable(BackupError):
    pass


@dataclass(frozen=True)
class BackupMeasurement:
    strategy: str
    object_count: int
    byte_size: int
    restore_ms: float
    processing_version_required: bool
    byte_identical: bool

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["restore_ms"] = round(self.restore_ms, 3)
        return value


@dataclass(frozen=True)
class BackupBundle:
    strategy: str
    objects: dict[str, bytes]
    metadata: dict[str, str]
    checksums: dict[str, str]


class DeterministicRenderer:
    """Recording domain fake; phase 3B.1 owns real image-byte proof."""

    known_versions = {PROCESSING_VERSION}

    def render(self, original: bytes, metadata: dict[str, str]) -> bytes:
        version = metadata.get("processing_version", "")
        if version not in self.known_versions:
            raise BackupError("unknown processing version")
        config = metadata.get("canonical_render_config", "")
        return b"phase3b2-recorded-render:" + sha256(
            original + b"\0" + version.encode("ascii") + b"\0" + config.encode("ascii")
        ).digest()


def make_direct_backup(original: bytes, rendition: bytes) -> BackupBundle:
    objects = {"private-original": original, "active-public-rendition": rendition}
    return BackupBundle(
        strategy="A-direct-active-rendition",
        objects=objects,
        metadata={},
        checksums={name: checksum_bytes(data) for name, data in objects.items()},
    )


def make_regeneration_backup(original: bytes, *, canonical_render_config: str) -> BackupBundle:
    objects = {"private-original": original}
    return BackupBundle(
        strategy="B-original-plus-metadata",
        objects=objects,
        metadata={
            "processing_version": PROCESSING_VERSION,
            "canonical_render_config": canonical_render_config,
        },
        checksums={"private-original": checksum_bytes(original)},
    )


def restore_direct(bundle: BackupBundle, *, storage_available: bool = True) -> tuple[bytes, BackupMeasurement]:
    started = time.perf_counter()
    if not storage_available:
        raise StorageUnavailable("storage unavailable during restore")
    _verify(bundle)
    try:
        rendition = bundle.objects["active-public-rendition"]
    except KeyError as exc:
        raise BackupError("active rendition missing") from exc
    duration = (time.perf_counter() - started) * 1000
    return rendition, BackupMeasurement(
        strategy=bundle.strategy,
        object_count=len(bundle.objects),
        byte_size=sum(len(data) for data in bundle.objects.values()),
        restore_ms=duration,
        processing_version_required=False,
        byte_identical=True,
    )


def restore_regenerated(
    bundle: BackupBundle,
    renderer: DeterministicRenderer,
    *,
    expected_rendition: bytes,
    storage_available: bool = True,
) -> tuple[bytes, BackupMeasurement]:
    started = time.perf_counter()
    if not storage_available:
        raise StorageUnavailable("storage unavailable during restore")
    _verify(bundle)
    try:
        original = bundle.objects["private-original"]
    except KeyError as exc:
        raise BackupError("private original missing") from exc
    rendered = renderer.render(original, bundle.metadata)
    duration = (time.perf_counter() - started) * 1000
    return rendered, BackupMeasurement(
        strategy=bundle.strategy,
        object_count=len(bundle.objects),
        byte_size=sum(len(data) for data in bundle.objects.values()) + sum(
            len(key) + len(value) for key, value in bundle.metadata.items()
        ),
        restore_ms=duration,
        processing_version_required=True,
        byte_identical=rendered == expected_rendition,
    )


def _verify(bundle: BackupBundle) -> None:
    for name, expected in bundle.checksums.items():
        data = bundle.objects.get(name)
        if data is None:
            raise BackupError(f"backup object missing: {name}")
        if checksum_bytes(data) != expected:
            raise BackupError(f"backup checksum mismatch: {name}")

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import struct
from typing import Iterable


PROCESSING_VERSION = "phase3b1-pillow-v1"
MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 20_000_000

# Square and landscape are prototype values, not final product decisions.
VARIANTS: dict[str, tuple[int, int]] = {
    "square": (512, 512),
    "landscape": (800, 450),
    "share": (1200, 630),
}

MIME_BY_FORMAT = {
    "AVIF": "image/avif",
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class ImageLabError(Exception):
    """Base class for expected prototype failures."""


class SourceRejected(ImageLabError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class UpscaleRequired(ImageLabError):
    pass


@dataclass(frozen=True)
class FixtureSpec:
    name: str
    filename: str
    declared_mime: str
    kind: str
    expected: str = "accept"
    semantic_flags: tuple[str, ...] = ()
    note: str = ""

    def path(self, root: Path) -> Path:
        return root / self.filename


@dataclass(frozen=True)
class SourceInfo:
    path: str
    byte_size: int
    byte_checksum: str
    detected_format: str
    detected_mime: str
    width: int
    height: int
    normalized_width: int
    normalized_height: int
    has_alpha: bool
    exif_orientation: int | None
    metadata_keys: tuple[str, ...]
    edge_variance: float

    @property
    def pixels(self) -> int:
        return self.width * self.height

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RenditionInfo:
    variant: str
    fit: str
    focus_x: float
    focus_y: float
    width: int
    height: int
    output_format: str
    byte_size: int
    checksum: str
    processing_version: str
    immutable_key: str
    crop_box: tuple[int, int, int, int] | None
    upscaled: bool
    metadata_keys: tuple[str, ...]
    has_alpha: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def checksum_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical_config_hash(config: dict[str, object]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return checksum_bytes(payload.encode("ascii"))[:20]


def immutable_rendition_key(
    source_checksum: str,
    *,
    variant: str,
    fit: str,
    focus: tuple[float, float],
    output_format: str,
    processing_version: str = PROCESSING_VERSION,
) -> str:
    config = {
        "fit": fit,
        "focus": [round(focus[0], 6), round(focus[1], 6)],
        "format": output_format.lower(),
        "processing_version": processing_version,
        "source_checksum": source_checksum,
        "variant": variant,
    }
    suffix = "jpg" if output_format.upper() == "JPEG" else output_format.lower()
    return (
        f"renditions/{processing_version}/{source_checksum[:16]}/"
        f"{variant}-{canonical_config_hash(config)}.{suffix}"
    )


def detect_mime(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG", "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP", "image/webp"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG", "image/jpeg"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in {
        b"avif",
        b"avis",
        b"mif1",
    }:
        return "AVIF", "image/avif"

    prefix = data[:1024].lstrip().lower()
    if prefix.startswith(b"<?xml") or prefix.startswith(b"<svg"):
        if b"<svg" in prefix:
            return "SVG", "image/svg+xml"

    return "UNKNOWN", "application/octet-stream"


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    import zlib

    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def safe_declared_pixel_bomb(width: int = 100_000, height: int = 100_000) -> bytes:
    """Return a tiny PNG that declares unsafe dimensions but has no pixel payload.

    The file is intentionally incomplete as an image. Pillow reads the IHDR and
    trips its decompression-bomb protection before any huge allocation occurs.
    """

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr) + png_chunk(b"IEND", b"")


def normalize_focus(focus: Iterable[float]) -> tuple[float, float]:
    values = tuple(float(value) for value in focus)
    if len(values) != 2:
        raise ValueError("focus must contain exactly two values")
    x, y = values
    if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
        raise ValueError("focus values must be normalized between 0 and 1")
    return x, y


def cover_crop_box(
    source_size: tuple[int, int],
    target_size: tuple[int, int],
    focus: tuple[float, float],
) -> tuple[int, int, int, int]:
    source_width, source_height = source_size
    target_width, target_height = target_size
    focus_x, focus_y = normalize_focus(focus)

    source_ratio = source_width / source_height
    target_ratio = target_width / target_height

    if source_ratio > target_ratio:
        crop_height = source_height
        crop_width = max(1, round(crop_height * target_ratio))
        desired_left = round(focus_x * source_width - crop_width / 2)
        left = min(max(0, desired_left), source_width - crop_width)
        top = 0
    else:
        crop_width = source_width
        crop_height = max(1, round(crop_width / target_ratio))
        desired_top = round(focus_y * source_height - crop_height / 2)
        top = min(max(0, desired_top), source_height - crop_height)
        left = 0

    return left, top, left + crop_width, top + crop_height

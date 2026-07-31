from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from urllib.parse import quote, urlsplit, urlunsplit

from image_lab.core import PROCESSING_VERSION, immutable_rendition_key


SAFE_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
TOKEN_FRAGMENT = re.compile(r"(?i)(access[_-]?key|secret|signature|token|credential)")


class ContractError(ValueError):
    pass


class ImmutableConflict(ContractError):
    pass


@dataclass(frozen=True)
class ProcessingProfile:
    processing_version: str
    format: str
    encoder_settings: dict[str, object]


PROFILE_V1 = {
    "JPEG": ProcessingProfile(
        PROCESSING_VERSION,
        "JPEG",
        {"quality": 85, "subsampling": 0, "optimize": False, "progressive": False},
    ),
    "PNG": ProcessingProfile(
        PROCESSING_VERSION,
        "PNG",
        {"compress_level": 9, "optimize": False},
    ),
    "WEBP": ProcessingProfile(
        PROCESSING_VERSION,
        "WEBP",
        {"quality": 82, "method": 6, "exact_alpha": True},
    ),
}


def checksum_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def validate_key(key: str, *, expected_tenant: str | None = None) -> str:
    if not key or key.startswith(("/", "\\")):
        raise ContractError("key must be relative")
    if any(ord(character) < 32 or ord(character) == 127 for character in key):
        raise ContractError("key contains control characters")
    if "\\" in key or any(part in {"", ".", ".."} for part in key.split("/")):
        raise ContractError("key contains an unsafe path segment")
    if "?" in key or "#" in key or TOKEN_FRAGMENT.search(key):
        raise ContractError("key contains a query, fragment or credential-like token")
    if expected_tenant:
        parts = key.split("/")
        if len(parts) < 2 or parts[0] != "public" or parts[1] != expected_tenant:
            raise ContractError("key is outside the expected tenant scope")
    return key


def private_original_key(tenant: str, source_checksum: str, extension: str) -> str:
    _validate_segment(tenant, "tenant")
    if not re.fullmatch(r"[0-9a-f]{64}", source_checksum):
        raise ContractError("source checksum must be SHA-256")
    normalized_extension = extension.lower().lstrip(".")
    if normalized_extension not in {"jpg", "jpeg", "png", "webp"}:
        raise ContractError("unsupported original extension")
    return validate_key(
        f"originals/{tenant}/{source_checksum[:16]}/{source_checksum}.{normalized_extension}"
    )


def processing_artifact_key(
    source_checksum: str,
    *,
    variant: str,
    fit: str,
    focus: tuple[float, float],
    output_format: str,
    processing_version: str = PROCESSING_VERSION,
    encoder_settings: dict[str, object] | None = None,
) -> str:
    """Reuse the phase 3B.1 key and bind encoder settings to its version.

    Phase 3B.1 intentionally encodes the processing profile through
    ``processing_version``. A caller cannot provide settings that differ from
    that pinned profile while retaining the same key.
    """

    normalized_format = output_format.upper()
    profile = PROFILE_V1.get(normalized_format)
    if profile is None or processing_version != profile.processing_version:
        raise ContractError("unknown processing profile")
    supplied = encoder_settings if encoder_settings is not None else profile.encoder_settings
    if canonical_json(supplied) != canonical_json(profile.encoder_settings):
        raise ContractError("encoder settings require a new processing version")
    return validate_key(
        immutable_rendition_key(
            source_checksum,
            variant=variant,
            fit=fit,
            focus=focus,
            output_format=normalized_format,
            processing_version=processing_version,
        )
    )


def public_release_key(
    *,
    tenant: str,
    actor: str,
    release_revision: int,
    variant: str,
    artifact_checksum: str,
    extension: str,
) -> str:
    _validate_segment(tenant, "tenant")
    _validate_segment(actor, "actor")
    _validate_segment(variant, "variant")
    if release_revision < 1:
        raise ContractError("release revision must be positive")
    if not re.fullmatch(r"[0-9a-f]{64}", artifact_checksum):
        raise ContractError("artifact checksum must be SHA-256")
    suffix = extension.lower().lstrip(".")
    if suffix not in {"jpg", "png", "webp"}:
        raise ContractError("unsupported public extension")
    return validate_key(
        f"public/{tenant}/{actor}/r{release_revision}/{variant}-{artifact_checksum[:20]}.{suffix}",
        expected_tenant=tenant,
    )


@dataclass(frozen=True)
class AbsoluteOrigin:
    value: str
    allow_http_localhost: bool = False

    def __post_init__(self) -> None:
        parsed = urlsplit(self.value)
        if not parsed.scheme or not parsed.netloc:
            raise ContractError("origin must be absolute")
        if parsed.username or parsed.password:
            raise ContractError("origin must not contain credentials")
        if parsed.query or parsed.fragment:
            raise ContractError("origin must not contain query or fragment")
        hostname = (parsed.hostname or "").lower()
        lab_http = self.allow_http_localhost and hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and lab_http):
            raise ContractError("external origin must use HTTPS")
        normalized_path = parsed.path.rstrip("/")
        object.__setattr__(
            self,
            "value",
            urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", "")),
        )

    def join(self, key: str) -> str:
        safe_key = validate_key(key)
        encoded = "/".join(quote(part, safe="-_.~") for part in safe_key.split("/"))
        return f"{self.value}/{encoded}"


@dataclass(frozen=True)
class PublicOriginConfiguration:
    public_site_origin: AbsoluteOrigin
    public_media_origin: AbsoluteOrigin

    @classmethod
    def from_values(
        cls,
        *,
        public_site_origin: str,
        public_media_origin: str,
        allow_http_localhost: bool = False,
    ) -> "PublicOriginConfiguration":
        return cls(
            public_site_origin=AbsoluteOrigin(public_site_origin, allow_http_localhost),
            public_media_origin=AbsoluteOrigin(public_media_origin, allow_http_localhost),
        )

    def media_url(self, key: str) -> str:
        if not key.startswith("public/"):
            raise ContractError("public media origin only accepts public release keys")
        return self.public_media_origin.join(key)


@dataclass(frozen=True)
class AppState:
    tenant: str
    actor: str
    public_key: str | None
    artifact_key: str | None
    release_revision: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "AppState":
        return cls(
            tenant=str(value["tenant"]),
            actor=str(value["actor"]),
            public_key=str(value["public_key"]) if value.get("public_key") else None,
            artifact_key=str(value["artifact_key"]) if value.get("artifact_key") else None,
            release_revision=int(value["release_revision"]),
        )


def _validate_segment(value: str, label: str) -> None:
    if not SAFE_SEGMENT.fullmatch(value):
        raise ContractError(f"unsafe {label} segment")

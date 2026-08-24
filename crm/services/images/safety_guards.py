from __future__ import annotations

from .bridge_client import ImageSafetyBridgeClient, ImageSafetyBridgeError


class ImageSafetyGuardError(RuntimeError):
    pass


class ImageSourceChecksumDenied(ImageSafetyGuardError):
    pass


class ImageSafetyGuardUnavailable(ImageSafetyGuardError):
    pass


def require_source_checksum_allowed(
    *,
    tenant_id: int,
    source_checksum_sha256: str,
    bridge: ImageSafetyBridgeClient | None = None,
) -> int:
    bridge = bridge or ImageSafetyBridgeClient(timeout=5.0)
    try:
        result = bridge.check_checksum(
            tenant_id=tenant_id,
            source_checksum_sha256=source_checksum_sha256,
        )
    except ImageSafetyBridgeError as error:
        raise ImageSafetyGuardUnavailable(
            "Image safety checksum state is unavailable."
        ) from error
    if result.denied:
        raise ImageSourceChecksumDenied(
            "The source image bytes are permanently denied in this tenant."
        )
    return result.read_cursor


def legacy_image_is_blocked(
    *,
    tenant_id: int,
    organization_id: int,
    bridge: ImageSafetyBridgeClient | None = None,
) -> bool:
    """Fail closed: unavailable safety state must never reveal a legacy image."""
    bridge = bridge or ImageSafetyBridgeClient(timeout=5.0)
    try:
        return bridge.legacy_guard(
            tenant_id=tenant_id,
            organization_id=organization_id,
        ).blocked
    except ImageSafetyBridgeError:
        return True

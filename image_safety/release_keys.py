from __future__ import annotations

import uuid


REQUIRED_RELEASE_VARIANTS = frozenset({"square", "landscape", "share"})
PUBLIC_RELEASE_EXTENSIONS = {
    "jpeg": "jpg",
    "png": "png",
    "webp": "webp",
}


class InvalidPublicReleaseKeyError(ValueError):
    pass


def canonical_release_id(release_id: uuid.UUID | str) -> str:
    try:
        value = uuid.UUID(str(release_id))
    except (AttributeError, TypeError, ValueError) as error:
        raise InvalidPublicReleaseKeyError(
            "Release ID must be a valid UUIDv4."
        ) from error
    if value.version != 4:
        raise InvalidPublicReleaseKeyError("Release ID must be UUIDv4.")
    return str(value)


def build_public_release_key(
    release_id: uuid.UUID | str,
    variant: str,
    output_format: str,
) -> str:
    canonical_id = canonical_release_id(release_id)
    if variant not in REQUIRED_RELEASE_VARIANTS:
        raise InvalidPublicReleaseKeyError("Unsupported public image variant.")
    try:
        extension = PUBLIC_RELEASE_EXTENSIONS[output_format]
    except KeyError as error:
        raise InvalidPublicReleaseKeyError(
            "Unsupported public image output format."
        ) from error
    return f"releases/{canonical_id}/{variant}.{extension}"

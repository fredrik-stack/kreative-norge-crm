from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from crm.validators import validate_storage_key
from image_safety.release_keys import PUBLIC_RELEASE_EXTENSIONS, build_public_release_key

from .processing import checksum_bytes


class ImmutableImageStorageError(RuntimeError):
    pass


class ImmutableImageStorageConflict(ImmutableImageStorageError):
    pass


class ImageStorageFeatureDisabledError(ImmutableImageStorageError):
    pass


@dataclass(frozen=True)
class ImmutableStorageResult:
    alias: str
    key: str
    checksum_sha256: str
    created: bool


def _validate_public_delivery_key(key: str) -> None:
    parts = key.split("/")
    if len(parts) != 3 or parts[0] != "releases" or "." not in parts[2]:
        raise ImmutableImageStorageError("Public delivery key is not canonical.")
    variant, extension = parts[2].rsplit(".", 1)
    formats = {
        public_extension: output_format
        for output_format, public_extension in PUBLIC_RELEASE_EXTENSIONS.items()
    }
    try:
        expected = build_public_release_key(
            parts[1], variant, formats[extension]
        )
    except (KeyError, ValueError) as error:
        raise ImmutableImageStorageError(
            "Public delivery key is not canonical."
        ) from error
    if key != expected:
        raise ImmutableImageStorageError("Public delivery key is not canonical.")


def _read_verified(storage, key: str, expected_bytes: bytes, expected_checksum: str) -> None:
    try:
        with storage.open(key, "rb") as stored:
            actual_bytes = stored.read()
    except (OSError, ValueError) as error:
        raise ImmutableImageStorageError(f"Stored object {key} cannot be verified.") from error
    if checksum_bytes(actual_bytes) != expected_checksum or actual_bytes != expected_bytes:
        raise ImmutableImageStorageConflict(f"Immutable object conflict for {key}.")


def _save_immutable(
    *,
    alias: str,
    requested_key: str,
    data: bytes,
    content_type: str,
) -> ImmutableStorageResult:
    if not settings.IMAGE_ASSET_FEATURE_ENABLED:
        raise ImageStorageFeatureDisabledError(
            "Image asset feature is disabled; image storage writes are unavailable."
        )
    validate_storage_key(requested_key)
    if alias not in {
        "image_originals_private",
        "image_renditions_public",
        "public_image_delivery",
    }:
        raise ImmutableImageStorageError("Unsupported image storage alias.")
    if (
        alias == "public_image_delivery"
        and not settings.PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED
    ):
        raise ImageStorageFeatureDisabledError(
            "Public image materialization is disabled."
        )
    if alias == "public_image_delivery":
        _validate_public_delivery_key(requested_key)
    if not isinstance(data, bytes) or not data:
        raise ImmutableImageStorageError("Immutable image storage requires non-empty bytes.")

    expected_checksum = checksum_bytes(data)
    storage = storages[alias]
    if storage.exists(requested_key):
        _read_verified(storage, requested_key, data, expected_checksum)
        return ImmutableStorageResult(alias, requested_key, expected_checksum, False)

    content = ContentFile(data, name=requested_key.rsplit("/", 1)[-1])
    content.content_type = content_type
    saved_key = storage.save(requested_key, content)
    if saved_key != requested_key:
        try:
            storage.delete(saved_key)
        except (OSError, ValueError):
            pass
        raise ImmutableImageStorageConflict(
            f"Storage returned {saved_key!r} instead of exact requested key {requested_key!r}."
        )
    _read_verified(storage, requested_key, data, expected_checksum)
    return ImmutableStorageResult(alias, requested_key, expected_checksum, True)

from __future__ import annotations

import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from image_safety.release_keys import InvalidPublicReleaseKeyError, build_public_release_key


_PUBLIC_KEY_RE = re.compile(
    r"releases/(?P<release_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/"
    r"(?P<variant>square|landscape|share)\.(?P<extension>webp|png|jpg)\Z"
)
_FORMAT_BY_EXTENSION = {"webp": "webp", "png": "png", "jpg": "jpeg"}
_FALLBACK_PATHS = {
    "square": "crm/public-image-fallback/v1/fallback-square.png",
    "landscape": "crm/public-image-fallback/v1/fallback-landscape.png",
    "share": "crm/public-image-fallback/v1/fallback-share.png",
}


class InvalidPublicMediaKey(ValueError):
    pass


def validate_canonical_public_key(public_storage_key: str) -> str:
    if not isinstance(public_storage_key, str):
        raise InvalidPublicMediaKey("Public media key must be a string.")
    match = _PUBLIC_KEY_RE.fullmatch(public_storage_key)
    if match is None:
        raise InvalidPublicMediaKey("Public media key is not canonical.")
    try:
        expected = build_public_release_key(
            match.group("release_id"),
            match.group("variant"),
            _FORMAT_BY_EXTENSION[match.group("extension")],
        )
    except InvalidPublicReleaseKeyError as error:
        raise InvalidPublicMediaKey("Public media key is not canonical.") from error
    if public_storage_key != expected:
        raise InvalidPublicMediaKey("Public media key is not canonical.")
    return public_storage_key


def build_public_media_url(public_storage_key: str) -> str:
    canonical_key = validate_canonical_public_key(public_storage_key)
    origin = settings.PUBLIC_MEDIA_ORIGIN
    if not origin:
        raise ImproperlyConfigured("PUBLIC_MEDIA_ORIGIN is not configured.")
    return f"{origin}/media/{canonical_key}"


def build_public_fallback_url(variant: str) -> str:
    try:
        path = _FALLBACK_PATHS[variant]
    except (KeyError, TypeError) as error:
        raise InvalidPublicMediaKey("Public fallback variant is invalid.") from error
    origin = settings.PUBLIC_SITE_ORIGIN
    if not origin:
        raise ImproperlyConfigured("PUBLIC_SITE_ORIGIN is not configured.")
    return f"{origin}/static/{path}"

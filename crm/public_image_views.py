from __future__ import annotations

import logging
from time import monotonic

from django.http import HttpResponse, HttpResponseNotAllowed
from django.utils.http import parse_etags, quote_etag

from .services.images.serving import (
    PublicImageNotFound,
    PublicImageUnavailable,
    prepare_public_image,
)


LOGGER = logging.getLogger("crm.public_image_serving")
_CACHE_CONTROL = "private, max-age=60, must-revalidate"


def _error_response(status: int) -> HttpResponse:
    response = HttpResponse(status=status)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _not_modified(request, etag: str) -> bool:
    candidates = parse_etags(request.headers.get("If-None-Match", ""))
    return "*" in candidates or etag in {
        candidate.removeprefix("W/") for candidate in candidates
    }


def public_image_release(request, release_id, variant: str, extension: str):
    started = monotonic()
    status = 500
    outcome = "internal_error"
    safety_category = "not_checked"
    safety_cursor = None
    canonical_id = str(release_id)
    if request.method not in {"GET", "HEAD"}:
        status = 405
        outcome = "method_not_allowed"
        response = HttpResponseNotAllowed(["GET", "HEAD"])
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
    else:
        try:
            prepared = prepare_public_image(
                release_id=canonical_id,
                variant=variant,
                extension=extension,
            )
        except PublicImageNotFound:
            status = 404
            outcome = "not_found"
            response = _error_response(status)
        except PublicImageUnavailable:
            status = 503
            outcome = "safety_unavailable"
            response = _error_response(status)
        else:
            safety_category = prepared.safety_category
            safety_cursor = prepared.safety_cursor
            etag = quote_etag(prepared.checksum_sha256)
            if _not_modified(request, etag):
                status = 304
                outcome = "not_modified"
                response = HttpResponse(status=304)
            else:
                status = 200
                outcome = "authorized"
                response = HttpResponse(status=200, content_type=prepared.content_type)
                response["Content-Length"] = str(prepared.content_length)
                response["X-Accel-Redirect"] = prepared.internal_redirect
            response["ETag"] = etag
            response["Cache-Control"] = _CACHE_CONTROL
            response["X-Content-Type-Options"] = "nosniff"

    LOGGER.info(
        "outcome=%s release_id=%s variant=%s http_status=%s safety_category=%s "
        "safety_cursor=%s duration_ms=%.3f",
        outcome,
        canonical_id,
        variant,
        status,
        safety_category,
        safety_cursor,
        (monotonic() - started) * 1000,
    )
    return response

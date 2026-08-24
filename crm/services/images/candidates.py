from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
import warnings
from urllib.parse import urljoin, urlsplit

from django.conf import settings
from django.core import signing
from django.core.files.storage import storages
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from crm.models import (
    ImageRendition,
    ImageRenditionSet,
    ImageReviewEvent,
    Organization,
    OrganizationImageSelection,
    Tenant,
    TenantMembership,
)
from crm.services.open_graph import MetaParser, _candidate_score, is_fallback_preview_image

from .brave import (
    BraveImageSearchError,
    build_search_context,
    prepare_search_query,
    rank_brave_results,
    search_brave_images,
)
from .fetch import SecureImageFetchError, fetch_external_resource, normalize_external_url
from .ingest import ingest_uploaded_image
from .processing import MAX_SOURCE_PIXELS, checksum_bytes
from .selections import (
    ALLOWED_SELECTION_ROLES,
    AssetApprovalEvidence,
    OrganizationImageSelectionResult,
    lock_organization_image_selection,
)
from .safety_guards import legacy_image_is_blocked


CANDIDATE_REF_SALT = "crm.image-candidate.v1"
APPROVAL_REF_SALT = "crm.image-approval.v1"
RENDITION_PREVIEW_REF_SALT = "crm.image-rendition-preview.v1"
REF_TTL_SECONDS = 30 * 60
MAX_DISCOVERY_HTML_BYTES = 1_000_000
MAX_CANDIDATES = 6
MAX_CANDIDATE_PREVIEW_PIXELS = 12_000_000
MAX_CANDIDATE_PREVIEW_DIMENSION = 640
MAX_CANDIDATE_PREVIEW_BYTES = 1_000_000


class ImageCandidateFlowError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ImageCandidateFeatureDisabledError(ImageCandidateFlowError):
    def __init__(self) -> None:
        super().__init__("feature_disabled", "Image candidate flow is disabled.")


class ImageCandidatePermissionDenied(ImageCandidateFlowError):
    def __init__(self) -> None:
        super().__init__("permission_denied", "Image candidate capability is required.")


@dataclass(frozen=True, slots=True)
class OfficialImageCandidate:
    candidate_ref: str
    source_type: str
    source_label: str
    source_domain: str | None
    provider: str | None
    width: int | None
    height: int | None
    technical_status: str
    source_title: str | None = None
    source_publisher: str | None = None
    source_key: str | None = None


@dataclass(frozen=True, slots=True)
class CandidatePreview:
    body: bytes
    content_type: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ProcessedOfficialCandidate:
    approval_ref: str
    rendition_preview_ref: str
    asset_id: int
    rendition_set_id: int
    variants: tuple[str, ...]
    warnings: tuple[str, ...]
    status: str


def _feature_guard() -> None:
    if not settings.IMAGE_ASSET_FEATURE_ENABLED:
        raise ImageCandidateFeatureDisabledError()


def _validate_actor(actor, tenant_id: int, *, allow_reader: bool = False) -> None:
    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
        or not getattr(actor, "is_active", False)
        or not getattr(actor, "pk", None)
    ):
        raise ImageCandidatePermissionDenied()
    if actor.is_superuser:
        return
    roles = TenantMembership.Role.values if allow_reader else ALLOWED_SELECTION_ROLES
    if not TenantMembership.objects.filter(
        tenant_id=tenant_id,
        user_id=actor.pk,
        role__in=roles,
    ).exists():
        raise ImageCandidatePermissionDenied()


def _organization(tenant_id: int, organization_id: int) -> Organization:
    organization = Organization.objects.filter(pk=organization_id, tenant_id=tenant_id).first()
    if organization is None:
        raise ImageCandidateFlowError("not_found", "Organization was not found in the tenant.")
    return organization


def _signed_payload(payload: dict[str, object], salt: str) -> str:
    return signing.dumps(payload, salt=salt, compress=True)


def _load_signed_payload(
    value: str,
    *,
    salt: str,
    actor,
    tenant_id: int,
    organization_id: int,
) -> dict[str, object]:
    if not isinstance(value, str) or not value:
        raise ImageCandidateFlowError("invalid_ref", "A signed image reference is required.")
    try:
        payload = signing.loads(value, salt=salt, max_age=REF_TTL_SECONDS)
    except signing.SignatureExpired as error:
        raise ImageCandidateFlowError("expired_ref", "The image reference has expired.") from error
    except signing.BadSignature as error:
        raise ImageCandidateFlowError("invalid_ref", "The image reference is invalid.") from error
    if not isinstance(payload, dict):
        raise ImageCandidateFlowError("invalid_ref", "The image reference payload is invalid.")
    if (
        payload.get("tenant_id") != tenant_id
        or payload.get("organization_id") != organization_id
        or payload.get("user_id") != actor.pk
    ):
        raise ImageCandidateFlowError("wrong_scope", "The image reference does not match this context.")
    return payload


def _candidate_payload(
    *,
    tenant_id: int,
    organization_id: int,
    actor,
    source_type: str,
    image_url: str,
    source_page_url: str | None,
    provider: str | None,
    width: int | None,
    height: int | None,
    preview_url: str | None = None,
    source_domain: str | None = None,
    source_title: str | None = None,
    source_publisher: str | None = None,
    search_query: str | None = None,
    query_sources: tuple[str, ...] = (),
    derive_source_domain: bool = True,
) -> dict[str, object]:
    discovered_at = timezone.now()
    source_url_for_domain = source_page_url or image_url
    resolved_source_domain = source_domain
    if resolved_source_domain is None and derive_source_domain:
        resolved_source_domain = urlsplit(source_url_for_domain).hostname or None
    return {
        "version": 1,
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "user_id": actor.pk,
        "source_type": source_type,
        "image_url": image_url,
        "preview_url": preview_url,
        "source_page_url": source_page_url or "",
        "source_domain": resolved_source_domain,
        "provider": provider,
        "width": width,
        "height": height,
        "source_title": source_title,
        "source_publisher": source_publisher,
        "search_query": search_query,
        "query_sources": list(query_sources),
        "discovered_at": discovered_at.isoformat(),
        "expires_at": (discovered_at + timedelta(seconds=REF_TTL_SECONDS)).isoformat(),
    }


def _candidate_from_payload(payload: dict[str, object]) -> OfficialImageCandidate:
    source_type = str(payload["source_type"])
    labels = {
        ImageReviewEvent.SourceType.OPEN_GRAPH: "Open Graph",
        ImageReviewEvent.SourceType.WEBSITE_IMAGE: "Offisiell nettside",
        ImageReviewEvent.SourceType.OFFICIAL_WEBSITE: "Lagret nettsidebilde",
        ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH: "Bildesøk",
        ImageReviewEvent.SourceType.PASTED_URL: "Direkte bilde-URL",
    }
    return OfficialImageCandidate(
        candidate_ref=_signed_payload(payload, CANDIDATE_REF_SALT),
        source_type=source_type,
        source_label=(
            str(payload["source_label"])
            if isinstance(payload.get("source_label"), str)
            else labels.get(source_type, "Offisiell nettside")
        ),
        source_domain=(
            str(payload["source_domain"])
            if isinstance(payload.get("source_domain"), str)
            else None
        ),
        provider=(
            str(payload["provider"])
            if isinstance(payload.get("provider"), str)
            else None
        ),
        width=payload.get("width") if isinstance(payload.get("width"), int) else None,
        height=payload.get("height") if isinstance(payload.get("height"), int) else None,
        technical_status="ready_for_preview",
        source_title=(
            str(payload["source_title"])
            if isinstance(payload.get("source_title"), str)
            else None
        ),
        source_publisher=(
            str(payload["source_publisher"])
            if isinstance(payload.get("source_publisher"), str)
            else None
        ),
        source_key=(
            str(payload["source_key"])
            if isinstance(payload.get("source_key"), str)
            else None
        ),
    )


def _normalized_candidate_url(page_url: str, value: str) -> str | None:
    if not value or value.lstrip().casefold().startswith("data:"):
        return None
    try:
        return normalize_external_url(urljoin(page_url, value))
    except SecureImageFetchError:
        return None


def _normalized_legacy_url(value: str) -> str | None:
    try:
        if urlsplit(value).fragment:
            return None
        return normalize_external_url(value)
    except (SecureImageFetchError, ValueError):
        return None


def get_legacy_image_candidates(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
) -> tuple[OfficialImageCandidate, ...]:
    """Return signed legacy refs without DNS, HTTP, decoding, or persistence."""
    _feature_guard()
    _validate_actor(actor, tenant_id)
    organization = _organization(tenant_id, organization_id)
    if legacy_image_is_blocked(
        tenant_id=tenant_id,
        organization_id=organization_id,
    ):
        return ()

    sources = (
        (
            "thumbnail_image_url",
            organization.thumbnail_image_url,
            ImageReviewEvent.SourceType.PASTED_URL,
            "Tidligere manuelt bilde",
        ),
        (
            "og_image_url",
            organization.og_image_url,
            ImageReviewEvent.SourceType.OPEN_GRAPH,
            "Tidligere Open Graph-bilde",
        ),
        (
            "auto_thumbnail_url",
            organization.auto_thumbnail_url,
            ImageReviewEvent.SourceType.OFFICIAL_WEBSITE,
            "Tidligere automatisk bilde",
        ),
    )
    candidates: list[OfficialImageCandidate] = []
    seen: set[str] = set()
    for source_key, raw_url, source_type, source_label in sources:
        if not raw_url or is_fallback_preview_image(raw_url):
            continue
        normalized_url = _normalized_legacy_url(raw_url)
        if normalized_url is None or normalized_url in seen:
            continue
        seen.add(normalized_url)
        payload = _candidate_payload(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            source_type=source_type,
            image_url=normalized_url,
            source_page_url=None,
            provider="legacy_database",
            width=None,
            height=None,
        )
        payload["source_key"] = source_key
        payload["source_label"] = source_label
        candidates.append(_candidate_from_payload(payload))
    return tuple(candidates)


def discover_official_image_candidates(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
) -> tuple[OfficialImageCandidate, ...]:
    _feature_guard()
    _validate_actor(actor, tenant_id)
    organization = _organization(tenant_id, organization_id)
    if not organization.website_url:
        return ()

    page_url = normalize_external_url(organization.website_url)
    raw_candidates: list[tuple[int, str, str, int | None, int | None]] = []

    try:
        page = fetch_external_resource(
            page_url,
            expected="html",
            max_bytes=MAX_DISCOVERY_HTML_BYTES,
        )
    except SecureImageFetchError:
        raise
    if page is not None:
        parser = MetaParser()
        parser.feed(page.body.decode("utf-8", errors="replace"))
        for candidate in parser.image_candidates:
            source_type = (
                ImageReviewEvent.SourceType.OPEN_GRAPH
                if candidate.source in {"og:image", "twitter:image"}
                else ImageReviewEvent.SourceType.WEBSITE_IMAGE
            )
            priority = 300 if candidate.source == "og:image" else 250 if candidate.source == "twitter:image" else _candidate_score(candidate)
            raw_candidates.append((priority, candidate.url, source_type, candidate.width, candidate.height))

    results: list[OfficialImageCandidate] = []
    seen: set[str] = set()
    for _, candidate_url, source_type, width, height in sorted(raw_candidates, key=lambda item: item[0], reverse=True):
        source_page_url = page.final_url if page is not None else page_url
        normalized_url = _normalized_candidate_url(source_page_url, candidate_url)
        if not normalized_url or normalized_url in seen:
            continue
        seen.add(normalized_url)
        payload = _candidate_payload(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            source_type=source_type,
            image_url=normalized_url,
            source_page_url=source_page_url,
            provider="official_website",
            width=width,
            height=height,
        )
        results.append(_candidate_from_payload(payload))
        if len(results) == MAX_CANDIDATES:
            break
    return tuple(results)


def get_brave_search_context(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
) -> dict[str, object]:
    _feature_guard()
    _validate_actor(actor, tenant_id)
    organization = _organization(tenant_id, organization_id)
    context = build_search_context(organization)
    return {
        "suggested_query": context.suggested_query,
        "query_sources": list(context.query_sources),
        "municipalities": list(context.municipalities),
        "categories": list(context.categories),
        "people": list(context.people),
    }


def discover_brave_image_candidates(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    query: object,
    municipality: object = None,
    category_id: object = None,
    person_id: object = None,
    query_edited: bool = False,
) -> tuple[str, tuple[str, ...], tuple[OfficialImageCandidate, ...]]:
    _feature_guard()
    _validate_actor(actor, tenant_id)
    organization = _organization(tenant_id, organization_id)
    if not isinstance(query_edited, bool):
        raise BraveImageSearchError(
            "invalid_query",
            "query_edited må være true eller false.",
        )
    prepared_query = prepare_search_query(
        organization,
        query=query,
        municipality=municipality,
        category_id=category_id,
        person_id=person_id,
        query_edited=query_edited,
    )
    provider_results = search_brave_images(prepared_query.query)
    ranked_results = rank_brave_results(
        provider_results,
        organization=organization,
        prepared_query=prepared_query,
    )

    candidates: list[OfficialImageCandidate] = []
    for result in ranked_results:
        if result.image_url is None:
            continue
        payload = _candidate_payload(
            tenant_id=tenant_id,
            organization_id=organization_id,
            actor=actor,
            source_type=ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH,
            image_url=result.image_url,
            preview_url=result.thumbnail_url,
            source_page_url=result.source_page_url,
            source_domain=result.source_domain,
            provider="brave_image_search",
            width=result.width,
            height=result.height,
            source_title=result.title,
            source_publisher=result.publisher,
            search_query=prepared_query.query,
            query_sources=prepared_query.query_sources,
            derive_source_domain=False,
        )
        candidates.append(_candidate_from_payload(payload))
    return prepared_query.query, prepared_query.query_sources, tuple(candidates)


def create_pasted_url_candidate(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    image_url: object,
) -> OfficialImageCandidate:
    _feature_guard()
    _validate_actor(actor, tenant_id)
    _organization(tenant_id, organization_id)
    if not isinstance(image_url, str):
        raise SecureImageFetchError("invalid_url", "Image URL is required.")
    normalized_url = normalize_external_url(image_url)
    payload = _candidate_payload(
        tenant_id=tenant_id,
        organization_id=organization_id,
        actor=actor,
        source_type=ImageReviewEvent.SourceType.PASTED_URL,
        image_url=normalized_url,
        source_page_url=None,
        provider="pasted_url",
        width=None,
        height=None,
    )
    return _candidate_from_payload(payload)


def _candidate_context(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    candidate_ref: str,
) -> dict[str, object]:
    _feature_guard()
    _validate_actor(actor, tenant_id)
    _organization(tenant_id, organization_id)
    payload = _load_signed_payload(
        candidate_ref,
        salt=CANDIDATE_REF_SALT,
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )
    if payload.get("source_type") not in {
        ImageReviewEvent.SourceType.OPEN_GRAPH,
        ImageReviewEvent.SourceType.WEBSITE_IMAGE,
        ImageReviewEvent.SourceType.OFFICIAL_WEBSITE,
        ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH,
        ImageReviewEvent.SourceType.PASTED_URL,
    }:
        raise ImageCandidateFlowError("invalid_ref", "Candidate source is unsupported.")
    if not isinstance(payload.get("image_url"), str):
        raise ImageCandidateFlowError("invalid_ref", "Candidate image URL is invalid.")
    if payload.get("provider") == "legacy_database" and legacy_image_is_blocked(
        tenant_id=tenant_id,
        organization_id=organization_id,
    ):
        raise ImageCandidateFlowError(
            "legacy_blocked",
            "The stored legacy image is no longer available.",
        )
    return payload


def render_candidate_preview(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    candidate_ref: str,
    original: bool = False,
) -> CandidatePreview:
    payload = _candidate_context(
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
        candidate_ref=candidate_ref,
    )
    if not isinstance(original, bool):
        raise ImageCandidateFlowError(
            "invalid_preview_mode",
            "Candidate preview original mode must be true or false.",
        )
    preview_url = (
        payload["image_url"]
        if original
        else payload.get("preview_url") or payload["image_url"]
    )
    if not isinstance(preview_url, str):
        raise ImageCandidateFlowError("invalid_ref", "Candidate preview URL is invalid.")
    fetched = fetch_external_resource(preview_url, expected="image")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(fetched.body)) as opened:
                preview_pixel_limit = (
                    MAX_SOURCE_PIXELS if original else MAX_CANDIDATE_PREVIEW_PIXELS
                )
                if opened.width * opened.height > preview_pixel_limit:
                    raise ImageCandidateFlowError("preview_pixel_limit", "Candidate preview exceeds pixel limit.")
                if int(getattr(opened, "n_frames", 1)) != 1 or bool(getattr(opened, "is_animated", False)):
                    raise ImageCandidateFlowError("preview_animated", "Animated candidate previews are unsupported.")
                opened.load()
                has_alpha = "A" in opened.getbands() or "transparency" in opened.info
                image = ImageOps.exif_transpose(opened).convert("RGBA" if has_alpha else "RGB")
    except ImageCandidateFlowError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImageCandidateFlowError("preview_pixel_limit", "Candidate preview exceeds pixel limit.") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise ImageCandidateFlowError("preview_decode", "Candidate preview could not be decoded.") from error

    image.thumbnail(
        (MAX_CANDIDATE_PREVIEW_DIMENSION, MAX_CANDIDATE_PREVIEW_DIMENSION),
        Image.Resampling.LANCZOS,
    )
    output = BytesIO()
    image.save(output, "WEBP", quality=76, method=4, exif=b"", icc_profile=b"", xmp=b"")
    body = output.getvalue()
    if len(body) > MAX_CANDIDATE_PREVIEW_BYTES:
        raise ImageCandidateFlowError("preview_size_limit", "Candidate preview exceeds output limit.")
    return CandidatePreview(body=body, content_type="image/webp", width=image.width, height=image.height)


def _validate_processing_options(
    *,
    image_kind: object,
    focus_x: float | None,
    focus_y: float | None,
    zoom: float | None,
) -> str:
    if image_kind not in {"photo", "logo"}:
        raise ImageCandidateFlowError("invalid_image_kind", "Image kind must be photo or logo.")
    if image_kind == "logo" and (focus_x is not None or focus_y is not None or zoom is not None):
        raise ImageCandidateFlowError("invalid_crop_recipe", "Logo processing does not accept focus or zoom.")
    return str(image_kind)


def _processed_candidate_result(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    image_kind: str,
    source_type: str,
    source_url: str,
    source_page_url: str,
    provider: str,
    ingest_result,
    search_query: str | None = None,
    query_sources: tuple[str, ...] = (),
) -> ProcessedOfficialCandidate:
    processed_at = timezone.now()
    approval_payload = {
        "version": 1,
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "user_id": actor.pk,
        "source_type": source_type,
        "source_url": source_url,
        "source_page_url": source_page_url,
        "provider": provider,
        "asset_checksum_sha256": ingest_result.asset.checksum_sha256,
        "rendition_set_id": ingest_result.rendition_set.pk,
        "image_kind": image_kind,
        "fit_mode": ingest_result.rendition_set.fit_mode,
        "technical_warnings": list(ingest_result.warnings),
        "search_query": search_query,
        "query_sources": list(query_sources),
        "processed_at": processed_at.isoformat(),
        "expires_at": (processed_at + timedelta(seconds=REF_TTL_SECONDS)).isoformat(),
    }
    preview_payload = {
        "version": 1,
        "tenant_id": tenant_id,
        "organization_id": organization_id,
        "user_id": actor.pk,
        "rendition_set_id": ingest_result.rendition_set.pk,
    }
    return ProcessedOfficialCandidate(
        approval_ref=_signed_payload(approval_payload, APPROVAL_REF_SALT),
        rendition_preview_ref=_signed_payload(preview_payload, RENDITION_PREVIEW_REF_SALT),
        asset_id=ingest_result.asset.pk,
        rendition_set_id=ingest_result.rendition_set.pk,
        variants=tuple(rendition.variant for rendition in ingest_result.renditions),
        warnings=ingest_result.warnings,
        status=ingest_result.status,
    )


def process_image_candidate(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    candidate_ref: str,
    image_kind: str,
    focus_x: float | None = None,
    focus_y: float | None = None,
    zoom: float | None = None,
) -> ProcessedOfficialCandidate:
    payload = _candidate_context(
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
        candidate_ref=candidate_ref,
    )
    normalized_kind = _validate_processing_options(
        image_kind=image_kind,
        focus_x=focus_x,
        focus_y=focus_y,
        zoom=zoom,
    )
    fetched = fetch_external_resource(str(payload["image_url"]), expected="image")
    upload = BytesIO(fetched.body)
    upload.content_type = fetched.content_type
    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if tenant is None:
        raise ImageCandidateFlowError("not_found", "Tenant was not found.")
    result = ingest_uploaded_image(
        tenant=tenant,
        upload=upload,
        content_mode="cover" if normalized_kind == "photo" else "contain",
        focus_x=focus_x,
        focus_y=focus_y,
        zoom=zoom,
    )
    source_type = str(payload["source_type"])
    transient_query_sources = payload.get("query_sources")
    query_sources = (
        tuple(str(value) for value in transient_query_sources if isinstance(value, str))
        if isinstance(transient_query_sources, list)
        else ()
    )
    brave_source = source_type == ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH
    return _processed_candidate_result(
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
        image_kind=normalized_kind,
        source_type=source_type,
        source_url="" if brave_source else str(payload["image_url"]),
        source_page_url="" if brave_source else str(payload.get("source_page_url") or ""),
        provider=str(payload.get("provider") or ""),
        ingest_result=result,
        search_query=(
            str(payload["search_query"])
            if isinstance(payload.get("search_query"), str)
            else None
        ),
        query_sources=query_sources,
    )


def process_uploaded_image_candidate(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    upload,
    image_kind: str,
    focus_x: float | None = None,
    focus_y: float | None = None,
    zoom: float | None = None,
) -> ProcessedOfficialCandidate:
    _feature_guard()
    _validate_actor(actor, tenant_id)
    _organization(tenant_id, organization_id)
    normalized_kind = _validate_processing_options(
        image_kind=image_kind,
        focus_x=focus_x,
        focus_y=focus_y,
        zoom=zoom,
    )
    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if tenant is None:
        raise ImageCandidateFlowError("not_found", "Tenant was not found.")
    result = ingest_uploaded_image(
        tenant=tenant,
        upload=upload,
        content_mode="cover" if normalized_kind == "photo" else "contain",
        focus_x=focus_x,
        focus_y=focus_y,
        zoom=zoom,
    )
    return _processed_candidate_result(
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
        image_kind=normalized_kind,
        source_type=ImageReviewEvent.SourceType.UPLOAD,
        source_url="",
        source_page_url="",
        provider="manual_upload",
        ingest_result=result,
    )


def process_official_image_candidate(**kwargs) -> ProcessedOfficialCandidate:
    """Compatibility wrapper for the phase 3D.1 service name."""

    return process_image_candidate(**kwargs)


def _rendition_preview_payload(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    preview_ref: str,
) -> dict[str, object]:
    _feature_guard()
    _validate_actor(actor, tenant_id, allow_reader=True)
    _organization(tenant_id, organization_id)
    return _load_signed_payload(
        preview_ref,
        salt=RENDITION_PREVIEW_REF_SALT,
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )


def read_rendition_preview(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    preview_ref: str,
    variant: str,
) -> tuple[bytes, str]:
    payload = _rendition_preview_payload(
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
        preview_ref=preview_ref,
    )
    if variant not in ImageRendition.Variant.values:
        raise ImageCandidateFlowError("invalid_variant", "Preview variant is invalid.")
    rendition = ImageRendition.objects.filter(
        tenant_id=tenant_id,
        rendition_set_id=payload.get("rendition_set_id"),
        variant=variant,
    ).first()
    if rendition is None:
        raise ImageCandidateFlowError("not_found", "Rendition preview was not found.")
    storage = storages["image_renditions_public"]
    try:
        with storage.open(rendition.artifact_storage_key, "rb") as source:
            body = source.read(rendition.file_size_bytes + 1)
    except (OSError, ValueError) as error:
        raise ImageCandidateFlowError("preview_unavailable", "Rendition preview is unavailable.") from error
    if len(body) != rendition.file_size_bytes or checksum_bytes(body) != rendition.checksum_sha256:
        raise ImageCandidateFlowError("preview_conflict", "Rendition preview failed integrity verification.")
    content_type = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[rendition.output_format]
    return body, content_type


def approve_image_candidate(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
    approval_ref: str,
    expected_revision: int,
    alt_text: str,
    public_credit: str = "",
) -> OrganizationImageSelectionResult:
    _feature_guard()
    _validate_actor(actor, tenant_id)
    _organization(tenant_id, organization_id)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
        raise ImageCandidateFlowError("invalid_revision", "Expected revision must be a non-negative integer.")
    if not isinstance(alt_text, str) or len(alt_text) > 500 or (
        alt_text and not alt_text.strip()
    ):
        raise ImageCandidateFlowError(
            "invalid_alt_text",
            "Alt text must be empty or contain at most 500 characters.",
        )
    if not isinstance(public_credit, str) or len(public_credit) > 500 or (
        public_credit and not public_credit.strip()
    ):
        raise ImageCandidateFlowError(
            "invalid_public_credit",
            "Public credit must be empty or contain at most 500 characters.",
        )
    payload = _load_signed_payload(
        approval_ref,
        salt=APPROVAL_REF_SALT,
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
    )
    rendition_set = ImageRenditionSet.objects.select_related("asset").filter(
        pk=payload.get("rendition_set_id"),
        tenant_id=tenant_id,
    ).first()
    if rendition_set is None or rendition_set.asset.checksum_sha256 != payload.get("asset_checksum_sha256"):
        raise ImageCandidateFlowError("invalid_ref", "Approval reference no longer matches its image aggregate.")
    expected_fit = "cover" if payload.get("image_kind") == "photo" else "contain"
    if rendition_set.fit_mode != expected_fit or payload.get("fit_mode") != expected_fit:
        raise ImageCandidateFlowError("invalid_ref", "Approval reference processing mode is inconsistent.")
    evidence = AssetApprovalEvidence(
        source_type=str(payload["source_type"]),
        source_url=str(payload["source_url"]),
        source_page_url=str(payload["source_page_url"]),
        provider=str(payload["provider"]),
        technical_warnings=tuple(payload.get("technical_warnings", ())),
    )
    return lock_organization_image_selection(
        actor=actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
        expected_revision=expected_revision,
        selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
        rendition_set_id=rendition_set.pk,
        alt_text=alt_text,
        public_credit=public_credit,
        asset_evidence=evidence,
    )


def approve_official_image_candidate(**kwargs) -> OrganizationImageSelectionResult:
    """Compatibility wrapper for the phase 3D.1 service name."""

    return approve_image_candidate(**kwargs)


def get_organization_image_state(
    *,
    actor,
    tenant_id: int,
    organization_id: int,
) -> dict[str, object]:
    _feature_guard()
    _validate_actor(actor, tenant_id, allow_reader=True)
    _organization(tenant_id, organization_id)
    selection = OrganizationImageSelection.objects.filter(
        tenant_id=tenant_id,
        organization_id=organization_id,
        status=OrganizationImageSelection.Status.ACTIVE,
    ).first()
    if selection is None:
        return {"active_selection": None, "expected_revision": 0}
    preview_ref = None
    variants: list[str] = []
    if selection.rendition_set_id:
        payload = {
            "version": 1,
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "user_id": actor.pk,
            "rendition_set_id": selection.rendition_set_id,
        }
        preview_ref = _signed_payload(payload, RENDITION_PREVIEW_REF_SALT)
        variants = list(
            ImageRendition.objects.filter(
                tenant_id=tenant_id,
                rendition_set_id=selection.rendition_set_id,
            ).order_by("variant").values_list("variant", flat=True)
        )
    return {
        "expected_revision": selection.revision,
        "active_selection": {
            "id": selection.pk,
            "revision": selection.revision,
            "status": selection.status,
            "kind": selection.selection_kind,
            "alt_text": selection.alt_text,
            "public_credit": selection.public_credit,
            "rendition_preview_ref": preview_ref,
            "variants": variants,
        },
    }

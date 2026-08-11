from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
import socket
import ssl
from typing import Callable
from urllib.parse import urlencode, urlsplit

from django.conf import settings

from crm.models import Organization, OrganizationPerson

from .fetch import SecureImageFetchError, normalize_external_url


BRAVE_API_HOST = "api.search.brave.com"
BRAVE_API_PATH = "/res/v1/images/search"
BRAVE_RESULT_COUNT = 30
BRAVE_RESPONSE_MAX_BYTES = 2 * 1024 * 1024
BRAVE_TIMEOUT_SECONDS = 10.0
MAX_QUERY_LENGTH = 400
MAX_QUERY_WORDS = 50

QUERY_SOURCE_ORGANIZATION = "organization_name"
QUERY_SOURCE_MUNICIPALITY = "municipality"
QUERY_SOURCE_CATEGORY = "category"
QUERY_SOURCE_PERSON = "person"
QUERY_SOURCE_MANUAL_EDIT = "manual_edit"


class BraveImageSearchError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class BraveSearchContext:
    suggested_query: str
    query_sources: tuple[str, ...]
    municipalities: tuple[str, ...]
    categories: tuple[dict[str, object], ...]
    people: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class PreparedBraveQuery:
    query: str
    query_sources: tuple[str, ...]
    selected_municipality: str | None
    selected_category: str | None
    selected_person: str | None


@dataclass(frozen=True, slots=True)
class BraveImageResult:
    image_url: str | None
    thumbnail_url: str | None
    source_page_url: str | None
    source_domain: str | None
    title: str | None
    publisher: str | None
    width: int | None
    height: int | None
    provider_index: int


BraveTransport = Callable[[str, dict[str, str], float], tuple[int, str, bytes]]


def _default_transport(
    path: str,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, str, bytes]:
    connection = http.client.HTTPSConnection(
        BRAVE_API_HOST,
        port=443,
        timeout=timeout,
        context=ssl.create_default_context(),
    )
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().casefold()
        content_length = response.getheader("Content-Length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError as error:
                raise BraveImageSearchError(
                    "provider_malformed",
                    "Bildesøket returnerte en ugyldig respons.",
                ) from error
            if declared_size < 0 or declared_size > BRAVE_RESPONSE_MAX_BYTES:
                raise BraveImageSearchError(
                    "provider_malformed",
                    "Bildesøket returnerte en for stor respons.",
                )
        body = response.read(BRAVE_RESPONSE_MAX_BYTES + 1)
        if len(body) > BRAVE_RESPONSE_MAX_BYTES:
            raise BraveImageSearchError(
                "provider_malformed",
                "Bildesøket returnerte en for stor respons.",
            )
        return response.status, content_type, body
    finally:
        connection.close()


def _clean_optional_text(value: object, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    return cleaned[:max_length]


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _safe_external_url(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return normalize_external_url(value)
    except SecureImageFetchError:
        return None


def parse_municipalities(value: str | None) -> tuple[str, ...]:
    if not isinstance(value, str):
        return ()
    results: list[str] = []
    seen: set[str] = set()
    for raw_part in value.split(","):
        municipality = " ".join(raw_part.split())
        normalized = municipality.casefold()
        if municipality and normalized not in seen:
            seen.add(normalized)
            results.append(municipality)
    return tuple(results)


def _validate_query(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BraveImageSearchError("invalid_query", "Søketeksten kan ikke være tom.")
    if len(value) > MAX_QUERY_LENGTH:
        raise BraveImageSearchError("invalid_query", "Søketeksten er for lang.")
    if len(value.split()) > MAX_QUERY_WORDS:
        raise BraveImageSearchError("invalid_query", "Søketeksten inneholder for mange ord.")
    if any(ord(character) < 32 and character not in {"\t"} for character in value):
        raise BraveImageSearchError("invalid_query", "Søketeksten inneholder ugyldige tegn.")
    return value


def build_search_context(organization: Organization) -> BraveSearchContext:
    municipalities = parse_municipalities(organization.municipalities)
    suggested_parts = [organization.name]
    query_sources = [QUERY_SOURCE_ORGANIZATION]
    if len(municipalities) == 1:
        suggested_parts.append(municipalities[0])
        query_sources.append(QUERY_SOURCE_MUNICIPALITY)

    categories = tuple(
        {"id": category.pk, "name": category.name}
        for category in organization.categories.all().order_by("name", "pk")
    )
    people = tuple(
        {"id": link.person_id, "name": link.person.full_name}
        for link in organization.org_people.filter(status="ACTIVE")
        .select_related("person")
        .order_by("person__full_name", "person_id")
    )
    return BraveSearchContext(
        suggested_query=" ".join(suggested_parts),
        query_sources=tuple(query_sources),
        municipalities=municipalities,
        categories=categories,
        people=people,
    )


def prepare_search_query(
    organization: Organization,
    *,
    query: object,
    municipality: object = None,
    category_id: object = None,
    person_id: object = None,
    query_edited: bool = False,
) -> PreparedBraveQuery:
    exact_query = _validate_query(query)
    if query_edited:
        refinements = (municipality, category_id, person_id)
        if any(value is not None and value != "" for value in refinements):
            raise BraveImageSearchError(
                "invalid_refinement",
                "Manuelt redigerte søk kan ikke ha skjulte strukturerte tillegg.",
            )
        return PreparedBraveQuery(
            query=exact_query,
            query_sources=(QUERY_SOURCE_MANUAL_EDIT,),
            selected_municipality=None,
            selected_category=None,
            selected_person=None,
        )

    municipalities = parse_municipalities(organization.municipalities)

    selected_municipality = None
    if municipality is not None and municipality != "":
        if not isinstance(municipality, str):
            raise BraveImageSearchError("invalid_refinement", "Valgt kommune er ugyldig.")
        municipality_by_key = {item.casefold(): item for item in municipalities}
        selected_municipality = municipality_by_key.get(municipality.strip().casefold())
        if selected_municipality is None:
            raise BraveImageSearchError(
                "invalid_refinement",
                "Valgt kommune finnes ikke på aktøren.",
            )
    elif not query_edited and len(municipalities) == 1:
        selected_municipality = municipalities[0]

    selected_category = None
    if category_id is not None and category_id != "":
        if isinstance(category_id, bool):
            raise BraveImageSearchError("invalid_refinement", "Valgt kategori er ugyldig.")
        try:
            category_pk = int(category_id)
        except (TypeError, ValueError) as error:
            raise BraveImageSearchError("invalid_refinement", "Valgt kategori er ugyldig.") from error
        category = organization.categories.filter(pk=category_pk).first()
        if category is None:
            raise BraveImageSearchError(
                "invalid_refinement",
                "Valgt kategori finnes ikke på aktøren.",
            )
        selected_category = category.name

    selected_person = None
    if person_id is not None and person_id != "":
        if isinstance(person_id, bool):
            raise BraveImageSearchError("invalid_refinement", "Valgt person er ugyldig.")
        try:
            person_pk = int(person_id)
        except (TypeError, ValueError) as error:
            raise BraveImageSearchError("invalid_refinement", "Valgt person er ugyldig.") from error
        link = (
            OrganizationPerson.objects.filter(
                organization=organization,
                tenant_id=organization.tenant_id,
                person_id=person_pk,
                status="ACTIVE",
            )
            .select_related("person")
            .first()
        )
        if link is None:
            raise BraveImageSearchError(
                "invalid_refinement",
                "Valgt person er ikke aktivt tilknyttet aktøren.",
            )
        selected_person = link.person.full_name

    expected_parts = [organization.name]
    query_sources = [QUERY_SOURCE_ORGANIZATION]
    if selected_municipality:
        expected_parts.append(selected_municipality)
        query_sources.append(QUERY_SOURCE_MUNICIPALITY)
    if selected_category:
        expected_parts.append(selected_category)
        query_sources.append(QUERY_SOURCE_CATEGORY)
    if selected_person:
        expected_parts.append(selected_person)
        query_sources.append(QUERY_SOURCE_PERSON)
    expected_query = " ".join(expected_parts)
    if exact_query != expected_query:
        raise BraveImageSearchError(
            "query_mismatch",
            "Søketeksten må markeres som redigert når den avviker fra forslaget.",
        )

    return PreparedBraveQuery(
        query=exact_query,
        query_sources=tuple(query_sources),
        selected_municipality=selected_municipality,
        selected_category=selected_category,
        selected_person=selected_person,
    )


def _parse_result(item: object, provider_index: int) -> BraveImageResult | None:
    if not isinstance(item, dict):
        return None
    properties = item.get("properties") if isinstance(item.get("properties"), dict) else {}
    thumbnail = item.get("thumbnail") if isinstance(item.get("thumbnail"), dict) else {}
    meta_url = item.get("meta_url") if isinstance(item.get("meta_url"), dict) else {}

    image_url = _safe_external_url(properties.get("url"))
    if image_url is None:
        return None
    source_page_url = _safe_external_url(item.get("url"))
    source_domain = _clean_optional_text(meta_url.get("hostname"), max_length=255)
    if source_domain:
        source_domain = source_domain.rstrip(".").casefold()
        if any(character.isspace() for character in source_domain):
            source_domain = None
    if source_domain is None and source_page_url:
        source_domain = urlsplit(source_page_url).hostname
    return BraveImageResult(
        image_url=image_url,
        thumbnail_url=_safe_external_url(thumbnail.get("src")),
        source_page_url=source_page_url,
        source_domain=source_domain,
        title=_clean_optional_text(item.get("title"), max_length=500),
        publisher=_clean_optional_text(item.get("source"), max_length=255),
        width=_positive_int(properties.get("width")),
        height=_positive_int(properties.get("height")),
        provider_index=provider_index,
    )


def search_brave_images(
    query: str,
    *,
    transport: BraveTransport = _default_transport,
) -> tuple[BraveImageResult, ...]:
    exact_query = _validate_query(query)
    api_key = str(getattr(settings, "BRAVE_IMAGE_SEARCH_API_KEY", "") or "").strip()
    if not api_key:
        raise BraveImageSearchError(
            "brave_not_configured",
            "Bildesøk er ikke konfigurert i dette miljøet.",
        )

    parameters = urlencode(
        {
            "q": exact_query,
            "country": "NO",
            "search_lang": "nb",
            "safesearch": "strict",
            "spellcheck": "false",
            "count": str(BRAVE_RESULT_COUNT),
        }
    )
    path = f"{BRAVE_API_PATH}?{parameters}"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "KreativeNorgeImageSearch/1.0",
        "X-Subscription-Token": api_key,
    }
    try:
        status_code, content_type, body = transport(path, headers, BRAVE_TIMEOUT_SECONDS)
    except BraveImageSearchError:
        raise
    except (TimeoutError, socket.timeout) as error:
        raise BraveImageSearchError(
            "provider_timeout",
            "Bildesøket brukte for lang tid.",
        ) from error
    except (http.client.HTTPException, OSError, ssl.SSLError) as error:
        raise BraveImageSearchError(
            "provider_unavailable",
            "Bildesøket er midlertidig utilgjengelig.",
        ) from error

    if status_code == 429:
        raise BraveImageSearchError(
            "provider_rate_limited",
            "Bildesøket har nådd en midlertidig grense.",
        )
    if status_code < 200 or status_code >= 300:
        raise BraveImageSearchError(
            "provider_unavailable",
            "Bildesøket er midlertidig utilgjengelig.",
        )
    if content_type != "application/json":
        raise BraveImageSearchError(
            "provider_malformed",
            "Bildesøket returnerte en ugyldig respons.",
        )
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BraveImageSearchError(
            "provider_malformed",
            "Bildesøket returnerte en ugyldig respons.",
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise BraveImageSearchError(
            "provider_malformed",
            "Bildesøket returnerte en ugyldig respons.",
        )

    results: list[BraveImageResult] = []
    seen: set[str] = set()
    for provider_index, raw_result in enumerate(payload["results"]):
        result = _parse_result(raw_result, provider_index)
        if result is None or result.image_url is None or result.image_url in seen:
            continue
        seen.add(result.image_url)
        results.append(result)
        if len(results) == BRAVE_RESULT_COUNT:
            break
    return tuple(results)


def rank_brave_results(
    results: tuple[BraveImageResult, ...],
    *,
    organization: Organization,
    prepared_query: PreparedBraveQuery,
) -> tuple[BraveImageResult, ...]:
    official_domain = ""
    if organization.website_url:
        try:
            official_domain = urlsplit(normalize_external_url(organization.website_url)).hostname or ""
        except SecureImageFetchError:
            official_domain = ""
    organization_name = organization.name.casefold()
    refinements = tuple(
        value.casefold()
        for value in (
            prepared_query.selected_municipality,
            prepared_query.selected_category,
            prepared_query.selected_person,
        )
        if value
    )

    def rank(result: BraveImageResult) -> tuple[int, int, int, int]:
        source_domain = result.source_domain or ""
        searchable = " ".join(
            value for value in (result.title, result.publisher) if value
        ).casefold()
        return (
            int(bool(official_domain and source_domain == official_domain)),
            int(bool(organization_name and organization_name in searchable)),
            sum(1 for refinement in refinements if refinement in searchable),
            -result.provider_index,
        )

    return tuple(sorted(results, key=rank, reverse=True))

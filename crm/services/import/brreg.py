from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from .normalizers import normalize_domain, normalize_name, normalize_space


BRREG_API_BASE = "https://data.brreg.no/enhetsregisteret/api/enheter"
BRREG_USER_AGENT = "KreativeNorgeCRM/1.0 (+https://github.com/fredrik-stack/kreative-norge-crm)"
COMPANY_SUFFIXES = {
    "as",
    "asa",
    "ans",
    "ba",
    "da",
    "enk",
    "forening",
    "foreningen",
    "ikb",
    "ks",
    "nuf",
    "sa",
}


@dataclass
class BrregCandidate:
    org_number: str
    name: str
    municipality: str
    postal_place: str
    website_url: str
    email: str
    score: float


def normalize_org_number_candidate(value: str | None) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 9 else ""


def is_valid_org_number(value: str | None) -> bool:
    digits = normalize_org_number_candidate(value)
    if len(digits) != 9:
        return False
    weights = [3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(digit) * weight for digit, weight in zip(digits[:8], weights, strict=True))
    remainder = 11 - (total % 11)
    check_digit = 0 if remainder == 11 else remainder
    if check_digit == 10:
        return False
    return check_digit == int(digits[-1])


def _fetch_brreg_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": BRREG_USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=settings.BRREG_TIMEOUT) as response:  # noqa: S310 - fixed trusted host
        return json.loads(response.read().decode("utf-8"))


def _normalize_entity_name_for_match(value: str) -> str:
    normalized = normalize_name(value)
    tokens = [token for token in normalized.split() if token not in COMPANY_SUFFIXES]
    return " ".join(tokens)


def _score_candidate(
    *,
    query_name: str,
    entity_name: str,
    municipality: str,
    entity_municipality: str,
    postal_place: str,
    website_hint: str,
    entity_website: str,
) -> float:
    normalized_query = _normalize_entity_name_for_match(query_name)
    normalized_entity = _normalize_entity_name_for_match(entity_name)
    normalized_municipality = normalize_name(municipality)
    normalized_entity_municipality = normalize_name(entity_municipality)
    normalized_postal_place = normalize_name(postal_place)
    hinted_domain = normalize_domain(website_hint.split("@", 1)[1] if "@" in website_hint else website_hint)
    entity_domain = normalize_domain(entity_website)

    score = 0.15
    if normalized_query and normalized_query == normalized_entity:
        score += 0.62
    elif normalized_query and normalized_query in normalized_entity:
        score += 0.42
    elif normalized_entity and normalized_entity in normalized_query:
        score += 0.34

    query_tokens = [token for token in normalized_query.split() if len(token) > 2]
    entity_tokens = set(normalized_entity.split())
    overlap = sum(1 for token in query_tokens if token in entity_tokens)
    if query_tokens:
        score += min(0.18, (overlap / len(query_tokens)) * 0.18)

    if normalized_municipality:
        if normalized_municipality == normalized_entity_municipality:
            score += 0.17
        elif normalized_municipality == normalized_postal_place:
            score += 0.14

    if hinted_domain and entity_domain and hinted_domain == entity_domain:
        score += 0.16

    return min(score, 0.99)


def _extract_contact_fields(payload: dict) -> tuple[str, str]:
    website_url = normalize_space(
        payload.get("hjemmeside")
        or payload.get("hjemmesideUrl")
        or payload.get("hjemmeside_url")
    )
    email = normalize_space(
        payload.get("epostadresse")
        or payload.get("epost")
        or payload.get("email")
    ).lower()
    return website_url, email


def _fetch_entity_details(org_number: str) -> dict:
    return _fetch_brreg_json(f"{BRREG_API_BASE}/{quote(org_number)}")


def search_brreg(name: str, *, municipality: str = "", website_hint: str = "", limit: int = 5) -> list[BrregCandidate]:
    query_name = normalize_space(name)
    if not query_name or not settings.BRREG_ENRICHMENT_ENABLED:
        return []

    query = (
        f"navn={quote(query_name)}"
        f"&navnMetodeForSoek=FORTLOEPENDE"
        f"&size={max(1, min(limit, 10))}"
    )
    try:
        payload = _fetch_brreg_json(f"{BRREG_API_BASE}?{query}")
    except Exception:
        return []
    entries = (payload.get("_embedded") or {}).get("enheter") or []
    candidates: list[BrregCandidate] = []

    scored_entries: list[tuple[float, dict]] = []
    for entry in entries:
        org_number = normalize_org_number_candidate(entry.get("organisasjonsnummer"))
        entity_name = normalize_space(entry.get("navn"))
        address = entry.get("forretningsadresse") or {}
        postal_place = normalize_space(address.get("poststed"))
        entity_municipality = normalize_space(address.get("kommune"))
        if not org_number or not entity_name:
            continue
        initial_website_url, _ = _extract_contact_fields(entry)
        initial_score = _score_candidate(
            query_name=query_name,
            entity_name=entity_name,
            municipality=municipality,
            entity_municipality=entity_municipality,
            postal_place=postal_place,
            website_hint=website_hint,
            entity_website=initial_website_url,
        )
        scored_entries.append((initial_score, entry))

    for initial_score, entry in sorted(scored_entries, key=lambda item: item[0], reverse=True)[:2]:
        org_number = normalize_org_number_candidate(entry.get("organisasjonsnummer"))
        entity_name = normalize_space(entry.get("navn"))
        address = entry.get("forretningsadresse") or {}
        postal_place = normalize_space(address.get("poststed"))
        entity_municipality = normalize_space(address.get("kommune"))
        details = entry
        try:
            details = _fetch_entity_details(org_number)
        except Exception:
            details = entry
        details_address = details.get("forretningsadresse") or address
        postal_place = normalize_space(details_address.get("poststed")) or postal_place
        entity_municipality = normalize_space(details_address.get("kommune")) or entity_municipality
        website_url, email = _extract_contact_fields(details)
        score = _score_candidate(
            query_name=query_name,
            entity_name=entity_name,
            municipality=municipality,
            entity_municipality=entity_municipality,
            postal_place=postal_place,
            website_hint=website_hint,
            entity_website=website_url,
        )
        candidates.append(
            BrregCandidate(
                org_number=org_number,
                name=entity_name,
                municipality=entity_municipality,
                postal_place=postal_place,
                website_url=website_url,
                email=email,
                score=score,
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates


def best_brreg_candidate(normalized_payload: dict) -> BrregCandidate | None:
    organization = normalized_payload.get("organization") or {}
    if organization.get("org_number"):
        return None
    candidates = search_brreg(
        organization.get("name", ""),
        municipality=organization.get("municipalities", ""),
        website_hint=organization.get("website_url", "") or organization.get("email", ""),
        limit=5,
    )
    if not candidates:
        return None
    best = candidates[0]
    return best if best.score >= 0.5 else None

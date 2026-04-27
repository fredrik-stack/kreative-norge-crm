from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings

from .normalizers import normalize_name, normalize_space


BRREG_API_BASE = "https://data.brreg.no/enhetsregisteret/api/enheter"
BRREG_USER_AGENT = "KreativeNorgeCRM/1.0 (+https://github.com/fredrik-stack/kreative-norge-crm)"


@dataclass
class BrregCandidate:
    org_number: str
    name: str
    municipality: str
    postal_place: str
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


def search_brreg(name: str, *, municipality: str = "", limit: int = 5) -> list[BrregCandidate]:
    query_name = normalize_space(name)
    if not query_name or not settings.BRREG_ENRICHMENT_ENABLED:
        return []

    query = f"navn={quote(query_name)}&size={max(1, min(limit, 10))}"
    try:
        payload = _fetch_brreg_json(f"{BRREG_API_BASE}?{query}")
    except Exception:
        return []
    entries = (payload.get("_embedded") or {}).get("enheter") or []
    normalized_name = normalize_name(query_name)
    normalized_municipality = normalize_name(municipality)
    candidates: list[BrregCandidate] = []

    for entry in entries:
        org_number = normalize_org_number_candidate(entry.get("organisasjonsnummer"))
        entity_name = normalize_space(entry.get("navn"))
        address = entry.get("forretningsadresse") or {}
        postal_place = normalize_space(address.get("poststed"))
        entity_municipality = normalize_space(address.get("kommune"))
        if not org_number or not entity_name:
            continue
        score = 0.2
        if normalize_name(entity_name) == normalized_name:
            score += 0.5
        elif normalized_name and normalized_name in normalize_name(entity_name):
            score += 0.3
        if normalized_municipality:
            if normalize_name(entity_municipality) == normalized_municipality:
                score += 0.2
            elif normalize_name(postal_place) == normalized_municipality:
                score += 0.15
        candidates.append(
            BrregCandidate(
                org_number=org_number,
                name=entity_name,
                municipality=entity_municipality,
                postal_place=postal_place,
                score=min(score, 0.99),
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
        limit=5,
    )
    return candidates[0] if candidates else None

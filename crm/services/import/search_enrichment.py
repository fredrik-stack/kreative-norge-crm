from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings

from crm.services.open_graph import MAX_HTML_BYTES, _fetch_url

from .normalizers import normalize_name, normalize_space


BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1/web/search"
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SOCIAL_HOSTS = {
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "youtube.com": "youtube",
}
LIKELY_CONTACT_PATHS = (
    "/kontakt",
    "/contact",
)


@dataclass
class SearchSignals:
    website_url: str | None = None
    emails: list[str] | None = None
    socials: dict[str, str] | None = None
    text_snippets: list[str] | None = None


def _sanitize_url(url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def _is_social_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(domain in host for domain in SOCIAL_HOSTS)


def _search(query: str, *, limit: int = 6) -> list[dict[str, str]]:
    if not settings.SEARCH_ENRICHMENT_ENABLED or not settings.BRAVE_SEARCH_API_KEY or not query.strip():
        return []
    params = (
        f"q={quote(query)}"
        f"&count={max(1, min(limit, settings.BRAVE_SEARCH_MAX_RESULTS))}"
        "&country=no"
        "&search_lang=no"
    )
    request = Request(
        f"{BRAVE_SEARCH_API_URL}?{params}",
        headers={
            "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY,
            "Accept": "application/json",
            "User-Agent": "KreativeNorgeCRM/1.0",
        },
    )
    try:
        with urlopen(request, timeout=settings.SEARCH_ENRICHMENT_TIMEOUT) as response:  # noqa: S310 - fixed trusted host
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    results = (payload.get("web") or {}).get("results") or []
    cleaned: list[dict[str, str]] = []
    for item in results:
        url = _sanitize_url(item.get("url"))
        if not url:
            continue
        cleaned.append(
            {
                "url": url,
                "title": normalize_space(item.get("title", "")),
                "snippet": normalize_space(item.get("description", "")),
            }
        )
        if len(cleaned) >= limit:
            break
    return cleaned


def _score_result(query_tokens: set[str], result: dict[str, str]) -> float:
    haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")]))
    if not haystack:
        return 0.0
    hits = sum(1 for token in query_tokens if token and token in haystack)
    if _is_social_url(result.get("url", "")):
        hits += 0.2
    return hits / max(len(query_tokens), 1)


def _pick_best_results(query: str, *, limit: int = 4) -> list[dict[str, str]]:
    results = _search(query, limit=max(limit, 6))
    query_tokens = {token for token in normalize_name(query).split() if len(token) > 2}
    ranked = sorted(results, key=lambda item: _score_result(query_tokens, item), reverse=True)
    return [item for item in ranked if item.get("url")][:limit]


def _extract_page_signals(url: str) -> tuple[list[str], dict[str, str], str]:
    safe_url = _sanitize_url(url)
    if not safe_url:
        return [], {}, ""
    try:
        result = _fetch_url(
            safe_url,
            timeout_seconds=min(settings.SEARCH_ENRICHMENT_TIMEOUT, 5),
            max_bytes=MAX_HTML_BYTES,
            allowed_content_prefixes=("text/html",),
        )
    except Exception:
        return [], {}, ""
    html = result.body.decode("utf-8", errors="ignore")
    emails = list(dict.fromkeys(match.group(0).lower() for match in EMAIL_RE.finditer(html)))
    urls = re.findall(r"https?://[^\s\"'<>]+", html, flags=re.IGNORECASE)
    socials: dict[str, str] = {}
    for candidate in urls:
        normalized = _sanitize_url(candidate.rstrip(").,;"))
        if not normalized:
            continue
        host = (urlparse(normalized).hostname or "").lower()
        for domain, label in SOCIAL_HOSTS.items():
            if domain in host and label not in socials:
                socials[label] = normalized
    text = normalize_space(re.sub(r"<[^>]+>", " ", html))
    return emails, socials, text


def _merge_emails(*email_lists: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for email_list in email_lists:
        for email in email_list:
            lowered = normalize_space(email).lower()
            if not lowered or lowered in seen:
                continue
            seen.add(lowered)
            merged.append(lowered)
    return merged


def _score_social_result(result: dict[str, str], *, target_name: str, organization_name: str = "") -> float:
    haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")]))
    score = 0.0
    normalized_target = normalize_name(target_name)
    normalized_org = normalize_name(organization_name)
    if normalized_target and normalized_target in haystack:
        score += 0.8
    target_tokens = [token for token in normalized_target.split() if len(token) > 2]
    if target_tokens:
        score += min(0.4, sum(1 for token in target_tokens if token in haystack) * 0.1)
    if normalized_org and normalized_org in haystack:
        score += 0.2
    return score


def _pick_primary_website(results: list[dict[str, str]]) -> str | None:
    for result in results:
        url = result.get("url", "")
        if url and not _is_social_url(url):
            return url
    return None


def _extract_search_signals(
    results: list[dict[str, str]],
    *,
    target_name: str,
    organization_name: str = "",
    person_specific: bool = False,
) -> SearchSignals:
    snippets = [normalize_space(result.get("snippet", "")) for result in results if normalize_space(result.get("snippet", ""))]
    website_url = _pick_primary_website(results)
    page_emails: list[str] = []
    socials: dict[str, str] = {}

    for result in results:
        url = result.get("url", "")
        if not url or not _is_social_url(url):
            continue
        host = (urlparse(url).hostname or "").lower()
        score = _score_social_result(result, target_name=target_name, organization_name=organization_name)
        if person_specific and score < 0.8:
            continue
        for domain, label in SOCIAL_HOSTS.items():
            if domain in host and label not in socials:
                socials[label] = url
                break

    if website_url:
        root_emails, root_socials, root_text = _extract_page_signals(website_url)
        page_emails = _merge_emails(page_emails, root_emails)
        snippets.extend([root_text] if root_text else [])
        for key, value in root_socials.items():
            socials.setdefault(key, value)
        for path in LIKELY_CONTACT_PATHS:
            candidate_url = _sanitize_url(f"{website_url.rstrip('/')}{path}")
            if not candidate_url:
                continue
            emails, nested_socials, nested_text = _extract_page_signals(candidate_url)
            page_emails = _merge_emails(page_emails, emails)
            snippets.extend([nested_text] if nested_text else [])
            for key, value in nested_socials.items():
                socials.setdefault(key, value)

    prefix = "person_" if person_specific else "organization_"
    return SearchSignals(
        website_url=website_url,
        emails=page_emails,
        socials={f"{prefix}{key}_url": value for key, value in socials.items()},
        text_snippets=[snippet for snippet in snippets if snippet][:8],
    )


def search_organization_signals(normalized_payload: dict) -> SearchSignals:
    organization = normalized_payload.get("organization") or {}
    name = normalize_space(organization.get("name"))
    municipality = normalize_space(organization.get("municipalities"))
    if not name:
        return SearchSignals(emails=[], socials={}, text_snippets=[])
    query_parts = [f"\"{name}\""]
    if municipality:
        query_parts.append(f"\"{municipality}\"")
    query_parts.append("Norge")
    results = _pick_best_results(" ".join(query_parts), limit=5)
    return _extract_search_signals(results, target_name=name)


def search_person_signals(normalized_payload: dict) -> SearchSignals:
    person = normalized_payload.get("person") or {}
    organization = normalized_payload.get("organization") or {}
    person_name = normalize_space(person.get("full_name"))
    organization_name = normalize_space(organization.get("name"))
    municipality = normalize_space(person.get("municipality") or organization.get("municipalities"))
    if not person_name:
        return SearchSignals(emails=[], socials={}, text_snippets=[])
    query_parts = [f"\"{person_name}\""]
    if organization_name:
        query_parts.append(f"\"{organization_name}\"")
    if municipality:
        query_parts.append(f"\"{municipality}\"")
    query_parts.append("Norge")
    results = _pick_best_results(" ".join(query_parts), limit=5)
    return _extract_search_signals(
        results,
        target_name=person_name,
        organization_name=organization_name,
        person_specific=True,
    )

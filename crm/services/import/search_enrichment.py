from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings

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


@dataclass
class SearchSignals:
    website_url: str | None = None
    emails: list[str] | None = None
    socials: dict[str, str] | None = None
    text_snippets: list[str] | None = None
    org_numbers: list[str] | None = None
    website_candidates: list[dict[str, str]] | None = None


DIRECTORY_HOST_PATTERNS = (
    "proff.no",
    "sceneweb.no",
    "wikipedia.org",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
)
ORG_NUMBER_RE = re.compile(r"\b(\d{3})[\s\-]?(\d{3})[\s\-]?(\d{3})\b")
GENERIC_CONTEXT_TOKENS = {
    "aktør",
    "aktor",
    "arrangør",
    "arrangor",
    "intern",
    "tag",
    "tags",
    "public",
    "api",
}


def _sanitize_url(url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip()
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def _is_social_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(domain in host for domain in SOCIAL_HOSTS)


def _is_directory_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(pattern in host for pattern in DIRECTORY_HOST_PATTERNS)


def _search(query: str, *, limit: int = 6) -> list[dict[str, str]]:
    if not settings.SEARCH_ENRICHMENT_ENABLED or not settings.BRAVE_SEARCH_API_KEY or not query.strip():
        return []
    params = (
        f"q={quote(query)}"
        f"&count={max(1, min(limit, settings.BRAVE_SEARCH_MAX_RESULTS))}"
        "&country=NO"
        "&spellcheck=false"
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


def _score_result(
    query_tokens: set[str],
    result: dict[str, str],
    *,
    exact_phrase: str = "",
    context_terms: list[str] | None = None,
) -> float:
    haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")]))
    if not haystack:
        return 0.0
    hits = sum(1 for token in query_tokens if token and token in haystack)
    if exact_phrase and exact_phrase in haystack:
        hits += 1.4
    for context_term in context_terms or []:
        normalized_context = normalize_name(context_term)
        if normalized_context and normalized_context in haystack:
            hits += 0.35
    if _is_social_url(result.get("url", "")):
        hits += 0.2
    if _is_directory_url(result.get("url", "")):
        hits -= 0.45
    return hits / max(len(query_tokens), 1)


def _merge_ranked_results(
    queries: list[str],
    *,
    target_name: str,
    context_terms: list[str] | None = None,
    limit: int = 4,
) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    normalized_target = normalize_name(target_name)
    query_tokens = {token for token in normalized_target.split() if len(token) > 2}
    context_terms = [normalize_space(term) for term in (context_terms or []) if normalize_space(term)]

    for query in queries:
        for result in _search(query, limit=max(limit, 6)):
            url = result.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(result)

    ranked = sorted(
        merged,
        key=lambda item: _score_result(query_tokens, item, exact_phrase=normalized_target, context_terms=context_terms),
        reverse=True,
    )
    return [item for item in ranked if item.get("url")][:limit]


def _extract_org_numbers(results: list[dict[str, str]]) -> list[str]:
    seen: set[str] = set()
    numbers: list[str] = []
    for result in results:
        haystack = " ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")])
        for match in ORG_NUMBER_RE.finditer(haystack):
            value = "".join(match.groups())
            if value in seen:
                continue
            seen.add(value)
            numbers.append(value)
    return numbers


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


def _pick_primary_website(results: list[dict[str, str]], *, target_name: str, context_terms: list[str] | None = None) -> str | None:
    ranked_candidates: list[tuple[float, str]] = []
    normalized_target = normalize_name(target_name)
    for result in results:
        url = result.get("url", "")
        haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), url]))
        if " nordlys " in f" {haystack} ":
            continue
        if not url or _is_social_url(url) or _is_directory_url(url):
            continue
        host = (urlparse(url).hostname or "").lower()
        host_tokens = set(normalize_name(host.replace("www.", "").replace(".no", "").replace(".com", "")).split())
        haystack_tokens = set(haystack.split())
        overlap = len(host_tokens & haystack_tokens)
        score = float(overlap)
        if normalized_target and normalized_target in haystack:
            score += 2.2
        elif any(token in haystack_tokens for token in normalized_target.split() if len(token) > 2):
            score += 0.7
        for context_term in context_terms or []:
            normalized_context = normalize_name(context_term)
            if normalized_context and normalized_context in haystack:
                score += 0.2
        ranked_candidates.append((score, url))
    if not ranked_candidates:
        return None
    ranked_candidates.sort(key=lambda item: item[0], reverse=True)
    return ranked_candidates[0][1]


def _search_context_terms(normalized_payload: dict, *, person_specific: bool = False) -> list[str]:
    organization = normalized_payload.get("organization") or {}
    person = normalized_payload.get("person") or {}
    context_values = [
        *(organization.get("categories") or []),
        *(organization.get("subcategories") or []),
        *(organization.get("internal_tags") or []),
        *(person.get("categories") or []),
        *(person.get("subcategories") or []),
        *(person.get("internal_tags") or []),
    ]
    if person_specific and person.get("title"):
        context_values.append(person.get("title"))
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in context_values:
        normalized = normalize_space(str(value))
        key = normalize_name(normalized)
        if not normalized or not key or key in GENERIC_CONTEXT_TOKENS or key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
    return cleaned[:4]


def _organization_queries(name: str, municipality: str, context_terms: list[str]) -> list[str]:
    queries = [
        f'"{name}"',
        f'"{name}" Norge',
        f'"{name}" kontakt',
    ]
    if municipality:
        queries.insert(1, f'"{name}" "{municipality}"')
        queries.append(f'"{name}" "{municipality}" kontakt')
    for context_term in context_terms[:2]:
        queries.append(f'"{name}" "{context_term}"')
        queries.append(f'"{name}" "{context_term}" kontakt')
        if municipality:
            queries.append(f'"{name}" "{municipality}" "{context_term}"')
    return queries


def _person_queries(person_name: str, organization_name: str, municipality: str, context_terms: list[str]) -> list[str]:
    queries = [f'"{person_name}"']
    if organization_name:
        queries.append(f'"{person_name}" "{organization_name}"')
    if municipality:
        queries.append(f'"{person_name}" "{municipality}"')
    if organization_name and municipality:
        queries.append(f'"{person_name}" "{organization_name}" "{municipality}"')
    for context_term in context_terms[:2]:
        queries.append(f'"{person_name}" "{context_term}"')
        if organization_name:
            queries.append(f'"{person_name}" "{organization_name}" "{context_term}"')
    return queries


def _extract_search_signals(
    results: list[dict[str, str]],
    *,
    target_name: str,
    organization_name: str = "",
    person_specific: bool = False,
    context_terms: list[str] | None = None,
) -> SearchSignals:
    snippets = [normalize_space(result.get("snippet", "")) for result in results if normalize_space(result.get("snippet", ""))]
    website_url = _pick_primary_website(results, target_name=target_name, context_terms=context_terms)
    normalized_target = normalize_name(target_name)
    if website_url:
        website_haystack = normalize_name(
            " ".join(
                [
                    website_url,
                    *[result.get("title", "") for result in results],
                    *[result.get("snippet", "") for result in results],
                ]
            )
        )
        if normalized_target and normalized_target not in website_haystack:
            website_url = None
    snippet_emails = _merge_emails(
        *[
            [match.group(0).lower() for match in EMAIL_RE.finditer(" ".join([result.get("title", ""), result.get("snippet", "")]))]
            for result in results
        ]
    )
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

    prefix = "person_" if person_specific else "organization_"
    return SearchSignals(
        website_url=website_url,
        emails=snippet_emails,
        socials={f"{prefix}{key}_url": value for key, value in socials.items()},
        text_snippets=[snippet for snippet in snippets if snippet][:8],
        org_numbers=_extract_org_numbers(results),
        website_candidates=[
            {"url": result.get("url", ""), "title": result.get("title", "")}
            for result in results
            if result.get("url") and not _is_social_url(result.get("url", "")) and not _is_directory_url(result.get("url", ""))
        ][:4],
    )


def search_organization_signals(normalized_payload: dict) -> SearchSignals:
    organization = normalized_payload.get("organization") or {}
    name = normalize_space(organization.get("name"))
    municipality = normalize_space(organization.get("municipalities"))
    context_terms = _search_context_terms(normalized_payload)
    if not name:
        return SearchSignals(emails=[], socials={}, text_snippets=[])
    results = _merge_ranked_results(
        _organization_queries(name, municipality, context_terms),
        target_name=name,
        context_terms=context_terms,
        limit=6,
    )
    return _extract_search_signals(results, target_name=name, context_terms=context_terms)


def search_person_signals(normalized_payload: dict) -> SearchSignals:
    person = normalized_payload.get("person") or {}
    organization = normalized_payload.get("organization") or {}
    person_name = normalize_space(person.get("full_name"))
    organization_name = normalize_space(organization.get("name"))
    municipality = normalize_space(person.get("municipality") or organization.get("municipalities"))
    context_terms = _search_context_terms(normalized_payload, person_specific=True)
    if not person_name:
        return SearchSignals(emails=[], socials={}, text_snippets=[])
    results = _merge_ranked_results(
        _person_queries(person_name, organization_name, municipality, context_terms),
        target_name=person_name,
        context_terms=context_terms,
        limit=6,
    )
    return _extract_search_signals(
        results,
        target_name=person_name,
        organization_name=organization_name,
        person_specific=True,
        context_terms=context_terms,
    )

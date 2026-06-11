from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from crm.models import Organization, Person, Tenant

from .normalizers import canonicalize_public_website_url, normalize_name, normalize_space


BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1/web/search"
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SOCIAL_HOSTS = {
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "youtube.com": "youtube",
}

PERSON_ALLOWED_SOCIAL_KEYS = {
    "person_instagram_url",
    "person_tiktok_url",
    "person_facebook_url",
}

PERSON_REJECT_ORGANIZATION_MARKERS = {
    "as",
    "asa",
    "festival",
    "scene",
    "kulturhus",
    "klubb",
    "forening",
    "kommune",
    "company",
    "organization",
    "venue",
}


@dataclass
class SearchSignals:
    website_url: str | None = None
    emails: list[str] | None = None
    socials: dict[str, str] | None = None
    text_snippets: list[str] | None = None
    org_numbers: list[str] | None = None
    website_candidates: list[dict[str, object]] | None = None
    social_candidates: dict[str, list[dict[str, object]]] | None = None
    municipality_candidates: list[dict[str, object]] | None = None
    confirmed_signals: dict[str, object] | None = None


DIRECTORY_HOST_PATTERNS = (
    "gulesider.no",
    "1881.no",
    "180.no",
    "telefonkatalogen.biz",
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


def _compact_text(value: str) -> str:
    return re.sub(r"[^0-9a-zæøå]+", "", normalize_name(value))


def _ascii_handle_text(value: str) -> str:
    folded = (
        normalize_space(value)
        .replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "aa")
        .replace("Æ", "Ae")
        .replace("Ø", "O")
        .replace("Å", "Aa")
    )
    normalized = unicodedata.normalize("NFKD", folded)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^0-9a-z]+", "", ascii_only.casefold())


def _unique_casefold(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_space(value)
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


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


def _host_key(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _is_social_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(domain in host for domain in SOCIAL_HOSTS)


def _is_directory_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(pattern in host for pattern in DIRECTORY_HOST_PATTERNS)


def _search(query: str, *, limit: int = 6, timeout: float | None = None) -> list[dict[str, str]]:
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
        with urlopen(request, timeout=timeout or settings.SEARCH_ENRICHMENT_TIMEOUT) as response:  # noqa: S310 - fixed trusted host
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
    max_queries: int | None = None,
    search_timeout: float | None = None,
) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    normalized_target = normalize_name(target_name)
    query_tokens = {token for token in normalized_target.split() if len(token) > 2}
    context_terms = [normalize_space(term) for term in (context_terms or []) if normalize_space(term)]

    queries_to_run = queries[: max_queries or len(queries)]

    for query in queries_to_run:
        for result in _search(query, limit=max(limit, 6), timeout=search_timeout):
            url = result.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append({**result, "query": query})

    ranked = sorted(
        merged,
        key=lambda item: _score_result(query_tokens, item, exact_phrase=normalized_target, context_terms=context_terms),
        reverse=True,
    )
    finalized: list[dict[str, str]] = []
    for item in ranked:
        if not item.get("url"):
            continue
        scored = dict(item)
        scored["score"] = str(
            _score_result(query_tokens, item, exact_phrase=normalized_target, context_terms=context_terms)
        )
        finalized.append(scored)
        if len(finalized) >= limit:
            break
    return finalized


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


def _person_handle_variants(person_name: str) -> list[str]:
    cleaned = normalize_space(person_name)
    if not cleaned:
        return []
    parts = [part for part in re.split(r"[\s\-]+", cleaned) if part]
    if len(parts) < 2:
        compact = _ascii_handle_text(cleaned)
        return [compact] if compact else []
    first = _ascii_handle_text(parts[0])
    last = _ascii_handle_text(parts[-1])
    first_initial = first[:1]
    variants = [
        f"{first}{last}",
        f"{first}.{last}",
        f"{first}_{last}",
        f"{last}{first}",
        f"{first_initial}{last}" if first_initial else "",
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        normalized = normalize_space(variant)
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped[:6]


def _score_social_result(
    result: dict[str, str],
    *,
    target_name: str,
    organization_name: str = "",
    municipality: str = "",
    context_terms: list[str] | None = None,
    person_specific: bool = False,
) -> float:
    haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")]))
    score = 0.0
    normalized_target = normalize_name(target_name)
    normalized_org = normalize_name(organization_name)
    normalized_municipality = normalize_name(municipality)
    handle_variants = _person_handle_variants(target_name) if person_specific else []
    parsed = urlparse(result.get("url", ""))
    path = parsed.path.strip("/").casefold()
    path_compact = re.sub(r"[^0-9a-z]+", "", path)
    if normalized_target and normalized_target in haystack:
        score += 0.8
    target_tokens = [token for token in normalized_target.split() if len(token) > 2]
    if target_tokens:
        score += min(0.4, sum(1 for token in target_tokens if token in haystack) * 0.1)
    if person_specific and handle_variants and any(re.sub(r"[^0-9a-z]+", "", variant.casefold()) in path_compact for variant in handle_variants):
        score += 0.9
    if normalized_org and normalized_org in haystack:
        score += 0.2
    if normalized_municipality and normalized_municipality in haystack:
        score += 0.15
    for context_term in context_terms or []:
        normalized_context = normalize_name(context_term)
        if normalized_context and normalized_context in haystack:
            score += 0.1
    if person_specific:
        haystack_tokens = set(haystack.split())
        person_token_hits = sum(1 for token in target_tokens if token in haystack_tokens)
        if person_token_hits < 2 and normalized_target not in haystack:
            score -= 0.45
        if any(marker in haystack_tokens for marker in PERSON_REJECT_ORGANIZATION_MARKERS):
            score -= 0.65
    return score


def _pick_primary_website(results: list[dict[str, str]], *, target_name: str, context_terms: list[str] | None = None) -> str | None:
    ranked_candidates: list[tuple[float, str]] = []
    normalized_target = normalize_name(target_name)
    compact_target = _compact_text(target_name)
    for result in results:
        url = result.get("url", "")
        haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), url]))
        if " nordlys " in f" {haystack} ":
            continue
        if not url or _is_social_url(url) or _is_directory_url(url):
            continue
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        compact_host = _compact_text(host.replace("www.", "").replace(".no", "").replace(".com", ""))
        host_tokens = set(normalize_name(host.replace("www.", "").replace(".no", "").replace(".com", "")).split())
        haystack_tokens = set(haystack.split())
        overlap = len(host_tokens & haystack_tokens)
        score = float(overlap)
        if compact_target and compact_host:
            if compact_target == compact_host:
                score += 3.1
            elif compact_target in compact_host or compact_host in compact_target:
                score += 1.6
        if normalized_target and normalized_target in haystack:
            score += 2.2
        elif any(token in haystack_tokens for token in normalized_target.split() if len(token) > 2):
            score += 0.7
        path = parsed.path.strip("/").casefold()
        if not path:
            score += 0.35
        elif path in {"kontakt", "om", "om-oss", "about", "kontakt-oss"}:
            score += 0.15
        elif path.count("/") >= 2:
            score -= 0.2
        for context_term in context_terms or []:
            normalized_context = normalize_name(context_term)
            if normalized_context and normalized_context in haystack:
                score += 0.2
        ranked_candidates.append((score, url))
    if not ranked_candidates:
        return None
    ranked_candidates.sort(key=lambda item: item[0], reverse=True)
    return canonicalize_public_website_url(ranked_candidates[0][1])


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
        f'"{name}" nettside',
        f'"{name}" offisiell',
        f'"{name}" kontakt',
        f'"{name}" instagram',
        f'"{name}" facebook',
    ]
    simplified_name = normalize_space(re.sub(r"[&/,+-]+", " ", name))
    if simplified_name and simplified_name != name:
        queries.extend(
            [
                f'"{simplified_name}"',
                f'"{simplified_name}" nettside',
                f'"{simplified_name}" kontakt',
            ]
        )
    if municipality:
        queries.insert(1, f'"{name}" "{municipality}"')
        queries.append(f'"{name}" "{municipality}" kontakt')
        queries.append(f'"{name}" "{municipality}" nettside')
    for context_term in context_terms[:2]:
        queries.append(f'"{name}" "{context_term}"')
        queries.append(f'"{name}" "{context_term}" kontakt')
        if municipality:
            queries.append(f'"{name}" "{municipality}" "{context_term}"')
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized_query = normalize_space(query)
        if not normalized_query or normalized_query in seen:
            continue
        seen.add(normalized_query)
        deduped.append(normalized_query)
    return deduped


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


def _organization_stage2_queries(name: str, municipality: str, context_terms: list[str]) -> list[str]:
    queries = [
        f"{name} hjemmeside",
        f"{name} offisiell nettside",
        f"{name} kontakt oss",
    ]
    if municipality:
        queries.extend(
            [
                f"{name} {municipality} hjemmeside",
                f"{name} {municipality} offisiell nettside",
            ]
        )
    for context_term in context_terms[:2]:
        queries.append(f"{name} {context_term} hjemmeside")
    return _dedupe_queries(queries)


def _person_stage2_queries(person_name: str, organization_name: str, municipality: str, context_terms: list[str]) -> list[str]:
    queries = [
        f'{person_name} kontakt',
        f'{person_name} bio',
    ]
    if organization_name:
        queries.extend(
            [
                f'{person_name} {organization_name} kontakt',
                f'{person_name} {organization_name} bio',
            ]
        )
    if municipality:
        queries.append(f'{person_name} {municipality} kontakt')
    for context_term in context_terms[:2]:
        queries.append(f'{person_name} {context_term}')
    return _dedupe_queries(queries)


def _dedupe_queries(queries: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized_query = normalize_space(query)
        if not normalized_query or normalized_query in seen:
            continue
        seen.add(normalized_query)
        deduped.append(normalized_query)
    return deduped


def _confirmed_organization_signals(tenant: Tenant | None, normalized_payload: dict) -> dict[str, object]:
    if tenant is None:
        return {"websites": [], "municipalities": [], "socials": {}}
    organization = normalized_payload.get("organization") or {}
    name = normalize_space(organization.get("name"))
    if not name:
        return {"websites": [], "municipalities": [], "socials": {}}
    queryset = Organization.objects.filter(tenant=tenant, name__iexact=name)[:5]
    websites = _unique_casefold(
        [
            canonicalize_public_website_url(item.website_url)
            for item in queryset
            if item.website_url
        ]
    )
    municipalities = _unique_casefold(
        [normalize_space(item.municipalities) for item in queryset if normalize_space(item.municipalities)]
    )
    socials: dict[str, str] = {}
    for field_name, payload_key in (
        ("instagram_url", "organization_instagram_url"),
        ("tiktok_url", "organization_tiktok_url"),
        ("linkedin_url", "organization_linkedin_url"),
        ("facebook_url", "organization_facebook_url"),
        ("youtube_url", "organization_youtube_url"),
    ):
        for item in queryset:
            value = canonicalize_public_website_url(getattr(item, field_name, "") or "")
            if value:
                socials.setdefault(payload_key, value)
    return {
        "websites": websites,
        "municipalities": municipalities,
        "socials": socials,
    }


def _confirmed_person_signals(tenant: Tenant | None, normalized_payload: dict) -> dict[str, object]:
    if tenant is None:
        return {"websites": [], "municipalities": [], "socials": {}}
    person = normalized_payload.get("person") or {}
    name = normalize_space(person.get("full_name"))
    if not name:
        return {"websites": [], "municipalities": [], "socials": {}}
    queryset = Person.objects.filter(tenant=tenant, full_name__iexact=name)[:5]
    websites = _unique_casefold(
        [
            canonicalize_public_website_url(item.website_url)
            for item in queryset
            if item.website_url
        ]
    )
    municipalities = _unique_casefold(
        [normalize_space(item.municipality) for item in queryset if normalize_space(item.municipality)]
    )
    socials: dict[str, str] = {}
    for field_name, payload_key in (
        ("instagram_url", "person_instagram_url"),
        ("tiktok_url", "person_tiktok_url"),
        ("facebook_url", "person_facebook_url"),
    ):
        for item in queryset:
            value = canonicalize_public_website_url(getattr(item, field_name, "") or "")
            if value:
                socials.setdefault(payload_key, value)
    return {
        "websites": websites,
        "municipalities": municipalities,
        "socials": socials,
    }


def _rank_website_candidates(
    results: list[dict[str, str]],
    *,
    target_name: str,
    context_terms: list[str] | None = None,
    confirmed_websites: list[str] | None = None,
) -> list[dict[str, object]]:
    confirmed_websites = confirmed_websites or []
    confirmed_hosts = {_host_key(url) for url in confirmed_websites if url}
    ranked_candidates: list[dict[str, object]] = []
    seen_hosts: set[str] = set()
    normalized_target = normalize_name(target_name)
    compact_target = _compact_text(target_name)
    for result in results:
        url = result.get("url", "")
        if not url or _is_social_url(url) or _is_directory_url(url):
            continue
        parsed = urlparse(url)
        host_key = _host_key(url)
        if not host_key or host_key in seen_hosts:
            continue
        host = (parsed.hostname or "").lower()
        compact_host = _compact_text(host_key.replace(".no", "").replace(".com", ""))
        haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), url]))
        haystack_tokens = set(haystack.split())
        score = float(result.get("score") or 0)
        if compact_target and compact_host:
            if compact_target == compact_host:
                score += 2.6
            elif compact_target in compact_host or compact_host in compact_target:
                score += 1.2
        if normalized_target and normalized_target in haystack:
            score += 1.4
        path = parsed.path.strip("/").casefold()
        if not path:
            score += 0.3
        elif path in {"kontakt", "om", "om-oss", "about", "kontakt-oss"}:
            score += 0.2
        elif path.count("/") >= 2:
            score -= 0.2
        for context_term in context_terms or []:
            normalized_context = normalize_name(context_term)
            if normalized_context and normalized_context in haystack_tokens:
                score += 0.15
        if host_key in confirmed_hosts:
            score += 1.8
        ranked_candidates.append(
            {
                "url": canonicalize_public_website_url(url),
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "score": round(score, 3),
                "source": "confirmed_prior" if host_key in confirmed_hosts else "web_search",
                "host": host_key,
                "query": result.get("query", ""),
            }
        )
        seen_hosts.add(host_key)
    ranked_candidates.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return ranked_candidates[:6]


def _social_queries(target_name: str, municipality: str, context_terms: list[str], platform: str) -> list[str]:
    queries = [
        f'"{target_name}" {platform}',
        f'"{target_name}" site:{platform}.com',
    ]
    if municipality:
        queries.append(f'"{target_name}" "{municipality}" {platform}')
    for context_term in context_terms[:1]:
        queries.append(f'"{target_name}" "{context_term}" {platform}')
    return _dedupe_queries(queries)


def _person_social_queries(
    person_name: str,
    municipality: str,
    context_terms: list[str],
    platform: str,
) -> list[str]:
    platform_domain = "facebook.com" if platform == "facebook" else f"{platform}.com"
    queries: list[str] = []
    for handle in _person_handle_variants(person_name)[:2]:
        queries.append(f'site:{platform_domain} "{handle}"')
        if municipality:
            queries.append(f'site:{platform_domain} "{handle}" "{municipality}"')
    queries.append(f'"{person_name}" site:{platform_domain}')
    if municipality:
        queries.append(f'"{person_name}" "{municipality}" {platform}')
    for context_term in context_terms[:1]:
        queries.append(f'"{person_name}" "{context_term}" {platform}')
    return _dedupe_queries(queries)


def _collect_social_candidates(
    results: list[dict[str, str]],
    *,
    target_name: str,
    organization_name: str = "",
    person_specific: bool = False,
    municipality: str = "",
    context_terms: list[str] | None = None,
    confirmed_socials: dict[str, str] | None = None,
) -> dict[str, list[dict[str, object]]]:
    confirmed_socials = confirmed_socials or {}
    collected: dict[str, list[dict[str, object]]] = {}
    for result in results:
        url = result.get("url", "")
        if not url or not _is_social_url(url):
            continue
        host = (urlparse(url).hostname or "").lower()
        payload_key = None
        for domain, label in SOCIAL_HOSTS.items():
            if domain in host:
                prefix = "person_" if person_specific else "organization_"
                payload_key = f"{prefix}{label}_url"
                break
        if not payload_key:
            continue
        if person_specific and payload_key not in PERSON_ALLOWED_SOCIAL_KEYS:
            continue
        score = _score_social_result(
            result,
            target_name=target_name,
            organization_name=organization_name,
            municipality=municipality,
            context_terms=context_terms,
            person_specific=person_specific,
        )
        if canonicalize_public_website_url(url) == confirmed_socials.get(payload_key):
            score += 1.4
        if person_specific and score < 0.75:
            continue
        collected.setdefault(payload_key, []).append(
            {
                "url": canonicalize_public_website_url(url),
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "score": round(score, 3),
                "source": "confirmed_prior" if canonicalize_public_website_url(url) == confirmed_socials.get(payload_key) else "web_search",
                "query": result.get("query", ""),
            }
        )
    for payload_key, candidates in collected.items():
        deduped: list[dict[str, object]] = []
        seen_urls: set[str] = set()
        for candidate in sorted(candidates, key=lambda item: float(item.get("score") or 0), reverse=True):
            url = str(candidate.get("url") or "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(candidate)
        collected[payload_key] = deduped[:4]
    return collected


def _known_municipality_values() -> list[str]:
    known_values = list(Organization.objects.exclude(municipalities="").values_list("municipalities", flat=True)) + list(
        Person.objects.exclude(municipality="").values_list("municipality", flat=True)
    )
    split_values: list[str] = []
    for value in [normalize_space(item) for item in known_values if normalize_space(item)]:
        split_values.extend(re.split(r"[;,/]", value))
    return _unique_casefold([normalize_space(item) for item in split_values if normalize_space(item)])


def _extract_municipality_candidates(
    results: list[dict[str, str]],
    *,
    confirmed_values: list[str] | None = None,
) -> list[dict[str, object]]:
    confirmed_values = confirmed_values or []
    candidates: list[dict[str, object]] = []
    seen: set[str] = set()
    for value in confirmed_values:
        normalized_value = normalize_name(value)
        if not normalized_value or normalized_value in seen:
            continue
        seen.add(normalized_value)
        candidates.append({"value": value, "score": 0.95, "source": "confirmed_prior"})
    known_values = _known_municipality_values()
    for result in results:
        haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", "")]))
        for value in known_values:
            normalized_value = normalize_name(value)
            if not normalized_value or normalized_value in seen:
                continue
            if normalized_value in haystack:
                seen.add(normalized_value)
                candidates.append({"value": value, "score": 0.67, "source": "web_search"})
    candidates.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return candidates[:5]


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
                if person_specific and f"{prefix}{label}_url" not in PERSON_ALLOWED_SOCIAL_KEYS:
                    continue
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


def search_organization_signals(normalized_payload: dict, tenant: Tenant | None = None) -> SearchSignals:
    organization = normalized_payload.get("organization") or {}
    name = normalize_space(organization.get("name"))
    municipality = normalize_space(organization.get("municipalities"))
    context_terms = _search_context_terms(normalized_payload)
    if not name:
        return SearchSignals(emails=[], socials={}, text_snippets=[], website_candidates=[], social_candidates={}, municipality_candidates=[], confirmed_signals={})
    confirmed_signals = _confirmed_organization_signals(tenant, normalized_payload)
    results = _merge_ranked_results(
        _organization_queries(name, municipality, context_terms),
        target_name=name,
        context_terms=context_terms,
        limit=6,
    )
    website_candidates = _rank_website_candidates(
        results,
        target_name=name,
        context_terms=context_terms,
        confirmed_websites=list(confirmed_signals.get("websites", [])),
    )
    if not website_candidates or float(website_candidates[0].get("score") or 0) < 2.1:
        stage2_results = _merge_ranked_results(
            _organization_stage2_queries(name, municipality, context_terms),
            target_name=name,
            context_terms=context_terms,
            limit=6,
        )
        results = [*results, *[item for item in stage2_results if item.get("url") and item.get("url") not in {result.get("url") for result in results}]]
        website_candidates = _rank_website_candidates(
            results,
            target_name=name,
            context_terms=context_terms,
            confirmed_websites=list(confirmed_signals.get("websites", [])),
        )
    social_results = []
    for platform in ("instagram", "facebook", "youtube", "tiktok", "linkedin"):
        social_results.extend(
            _merge_ranked_results(
                _social_queries(name, municipality, context_terms, platform),
                target_name=name,
                context_terms=context_terms,
                limit=3,
            )
        )
    merged_social_results = [
        item
        for item in social_results
        if item.get("url") and item.get("url") not in {result.get("url") for result in results}
    ]
    social_candidates = _collect_social_candidates(
        [*results, *merged_social_results],
        target_name=name,
        confirmed_socials=dict(confirmed_signals.get("socials", {})),
    )
    socials = {
        payload_key: str(candidates[0]["url"])
        for payload_key, candidates in social_candidates.items()
        if candidates
    }
    for payload_key, value in dict(confirmed_signals.get("socials", {})).items():
        socials.setdefault(payload_key, value)
    municipality_candidates = _extract_municipality_candidates(
        results,
        confirmed_values=list(confirmed_signals.get("municipalities", [])),
    )
    snippets = [normalize_space(result.get("snippet", "")) for result in results if normalize_space(result.get("snippet", ""))]
    snippet_emails = _merge_emails(
        *[
            [match.group(0).lower() for match in EMAIL_RE.finditer(" ".join([result.get("title", ""), result.get("snippet", "")]))]
            for result in results
        ]
    )
    website_url = None
    if website_candidates:
        website_url = str(website_candidates[0]["url"])
    elif confirmed_signals.get("websites"):
        website_url = str(list(confirmed_signals["websites"])[0])
    return SearchSignals(
        website_url=website_url,
        emails=snippet_emails,
        socials=socials,
        text_snippets=[snippet for snippet in snippets if snippet][:8],
        org_numbers=_extract_org_numbers(results),
        website_candidates=website_candidates,
        social_candidates=social_candidates,
        municipality_candidates=municipality_candidates,
        confirmed_signals=confirmed_signals,
    )


def search_person_signals(normalized_payload: dict, tenant: Tenant | None = None) -> SearchSignals:
    person = normalized_payload.get("person") or {}
    organization = normalized_payload.get("organization") or {}
    person_name = normalize_space(person.get("full_name"))
    organization_name = normalize_space(organization.get("name"))
    municipality = normalize_space(person.get("municipality") or organization.get("municipalities"))
    context_terms = _search_context_terms(normalized_payload, person_specific=True)
    if not person_name:
        return SearchSignals(emails=[], socials={}, text_snippets=[], website_candidates=[], social_candidates={}, municipality_candidates=[], confirmed_signals={})
    person_search_timeout = min(float(settings.SEARCH_ENRICHMENT_TIMEOUT or 5), 2.0)
    person_social_timeout = min(float(settings.SEARCH_ENRICHMENT_TIMEOUT or 5), 1.5)
    confirmed_signals = _confirmed_person_signals(tenant, normalized_payload)
    results = _merge_ranked_results(
        _person_queries(person_name, organization_name, municipality, context_terms),
        target_name=person_name,
        context_terms=context_terms,
        limit=6,
        max_queries=2,
        search_timeout=person_search_timeout,
    )
    website_candidates = _rank_website_candidates(
        results,
        target_name=person_name,
        context_terms=context_terms,
        confirmed_websites=list(confirmed_signals.get("websites", [])),
    )
    if (not website_candidates or float(website_candidates[0].get("score") or 0) < 1.9) and len(results) < 3:
        stage2_results = _merge_ranked_results(
            _person_stage2_queries(person_name, organization_name, municipality, context_terms),
            target_name=person_name,
            context_terms=context_terms,
            limit=6,
            max_queries=1,
            search_timeout=person_search_timeout,
        )
        results = [*results, *[item for item in stage2_results if item.get("url") and item.get("url") not in {result.get("url") for result in results}]]
        website_candidates = _rank_website_candidates(
            results,
            target_name=person_name,
            context_terms=context_terms,
            confirmed_websites=list(confirmed_signals.get("websites", [])),
        )
    social_results = []
    for platform in ("instagram", "facebook", "tiktok"):
        social_results.extend(
            _merge_ranked_results(
                _person_social_queries(person_name, municipality, context_terms, platform),
                target_name=person_name,
                context_terms=context_terms,
                limit=2,
                max_queries=2,
                search_timeout=person_social_timeout,
            )
        )
    merged_social_results = [
        item
        for item in social_results
        if item.get("url") and item.get("url") not in {result.get("url") for result in results}
    ]
    social_candidates = _collect_social_candidates(
        [*results, *merged_social_results],
        target_name=person_name,
        organization_name=organization_name,
        person_specific=True,
        municipality=municipality,
        context_terms=context_terms,
        confirmed_socials=dict(confirmed_signals.get("socials", {})),
    )
    socials = {
        payload_key: str(candidates[0]["url"])
        for payload_key, candidates in social_candidates.items()
        if candidates
    }
    for payload_key, value in dict(confirmed_signals.get("socials", {})).items():
        socials.setdefault(payload_key, value)
    municipality_candidates = _extract_municipality_candidates(
        results,
        confirmed_values=list(confirmed_signals.get("municipalities", [])),
    )
    snippets = [normalize_space(result.get("snippet", "")) for result in results if normalize_space(result.get("snippet", ""))]
    snippet_emails = _merge_emails(
        *[
            [match.group(0).lower() for match in EMAIL_RE.finditer(" ".join([result.get("title", ""), result.get("snippet", "")]))]
            for result in results
        ]
    )
    website_url = None
    if website_candidates:
        website_url = str(website_candidates[0]["url"])
    elif confirmed_signals.get("websites"):
        website_url = str(list(confirmed_signals["websites"])[0])
    return SearchSignals(
        website_url=website_url,
        emails=snippet_emails,
        socials=socials,
        text_snippets=[snippet for snippet in snippets if snippet][:8],
        website_candidates=website_candidates,
        social_candidates=social_candidates,
        municipality_candidates=municipality_candidates,
        confirmed_signals=confirmed_signals,
    )

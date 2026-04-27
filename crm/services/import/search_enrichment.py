from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote, urlparse

from django.conf import settings

from crm.services.open_graph import MAX_HTML_BYTES, _fetch_url

from .normalizers import normalize_name, normalize_space


SEARCH_BASE_URL = "https://html.duckduckgo.com/html/?q="


@dataclass
class SearchSignals:
    website_url: str | None = None
    emails: list[str] | None = None
    socials: dict[str, str] | None = None
    text_snippets: list[str] | None = None


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._collect_link_text = False
        self._current_link_text = ""
        self._current_snippet = ""
        self._inside_snippet = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        attrs_dict = {k.lower(): v for k, v in attrs if k and v}
        if tag.lower() == "a" and attrs_dict.get("class", "") == "result__a":
            self._current_href = attrs_dict.get("href")
            self._collect_link_text = True
            self._current_link_text = ""
            self._current_snippet = ""
        elif tag.lower() == "a" and "result__snippet" in attrs_dict.get("class", ""):
            self._inside_snippet = True
        elif tag.lower() == "div" and "result__snippet" in attrs_dict.get("class", ""):
            self._inside_snippet = True

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        lowered = tag.lower()
        if lowered == "a" and self._collect_link_text and self._current_href:
            self.results.append(
                {
                    "url": self._current_href,
                    "title": normalize_space(unescape(self._current_link_text)),
                    "snippet": normalize_space(unescape(self._current_snippet)),
                }
            )
            self._current_href = None
            self._collect_link_text = False
            self._current_link_text = ""
            self._current_snippet = ""
        if lowered in {"a", "div"}:
            self._inside_snippet = False

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._collect_link_text:
            self._current_link_text += data
        if self._inside_snippet:
            self._current_snippet += data


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SOCIAL_HOSTS = {
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "youtube.com": "youtube",
}


def _search(query: str, *, limit: int = 5) -> list[dict[str, str]]:
    if not settings.SEARCH_ENRICHMENT_ENABLED or not query.strip():
        return []
    try:
        result = _fetch_url(
            f"{SEARCH_BASE_URL}{quote(query)}",
            timeout_seconds=min(settings.SEARCH_ENRICHMENT_TIMEOUT, 5),
            max_bytes=MAX_HTML_BYTES,
            allowed_content_prefixes=("text/html",),
        )
    except Exception:
        return []
    parser = _DuckDuckGoParser()
    parser.feed(result.body.decode("utf-8", errors="ignore"))
    return [item for item in parser.results if item.get("url")][:limit]


def _is_social_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(domain in host for domain in SOCIAL_HOSTS)


def _score_result(query_tokens: set[str], result: dict[str, str]) -> float:
    haystack = normalize_name(" ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")]))
    if not haystack:
        return 0.0
    hits = sum(1 for token in query_tokens if token and token in haystack)
    if _is_social_url(result.get("url", "")):
        hits += 0.2
    return hits / max(len(query_tokens), 1)


def _pick_best_results(query: str, *, limit: int = 3) -> list[dict[str, str]]:
    results = _search(query, limit=8)
    query_tokens = {token for token in normalize_name(query).split() if len(token) > 2}
    ranked = sorted(results, key=lambda item: _score_result(query_tokens, item), reverse=True)
    return [item for item in ranked if item.get("url")][:limit]


def _extract_search_signals(results: list[dict[str, str]], *, person_name: str = "") -> SearchSignals:
    emails: list[str] = []
    socials: dict[str, str] = {}
    snippets: list[str] = []
    best_website: str | None = None
    normalized_person = normalize_name(person_name)

    for result in results:
        url = result.get("url", "")
        snippet = normalize_space(result.get("snippet"))
        if snippet:
            snippets.append(snippet)
        if not best_website and url and not _is_social_url(url):
            best_website = url
        if url:
            host = (urlparse(url).hostname or "").lower()
            for domain, label in SOCIAL_HOSTS.items():
                if domain in host and label not in socials:
                    if normalized_person:
                        target = normalize_name(" ".join([result.get("title", ""), snippet, url]))
                        if normalized_person not in target:
                            continue
                    socials[label] = url
        if snippet:
            for match in EMAIL_RE.finditer(snippet):
                candidate = match.group(0).lower()
                if candidate not in emails:
                    emails.append(candidate)

    return SearchSignals(
        website_url=best_website,
        emails=emails,
        socials={
            f"organization_{key}_url" if key in {"instagram", "tiktok", "linkedin", "facebook", "youtube"} else key: value
            for key, value in socials.items()
        },
        text_snippets=snippets,
    )


def search_organization_signals(normalized_payload: dict) -> SearchSignals:
    organization = normalized_payload.get("organization") or {}
    name = normalize_space(organization.get("name"))
    municipality = normalize_space(organization.get("municipalities"))
    if not name:
        return SearchSignals(emails=[], socials={}, text_snippets=[])
    query = " ".join(part for part in [name, municipality, "Norge"] if part)
    return _extract_search_signals(_pick_best_results(query))


def search_person_signals(normalized_payload: dict) -> SearchSignals:
    person = normalized_payload.get("person") or {}
    organization = normalized_payload.get("organization") or {}
    person_name = normalize_space(person.get("full_name"))
    if not person_name:
        return SearchSignals(emails=[], socials={}, text_snippets=[])
    query = " ".join(
        part
        for part in [
            person_name,
            normalize_space(organization.get("name")),
            normalize_space(person.get("municipality")),
            "Norge",
        ]
        if part
    )
    raw = _extract_search_signals(_pick_best_results(query), person_name=person_name)
    person_socials = {
        key.replace("organization_", "person_"): value
        for key, value in (raw.socials or {}).items()
    }
    return SearchSignals(
        website_url=raw.website_url,
        emails=raw.emails or [],
        socials=person_socials,
        text_snippets=raw.text_snippets or [],
    )

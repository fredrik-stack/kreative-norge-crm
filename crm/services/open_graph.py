from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from html.parser import HTMLParser
import ipaddress
import socket
import re
from urllib.parse import urljoin, urlparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.utils import timezone

from crm.models import Organization


USER_AGENT = (
    "Mozilla/5.0 (compatible; KreativeNorgeCRM/1.0; +https://github.com/fredrik-stack/kreative-norge-crm)"
)
MAX_HTML_BYTES = 1_000_000
MAX_REDIRECTS = 3
PRIVATE_HOSTNAMES = {"localhost", "metadata.google.internal"}


@dataclass
class OpenGraphData:
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    image_candidates: list["ImageCandidate"] = field(default_factory=list)


@dataclass
class ImageCandidate:
    url: str
    source: str
    width: int | None = None
    height: int | None = None
    alt: str | None = None
    css_hint: str | None = None


@dataclass
class FetchResult:
    final_url: str
    headers: object
    body: bytes


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.image_candidates: list[ImageCandidate] = []
        self._title_collect = False
        self._title_value = ""

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        attrs_dict = {k.lower(): v for k, v in attrs if k and v}
        if tag.lower() == "meta":
            prop = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content")
            if prop and content:
                self.meta[prop.lower()] = content.strip()
                lowered_prop = prop.lower()
                if lowered_prop in {"og:image", "twitter:image"}:
                    self.image_candidates.append(
                        ImageCandidate(
                            url=content.strip(),
                            source=lowered_prop,
                        )
                    )
        elif tag.lower() == "img":
            src = attrs_dict.get("src")
            if src:
                self.image_candidates.append(
                    ImageCandidate(
                        url=src.strip(),
                        source="img",
                        width=_parse_int(attrs_dict.get("width")),
                        height=_parse_int(attrs_dict.get("height")),
                        alt=attrs_dict.get("alt"),
                        css_hint=" ".join(
                            part for part in [attrs_dict.get("class"), attrs_dict.get("id")] if part
                        )
                        or None,
                    )
                )
        elif tag.lower() == "title":
            self._title_collect = True

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._title_collect:
            self._title_value += data

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag.lower() == "title":
            self._title_collect = False

    @property
    def title(self) -> str | None:
        value = self._title_value.strip()
        return value or None


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def fallback_preview_image(link: str | None) -> str | None:
    if not link:
        return None
    parsed = urlparse(link)
    if not parsed.netloc or not _is_public_http_url(link):
        return None
    return f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=256"


def is_fallback_preview_image(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.netloc in {"www.google.com", "google.com"} and parsed.path.startswith("/s2/favicons")


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_image_candidate(base_url: str, candidate: ImageCandidate) -> ImageCandidate | None:
    if not candidate.url or candidate.url.startswith("data:"):
        return None
    normalized_url = urljoin(base_url, candidate.url)
    if not _is_public_http_url(normalized_url):
        return None
    return ImageCandidate(
        url=normalized_url,
        source=candidate.source,
        width=candidate.width,
        height=candidate.height,
        alt=candidate.alt,
        css_hint=candidate.css_hint,
    )


def _candidate_score(candidate: ImageCandidate) -> int:
    score = 0
    lower_url = candidate.url.lower()
    hint_text = " ".join(filter(None, [candidate.alt, candidate.css_hint])).lower()

    if candidate.source == "og:image":
        score += 220
    elif candidate.source == "twitter:image":
        score += 180
    else:
        score += 80

    if any(bad in lower_url for bad in ["favicon", "icon", "sprite", "avatar", "logo", "emoji"]):
        score -= 260
    if any(bad in hint_text for bad in ["favicon", "icon", "sprite", "avatar", "logo"]):
        score -= 220

    if re.search(r"\.(jpg|jpeg|png|webp)(?:$|\?)", lower_url):
        score += 24

    if candidate.width and candidate.height:
        if candidate.width < 120 or candidate.height < 120:
            score -= 240
        else:
            score += min(candidate.width, 1200) // 20
            ratio = candidate.width / max(candidate.height, 1)
            if 0.7 <= ratio <= 1.7:
                score += 50
            elif 0.45 <= ratio <= 2.4:
                score += 20
            else:
                score -= 25
    elif candidate.source == "img":
        score -= 15

    if "/images/" in lower_url or "/uploads/" in lower_url or "/media/" in lower_url:
        score += 18

    return score


def _is_ip_public(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_global


def _resolve_host_addresses(hostname: str) -> list[str]:
    infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    addresses = []
    for info in infos:
        address = info[4][0]
        if address not in addresses:
            addresses.append(address)
    return addresses


def _is_public_hostname(hostname: str) -> bool:
    if not hostname:
        return False
    lowered = hostname.strip().lower().rstrip(".")
    if lowered in PRIVATE_HOSTNAMES or lowered.endswith(".local"):
        return False
    if _is_ip_public(lowered):
        return True
    try:
        addresses = _resolve_host_addresses(lowered)
    except OSError:
        return False
    if not addresses:
        return False
    return all(_is_ip_public(address) for address in addresses)


def _is_public_http_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    return _is_public_hostname(parsed.hostname or "")


def _fetch_url(
    url: str,
    *,
    timeout_seconds: int,
    max_bytes: int | None,
    allowed_content_prefixes: tuple[str, ...],
) -> FetchResult:
    if not _is_public_http_url(url):
        raise ValueError("Refusing to fetch non-public URL.")

    opener = build_opener(NoRedirectHandler())
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        request = Request(current_url, headers={"User-Agent": USER_AGENT})
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                content_type = (response.headers.get("Content-Type") or "").lower()
                if allowed_content_prefixes and not any(
                    content_type.startswith(prefix) for prefix in allowed_content_prefixes
                ):
                    raise ValueError("Unexpected content type.")
                if max_bytes is None:
                    body = b""
                else:
                    body = response.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        raise ValueError("Response too large.")
                return FetchResult(final_url=response.geturl(), headers=response.headers, body=body)
        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                location = exc.headers.get("Location")
                if not location:
                    raise ValueError("Redirect without location.")
                current_url = urljoin(current_url, location)
                if not _is_public_http_url(current_url):
                    raise ValueError("Redirect target is not public.")
                continue
            raise
    raise ValueError("Too many redirects.")


def _image_candidate_looks_usable(url: str, timeout_seconds: int = 4) -> bool:
    try:
        _fetch_url(
            url,
            timeout_seconds=timeout_seconds,
            max_bytes=None,
            allowed_content_prefixes=("image/",),
        )
        return True
    except Exception:
        return False


def choose_best_thumbnail(base_url: str, candidates: list[ImageCandidate]) -> str | None:
    normalized: list[ImageCandidate] = []
    seen: set[str] = set()

    for candidate in candidates:
        normalized_candidate = _normalize_image_candidate(base_url, candidate)
        if not normalized_candidate:
            continue
        if is_fallback_preview_image(normalized_candidate.url):
            continue
        if normalized_candidate.url in seen:
            continue
        seen.add(normalized_candidate.url)
        normalized.append(normalized_candidate)

    if not normalized:
        return None

    ranked = sorted(normalized, key=_candidate_score, reverse=True)
    for candidate in ranked:
        if _candidate_score(candidate) < 40:
            break
        if _image_candidate_looks_usable(candidate.url):
            return candidate.url
    return None


def fetch_open_graph(url: str, timeout_seconds: int = 4) -> OpenGraphData:
    result = _fetch_url(
        url,
        timeout_seconds=timeout_seconds,
        max_bytes=MAX_HTML_BYTES,
        allowed_content_prefixes=("text/html",),
    )
    charset = result.headers.get_content_charset() or "utf-8"
    html = result.body.decode(charset, errors="replace")

    parser = MetaParser()
    parser.feed(html)

    raw_image = parser.meta.get("og:image") or parser.meta.get("twitter:image")
    image_url = urljoin(result.final_url, raw_image) if raw_image else None
    if image_url and not _is_public_http_url(image_url):
        image_url = None

    return OpenGraphData(
        title=parser.meta.get("og:title") or parser.title,
        description=parser.meta.get("og:description"),
        image_url=image_url,
        image_candidates=parser.image_candidates,
    )


def refresh_organization_open_graph(
    organization: Organization,
    *,
    force: bool = False,
    min_refresh_interval: timedelta = timedelta(hours=12),
) -> None:
    primary = organization.get_primary_link()
    now = timezone.now()

    if not primary:
        organization.og_title = None
        organization.og_description = None
        organization.og_image_url = None
        organization.auto_thumbnail_url = None
        organization.og_last_fetched_at = now
        organization.save(
            update_fields=[
                "og_title",
                "og_description",
                "og_image_url",
                "auto_thumbnail_url",
                "og_last_fetched_at",
            ]
        )
        return

    if (
        not force
        and organization.og_last_fetched_at
        and now - organization.og_last_fetched_at < min_refresh_interval
    ):
        return

    try:
        og = fetch_open_graph(primary)
        organization.og_title = og.title
        organization.og_description = og.description
        organization.og_image_url = og.image_url
        organization.auto_thumbnail_url = choose_best_thumbnail(primary, og.image_candidates)
    except Exception:
        organization.og_image_url = None
        organization.auto_thumbnail_url = None
        if not organization.og_title:
            organization.og_title = organization.name
    organization.og_last_fetched_at = now
    organization.save(
        update_fields=[
            "og_title",
            "og_description",
            "og_image_url",
            "auto_thumbnail_url",
            "og_last_fetched_at",
        ]
    )

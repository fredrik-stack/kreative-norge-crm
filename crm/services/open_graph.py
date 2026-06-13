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
SOCIAL_PROFILE_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
}
SOCIAL_STATIC_HOST_PARTS = (
    "static.xx.fbcdn.net",
    "static.cdninstagram.com",
    "connect.facebook.net",
    "static.tiktokcdn.com",
)
UTILITY_IMAGE_TERMS = (
    "favicon",
    "sprite",
    "emoji",
    "placeholder",
    "loader",
    "blank",
    "transparent",
    "pixel",
    "avatar-default",
)
PARTNER_IMAGE_TERMS = (
    "sponsor",
    "sponsorer",
    "partner",
    "partners",
    "samarbeidspartner",
    "stottespiller",
    "støttespiller",
    "supporter",
    "powered",
    "footer",
    "vipps",
    "sparebank",
    "kulturradet",
    "kulturrådet",
    "nordland-fylkeskommune",
    "fylkeskommune",
)
PROMISING_IMAGE_TERMS = (
    "hero",
    "cover",
    "featured",
    "main",
    "poster",
    "artist",
    "scene",
    "festival",
    "concert",
    "konsert",
    "venue",
    "gallery",
    "uploads",
    "media",
    "image",
)


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
            image_urls = _candidate_urls_from_attrs(
                attrs_dict,
                [
                    "src",
                    "data-src",
                    "data-original",
                    "data-lazy-src",
                    "data-image",
                    "data-bg",
                    "srcset",
                    "data-srcset",
                ],
            )
            for src in image_urls:
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
        elif tag.lower() == "source":
            for src in _candidate_urls_from_attrs(attrs_dict, ["srcset", "data-srcset", "src"]):
                self.image_candidates.append(
                    ImageCandidate(
                        url=src.strip(),
                        source="source",
                        width=_parse_int(attrs_dict.get("width")),
                        height=_parse_int(attrs_dict.get("height")),
                    )
                )
        elif tag.lower() == "link":
            rel = (attrs_dict.get("rel") or "").lower()
            href = attrs_dict.get("href")
            if href and "image_src" in rel:
                self.image_candidates.append(ImageCandidate(url=href.strip(), source="link:image_src"))
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
    if _is_social_profile_url(link):
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


def is_disallowed_thumbnail_image(url: str | None) -> bool:
    if not url or is_fallback_preview_image(url):
        return True
    lowered = url.lower()
    return _is_social_platform_asset(lowered) or _text_contains_any(lowered, UTILITY_IMAGE_TERMS)


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _candidate_urls_from_attrs(attrs: dict[str, str], keys: list[str]) -> list[str]:
    urls: list[str] = []
    for key in keys:
        value = attrs.get(key)
        if not value:
            continue
        if key.endswith("srcset"):
            picked = _pick_largest_srcset_url(value)
            if picked:
                urls.append(picked)
        else:
            urls.append(value)
    return urls


def _pick_largest_srcset_url(value: str) -> str | None:
    best_url = None
    best_score = -1.0
    for item in value.split(","):
        parts = item.strip().split()
        if not parts:
            continue
        score = 1.0
        if len(parts) > 1:
            descriptor = parts[-1].lower()
            try:
                if descriptor.endswith("w"):
                    score = float(descriptor[:-1])
                elif descriptor.endswith("x"):
                    score = float(descriptor[:-1]) * 1000
            except ValueError:
                score = 1.0
        if score > best_score:
            best_url = parts[0]
            best_score = score
    return best_url


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


def _normalize_text(value: str | None) -> str:
    return (
        (value or "")
        .casefold()
        .replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
    )


def _name_tokens(value: str | None) -> list[str]:
    normalized = _normalize_text(value)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    stopwords = {"as", "sa", "ba", "og", "for", "the", "and", "of", "i", "in", "no", "org"}
    return [token for token in tokens if len(token) >= 3 and token not in stopwords]


def _candidate_text(candidate: ImageCandidate) -> str:
    parsed = urlparse(candidate.url)
    return _normalize_text(" ".join(filter(None, [candidate.url, parsed.path, candidate.alt, candidate.css_hint])))


def _text_contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _normalize_text(text)
    return any(_normalize_text(term) in normalized for term in terms)


def _candidate_mentions_actor(candidate: ImageCandidate, target_name: str | None) -> bool:
    tokens = _name_tokens(target_name)
    if not tokens:
        return False
    text = _candidate_text(candidate)
    if "-".join(tokens[: min(len(tokens), 4)]) in text.replace("_", "-"):
        return True
    matches = sum(1 for token in tokens if token in text)
    required = 1 if len(tokens) == 1 else 2
    return matches >= required


def _is_social_platform_asset(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if any(part in host for part in SOCIAL_STATIC_HOST_PARTS):
        return True
    social_logo_terms = (
        "facebook-logo",
        "fb_icon",
        "instagram_logo",
        "instagram-icon",
        "tiktok-logo",
        "tiktok-icon",
        "/static/images/ico/",
        "/rsrc.php/",
    )
    return any(term in path for term in social_logo_terms)


def _is_social_profile_url(link: str | None) -> bool:
    if not link:
        return False
    parsed = urlparse(link)
    host = (parsed.netloc or "").lower()
    return host in SOCIAL_PROFILE_HOSTS


def _candidate_is_disallowed(candidate: ImageCandidate, target_name: str | None) -> bool:
    text = _candidate_text(candidate)
    if is_disallowed_thumbnail_image(candidate.url):
        return True
    if _text_contains_any(text, PARTNER_IMAGE_TERMS) and not _candidate_mentions_actor(candidate, target_name):
        return True
    lower_text = _normalize_text(text)
    if "logo" in lower_text and any(term in lower_text for term in ["partner", "sponsor", "footer"]):
        return True
    return False


def _candidate_score(candidate: ImageCandidate, target_name: str | None = None) -> int:
    score = 0
    lower_url = candidate.url.lower()
    hint_text = " ".join(filter(None, [candidate.alt, candidate.css_hint])).lower()
    candidate_text = _candidate_text(candidate)

    if candidate.source == "og:image":
        score += 220
    elif candidate.source == "twitter:image":
        score += 180
    elif candidate.source == "link:image_src":
        score += 130
    elif candidate.source == "source":
        score += 95
    else:
        score += 80

    if _text_contains_any(lower_url, UTILITY_IMAGE_TERMS):
        score -= 260
    if _text_contains_any(hint_text, UTILITY_IMAGE_TERMS):
        score -= 220
    if "logo" in candidate_text:
        score -= 120
        if _candidate_mentions_actor(candidate, target_name):
            score += 150

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

    if _text_contains_any(candidate_text, PROMISING_IMAGE_TERMS):
        score += 28

    if _candidate_mentions_actor(candidate, target_name):
        score += 80

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


def choose_best_thumbnail(
    base_url: str,
    candidates: list[ImageCandidate],
    *,
    target_name: str | None = None,
) -> str | None:
    normalized: list[ImageCandidate] = []
    seen: set[str] = set()

    for candidate in candidates:
        normalized_candidate = _normalize_image_candidate(base_url, candidate)
        if not normalized_candidate:
            continue
        if _candidate_is_disallowed(normalized_candidate, target_name):
            continue
        if normalized_candidate.url in seen:
            continue
        seen.add(normalized_candidate.url)
        normalized.append(normalized_candidate)

    if not normalized:
        return None

    ranked = sorted(normalized, key=lambda candidate: _candidate_score(candidate, target_name), reverse=True)
    for candidate in ranked:
        if _candidate_score(candidate, target_name) < 40:
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
    if image_url and (not _is_public_http_url(image_url) or is_disallowed_thumbnail_image(image_url)):
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
    def _fit(value: str | None, max_length: int) -> str | None:
        if not value:
            return None
        return value[:max_length]

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
        safe_og_image = choose_best_thumbnail(
            primary,
            [ImageCandidate(url=og.image_url, source="og:image")] if og.image_url else [],
            target_name=organization.name,
        )
        auto_thumbnail = choose_best_thumbnail(primary, og.image_candidates, target_name=organization.name)
        organization.og_title = _fit(og.title, 255)
        organization.og_description = og.description
        organization.og_image_url = _fit(safe_og_image, 200)
        organization.auto_thumbnail_url = _fit(auto_thumbnail, 200)
    except Exception:
        organization.og_image_url = None
        organization.auto_thumbnail_url = None
        if not organization.og_title:
            organization.og_title = _fit(organization.name, 255)
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

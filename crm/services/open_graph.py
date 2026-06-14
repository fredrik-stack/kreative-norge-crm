from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import html
from html.parser import HTMLParser
import ipaddress
import json
import socket
import re
import struct
from urllib.parse import quote, urljoin, urlparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.utils import timezone

from crm.models import Organization


USER_AGENT = (
    "Mozilla/5.0 (compatible; KreativeNorgeCRM/1.0; +https://github.com/fredrik-stack/kreative-norge-crm)"
)
MAX_HTML_BYTES = 3_000_000
MAX_REDIRECTS = 3
FOLLOWUP_LINK_LIMIT = 4
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
    "sprite",
    "emoji",
    "placeholder",
    "loader",
    "blank",
    "transparent",
    "pixel",
    "avatar-default",
)
MISLEADING_IMAGE_TERMS = (
    "miljofyrtarn",
    "miljøfyrtårn",
    "gronn-festival",
    "grønn-festival",
    "green-festival",
    "sertifisering",
    "certification",
    "certificate",
    "qrcode",
    "qr-code",
    "qrcodelogin",
    "login",
    "pizza",
    "pressefoto",
    "ansatt",
    "employee",
    "staff",
    "ledig-stilling",
    "ny-produsent",
    "stillingsannonse",
    "stilling",
    "job-ad",
    "vacancy",
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
    "hkraft",
    "coop",
    "coop-nordland",
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
FOLLOWUP_LINK_TERMS = (
    "forside",
    "hjem",
    "home",
    "om",
    "about",
    "program",
    "arrangement",
    "event",
    "aktuelt",
    "nyheter",
    "news",
    "gallery",
    "galleri",
    "bilder",
    "media",
)
LOW_PRIORITY_ICON_REL_TERMS = ("icon", "apple-touch-icon", "mask-icon")
IMAGE_FILE_RE = re.compile(
    r"https?:\\?/\\?/[^\"'\s<>\\]+?\.(?:jpe?g|png|webp|gif|svg)(?:\?[^\"'\s<>\\]*)?",
    re.IGNORECASE,
)
STYLE_URL_RE = re.compile(r"url\((?P<quote>['\"]?)(?P<url>.*?)(?P=quote)\)", re.IGNORECASE)


@dataclass
class OpenGraphData:
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    image_candidates: list["ImageCandidate"] = field(default_factory=list)
    page_links: list[str] = field(default_factory=list)


@dataclass
class ImageCandidate:
    url: str
    source: str
    width: int | None = None
    height: int | None = None
    alt: str | None = None
    css_hint: str | None = None


@dataclass
class ImageProbe:
    content_type: str
    width: int | None = None
    height: int | None = None


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
        self.page_links: list[str] = []
        self._title_collect = False
        self._title_value = ""

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        attrs_dict = {k.lower(): v for k, v in attrs if k and v}
        if tag.lower() == "meta":
            prop = attrs_dict.get("property") or attrs_dict.get("name") or attrs_dict.get("itemprop")
            content = attrs_dict.get("content")
            if prop and content:
                self.meta[prop.lower()] = content.strip()
                lowered_prop = prop.lower()
                if lowered_prop in {"og:image", "twitter:image", "image"}:
                    self.image_candidates.append(
                        ImageCandidate(
                            url=content.strip(),
                            source=lowered_prop,
                        )
                    )
        if tag.lower() == "a":
            href = attrs_dict.get("href")
            if href:
                self.page_links.append(href.strip())
        if tag.lower() == "img":
            image_urls = _candidate_urls_from_attrs(
                attrs_dict,
                [
                    "src",
                    "data-src",
                    "data-original",
                    "data-lazy-src",
                    "data-image",
                    "data-image-url",
                    "data-bg",
                    "data-bg-image",
                    "data-background-image",
                    "data-background",
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
        if tag.lower() == "source":
            for src in _candidate_urls_from_attrs(attrs_dict, ["srcset", "data-srcset", "src"]):
                self.image_candidates.append(
                    ImageCandidate(
                        url=src.strip(),
                        source="source",
                        width=_parse_int(attrs_dict.get("width")),
                        height=_parse_int(attrs_dict.get("height")),
                    )
                )
        if tag.lower() == "link":
            rel = (attrs_dict.get("rel") or "").lower()
            href = attrs_dict.get("href")
            if href and "image_src" in rel:
                self.image_candidates.append(ImageCandidate(url=href.strip(), source="link:image_src"))
            elif href and any(term in rel for term in LOW_PRIORITY_ICON_REL_TERMS):
                self.image_candidates.append(ImageCandidate(url=href.strip(), source="link:icon"))
        style_urls = _extract_style_urls(attrs_dict.get("style") or "")
        for src in style_urls:
            self.image_candidates.append(
                ImageCandidate(
                    url=src,
                    source="style",
                    css_hint=" ".join(part for part in [tag.lower(), attrs_dict.get("class"), attrs_dict.get("id")] if part)
                    or None,
                )
            )
        if tag.lower() == "title":
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
    return (
        _is_social_platform_asset(lowered)
        or _text_contains_any(lowered, UTILITY_IMAGE_TERMS)
        or _text_contains_any(lowered, MISLEADING_IMAGE_TERMS)
    )


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


def _extract_style_urls(style: str) -> list[str]:
    if not style:
        return []
    urls = []
    for match in STYLE_URL_RE.finditer(style):
        value = match.group("url").strip()
        if value:
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
    normalized_url = _upgrade_cdn_image_url(urljoin(base_url, candidate.url))
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


def _embedded_image_candidates(html_text: str) -> list[ImageCandidate]:
    candidates: list[ImageCandidate] = []
    seen: set[str] = set()
    normalized_html = html.unescape(html_text).replace("\\/", "/")

    for match in IMAGE_FILE_RE.finditer(normalized_html):
        url = match.group(0).strip().rstrip("),.;")
        if url not in seen:
            seen.add(url)
            candidates.append(ImageCandidate(url=url, source="embedded"))

    for script_json in _json_ld_blocks(normalized_html):
        for url in _extract_json_image_urls(script_json):
            if url not in seen:
                seen.add(url)
                candidates.append(ImageCandidate(url=url, source="json-ld"))

    return candidates


def _json_ld_blocks(html_text: str) -> list[object]:
    blocks = re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parsed_blocks: list[object] = []
    for block in blocks:
        try:
            parsed_blocks.append(json.loads(html.unescape(block.strip())))
        except (TypeError, ValueError):
            continue
    return parsed_blocks


def _extract_json_image_urls(value: object) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).casefold()
            if lowered in {"image", "logo", "thumbnailurl", "contenturl", "url"}:
                urls.extend(_extract_json_image_urls(item))
            elif isinstance(item, (dict, list)):
                urls.extend(_extract_json_image_urls(item))
            elif isinstance(item, str) and lowered in {"image", "logo", "thumbnailurl", "contenturl"}:
                urls.append(item)
    elif isinstance(value, list):
        for item in value:
            urls.extend(_extract_json_image_urls(item))
    elif isinstance(value, str) and re.search(r"\.(?:jpe?g|png|webp|gif|svg)(?:\?|$)", value, re.I):
        urls.append(value)
    return urls


def _normalize_text(value: str | None) -> str:
    return (
        (value or "")
        .casefold()
        .replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
    )


def _loose_norwegian_text(value: str | None) -> str:
    return _normalize_text(value).replace("aa", "a")


def _name_tokens(value: str | None) -> list[str]:
    normalized = _loose_norwegian_text(value)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    stopwords = {"as", "sa", "ba", "og", "for", "the", "and", "of", "i", "in", "no", "org"}
    return [token for token in tokens if len(token) >= 3 and token not in stopwords]


def _candidate_text(candidate: ImageCandidate) -> str:
    parsed = urlparse(candidate.url)
    return _loose_norwegian_text(
        " ".join(filter(None, [candidate.url, parsed.path, candidate.alt, candidate.css_hint]))
    )


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
    if any(len(token) >= 6 and token in text for token in tokens):
        return True
    matches = sum(1 for token in tokens if token in text)
    required = 1 if len(tokens) == 1 else 2
    return matches >= required


def _upgrade_cdn_image_url(url: str) -> str:
    parsed = urlparse(url)
    if "static.wixstatic.com" in (parsed.netloc or "").lower():
        upgraded = re.sub(r"/v1/fill/w_\d+,h_\d+,", "/v1/fill/w_1200,h_675,", url)
        upgraded = re.sub(r",blur_\d+", "", upgraded)
        upgraded = re.sub(r",q_\d+", ",q_90", upgraded)
        return upgraded
    return url


def _is_social_platform_asset(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if any(part in host for part in SOCIAL_STATIC_HOST_PARTS):
        return True
    social_logo_terms = (
        "facebook-logo",
        "facebook-f-icon",
        "fb_icon",
        "fb-icon",
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
    if _is_social_icon_candidate(candidate):
        return True
    if _text_contains_any(text, MISLEADING_IMAGE_TERMS):
        return True
    if _text_contains_any(text, PARTNER_IMAGE_TERMS) and not _candidate_mentions_actor(candidate, target_name):
        return True
    lower_text = _normalize_text(text)
    if "logo" in lower_text and any(term in lower_text for term in ["partner", "sponsor", "footer"]):
        return True
    return False


def _is_social_icon_candidate(candidate: ImageCandidate) -> bool:
    text = _candidate_text(candidate)
    has_platform = any(platform in text for platform in ["facebook", "instagram", "tiktok", "linkedin", "youtube"])
    has_icon_or_logo = any(term in text for term in ["icon", "logo", "glyph", "symbol"])
    return has_platform and has_icon_or_logo and not _candidate_mentions_actor(candidate, None)


def _candidate_is_logo_like(candidate: ImageCandidate) -> bool:
    text = _candidate_text(candidate)
    return any(term in text for term in ["logo", "icon", "favicon", "apple-touch-icon", "brandmark"])


def _candidate_is_low_value_icon(candidate: ImageCandidate, target_name: str | None) -> bool:
    text = _candidate_text(candidate)
    if candidate.source not in {"link:icon", "generated:icon"}:
        return False
    if _candidate_mentions_actor(candidate, target_name):
        return False
    return any(term in text for term in ["favicon", "favikon", ".ico", "apple-touch-icon"])


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
    elif candidate.source == "link:icon":
        score += 12
    elif candidate.source == "json-ld":
        score += 125
    elif candidate.source == "embedded":
        score += 90
    elif candidate.source == "style":
        score += 85
    elif candidate.source == "social:facebook-profile-image":
        score += 155
    elif candidate.source in {"social:instagram-profile-image", "social:tiktok-profile-image"}:
        score += 150
    elif candidate.source == "external:page-screenshot":
        score += 135
    elif candidate.source == "source":
        score += 95
    else:
        score += 80

    if _text_contains_any(lower_url, UTILITY_IMAGE_TERMS):
        score -= 260
    if _text_contains_any(hint_text, UTILITY_IMAGE_TERMS):
        score -= 220
    if _candidate_is_logo_like(candidate):
        score -= 120
        if _candidate_mentions_actor(candidate, target_name):
            score += 190
    if _candidate_is_low_value_icon(candidate, target_name):
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
                        body = body[:max_bytes]
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


def _parse_image_probe(content_type: str, body: bytes) -> ImageProbe:
    content_type = (content_type or "").lower()
    if body.startswith(b"\x89PNG\r\n\x1a\n") and len(body) >= 24:
        width, height = struct.unpack(">II", body[16:24])
        return ImageProbe(content_type=content_type, width=width, height=height)
    if body.startswith(b"GIF87a") or body.startswith(b"GIF89a"):
        if len(body) >= 10:
            width, height = struct.unpack("<HH", body[6:10])
            return ImageProbe(content_type=content_type, width=width, height=height)
    if body.startswith(b"\x00\x00\x01\x00") and len(body) >= 8:
        width = body[6] or 256
        height = body[7] or 256
        return ImageProbe(content_type=content_type, width=width, height=height)
    if body.startswith(b"RIFF") and body[8:12] == b"WEBP":
        dimensions = _parse_webp_dimensions(body)
        if dimensions:
            return ImageProbe(content_type=content_type, width=dimensions[0], height=dimensions[1])
    if body.startswith(b"\xff\xd8"):
        dimensions = _parse_jpeg_dimensions(body)
        if dimensions:
            return ImageProbe(content_type=content_type, width=dimensions[0], height=dimensions[1])
    if "svg" in content_type or body.lstrip().startswith(b"<svg"):
        dimensions = _parse_svg_dimensions(body)
        return ImageProbe(content_type=content_type or "image/svg+xml", width=dimensions[0], height=dimensions[1])
    return ImageProbe(content_type=content_type)


def _parse_jpeg_dimensions(body: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 9 < len(body):
        if body[index] != 0xFF:
            index += 1
            continue
        marker = body[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(body):
            return None
        segment_length = int.from_bytes(body[index : index + 2], "big")
        if segment_length < 2:
            return None
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if index + 7 <= len(body):
                height = int.from_bytes(body[index + 3 : index + 5], "big")
                width = int.from_bytes(body[index + 5 : index + 7], "big")
                return width, height
            return None
        index += segment_length
    return None


def _parse_webp_dimensions(body: bytes) -> tuple[int, int] | None:
    if len(body) < 30:
        return None
    chunk = body[12:16]
    if chunk == b"VP8X" and len(body) >= 30:
        width = 1 + int.from_bytes(body[24:27], "little")
        height = 1 + int.from_bytes(body[27:30], "little")
        return width, height
    if chunk == b"VP8 " and len(body) >= 30:
        width = int.from_bytes(body[26:28], "little") & 0x3FFF
        height = int.from_bytes(body[28:30], "little") & 0x3FFF
        return width, height
    if chunk == b"VP8L" and len(body) >= 25:
        bits = int.from_bytes(body[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    return None


def _parse_svg_dimensions(body: bytes) -> tuple[int | None, int | None]:
    text = body[:4096].decode("utf-8", errors="ignore")
    width = _parse_svg_number(re.search(r"\bwidth=[\"']([^\"']+)[\"']", text))
    height = _parse_svg_number(re.search(r"\bheight=[\"']([^\"']+)[\"']", text))
    if width and height:
        return width, height
    viewbox = re.search(r"\bviewBox=[\"']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)", text)
    if viewbox:
        try:
            return int(float(viewbox.group(1))), int(float(viewbox.group(2)))
        except ValueError:
            return None, None
    return None, None


def _parse_svg_number(match: re.Match[str] | None) -> int | None:
    if not match:
        return None
    number = re.match(r"[\d.]+", match.group(1).strip())
    if not number:
        return None
    try:
        return int(float(number.group(0)))
    except ValueError:
        return None


def _probe_image_url(url: str, timeout_seconds: int = 4) -> ImageProbe | None:
    try:
        result = _fetch_url(
            url,
            timeout_seconds=timeout_seconds,
            max_bytes=262_144,
            allowed_content_prefixes=("image/",),
        )
    except Exception:
        return None
    return _parse_image_probe(result.headers.get("Content-Type") or "", result.body)


def _image_candidate_looks_usable(url: str, timeout_seconds: int = 4) -> bool:
    probe = _probe_image_url(url, timeout_seconds=timeout_seconds)
    if not probe:
        return False
    if probe.width and probe.height and (probe.width < 96 or probe.height < 96):
        return False
    return True


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
        if _candidate_is_low_value_icon(normalized_candidate, target_name):
            continue
        if normalized_candidate.url in seen:
            continue
        seen.add(normalized_candidate.url)
        normalized.append(normalized_candidate)

    if not normalized:
        return None

    ranked = sorted(normalized, key=lambda candidate: _candidate_score(candidate, target_name), reverse=True)
    strong_non_logo_ranked = [
        candidate
        for candidate in ranked
        if (
            not _candidate_is_logo_like(candidate)
            and _candidate_score(candidate, target_name) >= 40
            and not _candidate_is_weak_generic_image(candidate, target_name)
        )
    ]
    actor_logo_ranked = [
        candidate
        for candidate in ranked
        if (
            _candidate_is_logo_like(candidate)
            and _candidate_score(candidate, target_name) >= 40
            and _candidate_mentions_actor(candidate, target_name)
        )
    ]
    weak_non_logo_ranked = [
        candidate
        for candidate in ranked
        if (
            not _candidate_is_logo_like(candidate)
            and _candidate_score(candidate, target_name) >= 40
            and _candidate_is_weak_generic_image(candidate, target_name)
        )
    ]
    other_logo_ranked = [
        candidate
        for candidate in ranked
        if (
            _candidate_is_logo_like(candidate)
            and _candidate_score(candidate, target_name) >= 40
            and not _candidate_mentions_actor(candidate, target_name)
        )
    ]
    for group in [strong_non_logo_ranked, actor_logo_ranked, weak_non_logo_ranked, other_logo_ranked]:
        for candidate in group:
            if _image_candidate_looks_usable(candidate.url):
                return candidate.url
    return None


def _candidate_is_weak_generic_image(candidate: ImageCandidate, target_name: str | None) -> bool:
    if _candidate_mentions_actor(candidate, target_name):
        return False
    if candidate.source.startswith("social:") or candidate.source == "external:page-screenshot":
        return False
    if candidate.alt or candidate.css_hint:
        return False
    text = _candidate_text(candidate)
    generic_terms = ("uploads", "media", "image", "content", "static", "cdn", "squarespace")
    return candidate.source in {"img", "embedded", "source", "style"} and any(term in text for term in generic_terms)


def _site_icon_fallback_candidates(link: str | None) -> list[ImageCandidate]:
    if not link or _is_social_profile_url(link):
        return []
    parsed = urlparse(link)
    if not parsed.scheme or not parsed.netloc:
        return []
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [
        ImageCandidate(url=urljoin(root, path), source="generated:icon")
        for path in [
            "/apple-touch-icon.png",
            "/favicon-192x192.png",
        ]
    ]


def choose_site_icon_fallback(link: str | None) -> str | None:
    for candidate in _site_icon_fallback_candidates(link):
        normalized = _normalize_image_candidate(link or "", candidate)
        if not normalized:
            continue
        probe = _probe_image_url(normalized.url)
        if probe and probe.width and probe.height and probe.width >= 180 and probe.height >= 180:
            return normalized.url
    return None


def _same_site_url(base_url: str, maybe_url: str | None) -> str | None:
    if not maybe_url:
        return None
    resolved = urljoin(base_url, maybe_url)
    parsed_base = urlparse(base_url)
    parsed_resolved = urlparse(resolved)
    if parsed_resolved.scheme not in {"http", "https"}:
        return None
    if (parsed_base.hostname or "").lower() != (parsed_resolved.hostname or "").lower():
        return None
    if parsed_resolved.path.lower().endswith((".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx")):
        return None
    return resolved


def _candidate_followup_links(base_url: str, page_links: list[str]) -> list[str]:
    if _is_social_profile_url(base_url):
        return []
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else None
    normalized: list[str] = []
    seen = {base_url.rstrip("/")}

    for link in [root, *page_links]:
        resolved = _same_site_url(base_url, link)
        if not resolved:
            continue
        key = resolved.rstrip("/")
        if key in seen:
            continue
        link_text = _loose_norwegian_text(resolved)
        if link != root and not any(term in link_text for term in FOLLOWUP_LINK_TERMS):
            continue
        seen.add(key)
        normalized.append(resolved)
        if len(normalized) >= FOLLOWUP_LINK_LIMIT:
            break
    return normalized


def _facebook_handle_from_url(link: str | None) -> str | None:
    if not link:
        return None
    parsed = urlparse(link)
    host = (parsed.netloc or "").lower()
    if host not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return None
    handle = parts[0]
    if handle in {"profile.php", "pages", "groups", "events", "login"}:
        return None
    return handle


def _instagram_handle_from_url(link: str | None) -> str | None:
    if not link:
        return None
    parsed = urlparse(link)
    host = (parsed.netloc or "").lower()
    if host not in {"instagram.com", "www.instagram.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return None
    handle = parts[0].lstrip("@")
    if handle in {"accounts", "explore", "p", "reel", "reels", "stories", "about", "developer"}:
        return None
    return handle


def _tiktok_handle_from_url(link: str | None) -> str | None:
    if not link:
        return None
    parsed = urlparse(link)
    host = (parsed.netloc or "").lower()
    if host not in {"tiktok.com", "www.tiktok.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return None
    handle = parts[0].lstrip("@")
    if not handle or handle in {"discover", "tag", "music", "embed", "login"}:
        return None
    return handle


def _social_profile_image_candidates(link: str | None) -> list[ImageCandidate]:
    facebook_handle = _facebook_handle_from_url(link)
    if facebook_handle:
        return [
            ImageCandidate(
                url=f"https://graph.facebook.com/{facebook_handle}/picture?type=large",
                source="social:facebook-profile-image",
            )
        ]
    instagram_handle = _instagram_handle_from_url(link)
    if instagram_handle:
        return [
            ImageCandidate(
                url=f"https://unavatar.io/instagram/{instagram_handle}",
                source="social:instagram-profile-image",
                alt=instagram_handle,
            )
        ]
    tiktok_handle = _tiktok_handle_from_url(link)
    if tiktok_handle:
        return [
            ImageCandidate(
                url=f"https://unavatar.io/tiktok/{tiktok_handle}",
                source="social:tiktok-profile-image",
                alt=tiktok_handle,
            )
        ]
    return []


def _page_screenshot_candidates(link: str | None) -> list[ImageCandidate]:
    if not link or _is_social_profile_url(link):
        return []
    parsed = urlparse(link)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []
    return [
        ImageCandidate(
            url=f"https://s0.wp.com/mshots/v1/{quote(link, safe='')}?w=900",
            source="external:page-screenshot",
        )
    ]


def _organization_candidate_links(organization: Organization) -> list[str]:
    links = [
        organization.website_url,
        organization.instagram_url,
        organization.facebook_url,
        organization.tiktok_url,
        organization.youtube_url,
        organization.linkedin_url,
    ]
    unique_links = []
    seen = set()
    for link in links:
        if not link or link in seen:
            continue
        seen.add(link)
        unique_links.append(link)
    return unique_links


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
    image_candidates = parser.image_candidates + _embedded_image_candidates(html)

    raw_image = parser.meta.get("og:image") or parser.meta.get("twitter:image")
    image_url = urljoin(result.final_url, raw_image) if raw_image else None
    if image_url and (not _is_public_http_url(image_url) or is_disallowed_thumbnail_image(image_url)):
        image_url = None

    return OpenGraphData(
        title=parser.meta.get("og:title") or parser.title,
        description=parser.meta.get("og:description"),
        image_url=image_url,
        image_candidates=image_candidates,
        page_links=parser.page_links,
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
        title = None
        description = None
        safe_og_image = None
        auto_thumbnail = None
        first_error = None
        candidate_links = _organization_candidate_links(organization)
        fetched_links: set[str] = set()

        for link in candidate_links:
            try:
                og = fetch_open_graph(link)
            except Exception as exc:
                first_error = first_error or exc
                continue
            fetched_links.add(link.rstrip("/"))

            if link == primary:
                title = og.title
                description = og.description
                safe_og_image = choose_best_thumbnail(
                    link,
                    [ImageCandidate(url=og.image_url, source="og:image")] if og.image_url else [],
                    target_name=organization.name,
                )

            if not auto_thumbnail:
                auto_thumbnail = choose_best_thumbnail(link, og.image_candidates, target_name=organization.name)
            if not auto_thumbnail:
                for followup_link in _candidate_followup_links(link, og.page_links):
                    key = followup_link.rstrip("/")
                    if key in fetched_links:
                        continue
                    fetched_links.add(key)
                    try:
                        followup_og = fetch_open_graph(followup_link)
                    except Exception as exc:
                        first_error = first_error or exc
                        continue
                    auto_thumbnail = choose_best_thumbnail(
                        followup_link,
                        followup_og.image_candidates,
                        target_name=organization.name,
                    )
                    if auto_thumbnail:
                        break
            if auto_thumbnail and link == primary:
                break

        if not auto_thumbnail:
            for link in candidate_links:
                social_thumbnail = choose_best_thumbnail(
                    link,
                    _social_profile_image_candidates(link),
                    target_name=organization.name,
                )
                if social_thumbnail:
                    auto_thumbnail = social_thumbnail
                    break

        if not auto_thumbnail:
            for link in candidate_links:
                screenshot_thumbnail = choose_best_thumbnail(
                    link,
                    _page_screenshot_candidates(link),
                    target_name=organization.name,
                )
                if screenshot_thumbnail:
                    auto_thumbnail = screenshot_thumbnail
                    break

        if not auto_thumbnail:
            auto_thumbnail = choose_site_icon_fallback(primary)

        if not title and not auto_thumbnail and first_error:
            raise first_error

        organization.og_title = _fit(title, 255)
        organization.og_description = description
        organization.og_image_url = _fit(safe_og_image, 500)
        organization.auto_thumbnail_url = _fit(auto_thumbnail, 500)
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

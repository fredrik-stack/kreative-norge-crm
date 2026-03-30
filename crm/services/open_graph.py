from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from django.utils import timezone

from crm.models import Organization


USER_AGENT = (
    "Mozilla/5.0 (compatible; KreativeNorgeCRM/1.0; +https://github.com/fredrik-stack/kreative-norge-crm)"
)


@dataclass
class OpenGraphData:
    title: str | None = None
    description: str | None = None
    image_url: str | None = None


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self._title_collect = False
        self._title_value = ""

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        attrs_dict = {k.lower(): v for k, v in attrs if k and v}
        if tag.lower() == "meta":
            prop = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content")
            if prop and content:
                self.meta[prop.lower()] = content.strip()
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


def fallback_preview_image(link: str | None) -> str | None:
    if not link:
        return None
    parsed = urlparse(link)
    if not parsed.netloc:
        return None
    return f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=256"


def is_fallback_preview_image(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.netloc in {"www.google.com", "google.com"} and parsed.path.startswith("/s2/favicons")


def fetch_open_graph(url: str, timeout_seconds: int = 4) -> OpenGraphData:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="replace")

    parser = MetaParser()
    parser.feed(html)

    raw_image = parser.meta.get("og:image") or parser.meta.get("twitter:image")
    image_url = urljoin(url, raw_image) if raw_image else None

    return OpenGraphData(
        title=parser.meta.get("og:title") or parser.title,
        description=parser.meta.get("og:description"),
        image_url=image_url,
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
        organization.og_last_fetched_at = now
        organization.save(
            update_fields=["og_title", "og_description", "og_image_url", "og_last_fetched_at"]
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
    except Exception:
        organization.og_image_url = None
        if not organization.og_title:
            organization.og_title = organization.name
    organization.og_last_fetched_at = now
    organization.save(
        update_fields=["og_title", "og_description", "og_image_url", "og_last_fetched_at"]
    )

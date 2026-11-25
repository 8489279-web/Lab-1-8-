from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)


@dataclass(frozen=True, slots=True)
class Page:
    url: str
    title: str
    text: str
    fetched_at: datetime


def canonicalize(url: str) -> str:
    parts = urlsplit(url)

    scheme = parts.scheme.lower()
    host = parts.netloc.lower()

    path = parts.path.rstrip("/") or "/"

    query = urlencode(
        sorted(
            parse_qsl(
                parts.query,
                keep_blank_values=True,
            )
        )
    )

    return urlunsplit((scheme, host, path, query, ""))


def allowed_url(
    url: str,
    allowed_domains: set[str],
) -> bool:
    parts = urlsplit(url)

    return (
        parts.scheme in ("http", "https")
        and parts.hostname is not None
        and parts.hostname.lower() in allowed_domains
        and parts.username is None
        and parts.password is None
    )


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

        self.links: list[str] = []
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

        self.in_title = False
        self.ignored_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag in ("script", "style", "noscript"):
            self.ignored_depth += 1

        if tag == "title":
            self.in_title = True

        if tag == "a":
            attributes = dict(attrs)
            href = attributes.get("href")

            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self.ignored_depth = max(
                0,
                self.ignored_depth - 1,
            )

        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return

        value = data.strip()

        if not value:
            return

        if self.in_title:
            self.title_parts.append(value)
        else:
            self.text_parts.append(value)


def parse_html(
    url: str,
    html: str,
) -> tuple[str, str, list[str]]:
    parser = PageParser()
    parser.feed(html)
    parser.close()

    title = " ".join(parser.title_parts)
    text = " ".join(parser.text_parts)

    links: list[str] = []

    for href in parser.links:
        try:
            absolute = urljoin(url, href)
            parts = urlsplit(absolute)

            if parts.scheme in ("http", "https"):
                links.append(canonicalize(absolute))
        except ValueError:
            continue

    return title, text, links

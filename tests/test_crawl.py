import httpx
import pytest

from findex.crawler.crawl import crawl
from findex.crawler.parser import canonicalize, parse_html


def test_canonicalize() -> None:
    url = "HTTPS://EXAMPLE.COM/page/?b=2&a=1#section"

    assert canonicalize(url) == ("https://example.com/page?a=1&b=2")


def test_parse_html() -> None:
    html = """
    <title>Test page</title>
    <p>Hello world</p>
    <script>hidden text</script>
    <a href="/next">Next</a>
    """

    title, text, links = parse_html(
        "https://example.com",
        html,
    )

    assert title == "Test page"
    assert "Hello world" in text
    assert "hidden text" not in text
    assert links == ["https://example.com/next"]


@pytest.mark.asyncio
async def test_crawl_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        if request.url.path == "/":
            return httpx.Response(
                200,
                text='<title>Home</title><a href="/page">Page</a>',
            )

        return httpx.Response(
            200,
            text="<title>Second page</title><p>Content</p>",
        )

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            max_pages=10,
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert len(pages) == 2
    assert pages[0].title == "Home"
    assert pages[1].title == "Second page"


@pytest.mark.asyncio
async def test_crawl_duplicates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        return httpx.Response(
            200,
            text="""
            <a href="/">Home</a>
            <a href="/#section">Duplicate</a>
            <a href="/page">Page</a>
            <a href="/page/">Duplicate page</a>
            """,
        )

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            max_pages=10,
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert len(pages) == 2
    assert len({page.url for page in pages}) == 2


@pytest.mark.asyncio
async def test_crawl_allowed_domains() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "example.com"

        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        return httpx.Response(
            200,
            text='<a href="https://other.com">External</a>',
        )

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            allowed_domains={"example.com"},
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert len(pages) == 1


@pytest.mark.asyncio
async def test_crawl_robots_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow: /private",
            )

        assert request.url.path != "/private"

        return httpx.Response(
            200,
            text='<a href="/private">Private</a>',
        )

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert len(pages) == 1


@pytest.mark.asyncio
async def test_crawl_max_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        links = "".join(f'<a href="/page{i}">Page {i}</a>' for i in range(20))

        return httpx.Response(200, text=links)

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            max_pages=5,
            concurrency=10,
            per_host=2,
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert len(pages) == 5

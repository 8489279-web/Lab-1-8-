import asyncio

import httpx
import pytest

from findex.crawler.crawl import crawl


@pytest.mark.asyncio
async def test_redirect_allowed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        if request.url.path == "/":
            return httpx.Response(
                302,
                headers={"Location": "/target"},
            )

        return httpx.Response(200, text="<title>Target</title>")

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert len(pages) == 1
    assert pages[0].url == "https://example.com/target"
    assert pages[0].title == "Target"


@pytest.mark.asyncio
async def test_redirect_external_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "example.com"

        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        return httpx.Response(
            302,
            headers={"Location": "https://other.com"},
        )

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert pages == []


@pytest.mark.asyncio
async def test_redirect_loop() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls

        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        calls += 1

        target = "/second" if request.url.path == "/" else "/"

        return httpx.Response(
            302,
            headers={"Location": target},
        )

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert pages == []
    assert calls == 2


@pytest.mark.asyncio
async def test_concurrency_limit() -> None:
    active = 0
    peak = 0

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal active, peak

        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *")

        active += 1
        peak = max(peak, active)

        try:
            await asyncio.sleep(0.05)

            if request.url.path == "/":
                links = "".join(f'<a href="/page{i}">Page</a>' for i in range(10))
                return httpx.Response(200, text=links)

            return httpx.Response(200, text="Content")

        finally:
            active -= 1

    pages = [
        page
        async for page in crawl(
            ["https://example.com"],
            max_pages=20,
            concurrency=5,
            per_host=2,
            min_delay=0,
            transport=httpx.MockTransport(handler),
        )
    ]

    assert len(pages) == 11
    assert peak == 2
    assert active == 0

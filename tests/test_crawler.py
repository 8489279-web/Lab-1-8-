import asyncio

import httpx
import pytest

from findex.crawler.fetch import fetch, retry_delay
from findex.crawler.robots import RobotsCache


@pytest.mark.asyncio
async def test_fetch_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Hello crawler")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch(client, "https://example.com")

    assert result.status == 200
    assert result.content == b"Hello crawler"
    assert result.attempts == 1
    assert result.size == 13
    assert result.error is None


@pytest.mark.asyncio
async def test_fetch_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch(client, "https://example.com/missing")

    assert result.status == 404
    assert result.attempts == 1
    assert result.error == "HTTP 404"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 503])
async def test_fetch_retry(status: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1

        if calls == 1:
            return httpx.Response(
                status,
                headers={"Retry-After": "0"},
            )

        return httpx.Response(200, text="Success")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch(client, "https://example.com")

    assert result.status == 200
    assert result.attempts == 2
    assert calls == 2


@pytest.mark.asyncio
async def test_fetch_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "findex.crawler.fetch.retry_delay",
        lambda *args: 0.0,
    )

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        await asyncio.sleep(0.1)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch(
            client,
            "https://example.com",
            timeout=0.01,
        )

    assert result.status == 0
    assert result.error == "Timeout"
    assert result.attempts == 4


def test_retry_after() -> None:
    assert retry_delay(0, "5") >= 5.0


@pytest.mark.asyncio
async def test_robots_rules() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="User-agent: *\nDisallow: /private\nCrawl-delay: 2",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        robots = RobotsCache(client)

        assert await robots.allowed("https://example.com/public")

        assert not await robots.allowed("https://example.com/private")

        assert await robots.crawl_delay("https://example.com") == 2.0


@pytest.mark.asyncio
async def test_robots_cache() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            text="User-agent: *\nDisallow:",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        robots = RobotsCache(client)

        results = await asyncio.gather(
            robots.allowed("https://example.com/page1"),
            robots.allowed("https://example.com/page2"),
            robots.allowed("https://example.com/page3"),
        )

    assert all(results)
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [(404, True), (410, True), (403, False)],
)
async def test_robots_missing_or_denied(
    status: int,
    expected: bool,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        robots = RobotsCache(client)

        assert await robots.allowed("https://example.com/page") == expected

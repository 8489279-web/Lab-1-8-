import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from urllib.parse import urljoin, urlsplit

import httpx

from findex.crawler.fetch import USER_AGENT, fetch
from findex.crawler.parser import (
    Page,
    allowed_url,
    canonicalize,
    parse_html,
)
from findex.crawler.robots import RobotsCache

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    pages: int = 0
    in_flight: int = 0
    errors: int = 0
    queue_depth: int = 0


async def crawl(
    seeds: list[str],
    *,
    max_pages: int = 500,
    concurrency: int = 10,
    per_host: int = 2,
    allowed_domains: set[str] | None = None,
    min_delay: float = 0.1,
    transport: httpx.AsyncBaseTransport | None = None,
    stats: CrawlStats | None = None,
) -> AsyncGenerator[Page, None]:
    if min(max_pages, concurrency, per_host) < 1:
        raise ValueError("Limits must be positive")

    if min_delay < 0:
        raise ValueError("Delay cannot be negative")

    metrics = stats if stats is not None else CrawlStats()

    metrics.pages = 0
    metrics.in_flight = 0
    metrics.errors = 0
    metrics.queue_depth = 0

    domains = {domain.lower() for domain in (allowed_domains or set())}

    if allowed_domains is None:
        for seed in seeds:
            host = urlsplit(seed).hostname

            if host is not None:
                domains.add(host.lower())

    frontier: asyncio.Queue[str] = asyncio.Queue()
    results: asyncio.Queue[Page | None] = asyncio.Queue()

    result_slots = asyncio.Semaphore(concurrency)

    seen: set[str] = set()

    global_limit = asyncio.Semaphore(concurrency)
    host_limits: dict[str, asyncio.Semaphore] = {}
    host_locks: dict[str, asyncio.Lock] = {}
    last_request: dict[str, float] = {}
    host_delays: dict[str, float] = {}

    stopped = asyncio.Event()

    @asynccontextmanager
    async def request_gate(
        url: str,
    ) -> AsyncGenerator[None, None]:
        host = urlsplit(url).hostname or ""

        host_limit = host_limits.setdefault(
            host,
            asyncio.Semaphore(per_host),
        )

        host_lock = host_locks.setdefault(
            host,
            asyncio.Lock(),
        )

        async with host_limit, global_limit:
            async with host_lock:
                delay = max(
                    min_delay,
                    host_delays.get(host, 0.0),
                )

                previous = last_request.get(host, 0.0)
                remaining = delay - (monotonic() - previous)

                if remaining > 0:
                    await asyncio.sleep(remaining)

                last_request[host] = monotonic()

            metrics.in_flight += 1

            try:
                yield
            finally:
                metrics.in_flight -= 1

    def enqueue(url: str) -> None:
        try:
            url = canonicalize(url)

            if not allowed_url(url, domains):
                logger.info("Blocked domain: %s", url)
                return

            if url in seen or stopped.is_set():
                return

            seen.add(url)
            frontier.put_nowait(url)

            metrics.queue_depth = frontier.qsize()

        except ValueError:
            metrics.errors += 1
            logger.warning("Invalid URL: %s", url)

    for seed in seeds:
        enqueue(seed)

    client = await asyncio.to_thread(
        httpx.AsyncClient,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=False,
        transport=transport,
    )

    async with client:
        robots = RobotsCache(client, gate=request_gate)

        async def worker() -> None:
            while not stopped.is_set():
                url = await frontier.get()

                metrics.queue_depth = frontier.qsize()

                try:
                    if stopped.is_set():
                        continue

                    if not await robots.allowed(url):
                        logger.info(
                            "Blocked by robots.txt: %s",
                            url,
                        )
                        continue

                    host = urlsplit(url).hostname or ""

                    host_delays[host] = max(
                        host_delays.get(host, 0.0),
                        await robots.crawl_delay(url),
                    )

                    result = await fetch(
                        client,
                        url,
                        gate=request_gate,
                    )

                    if result.status in (301, 302, 303, 307, 308):
                        if result.location:
                            try:
                                target = urljoin(
                                    url,
                                    result.location,
                                )

                                logger.info(
                                    "Redirect: %s -> %s",
                                    url,
                                    target,
                                )

                                enqueue(target)

                            except ValueError:
                                metrics.errors += 1

                                logger.warning(
                                    "Invalid redirect: %s",
                                    url,
                                )
                        else:
                            metrics.errors += 1

                        continue

                    if result.status != 200:
                        metrics.errors += 1

                        logger.warning(
                            "Skipped url=%s status=%s",
                            url,
                            result.status,
                        )
                        continue

                    html = result.content.decode(
                        "utf-8",
                        errors="replace",
                    )

                    title, text, links = await asyncio.to_thread(
                        parse_html,
                        url,
                        html,
                    )

                    await result_slots.acquire()

                    if metrics.pages >= max_pages:
                        result_slots.release()
                        continue

                    page = Page(
                        url=url,
                        title=title,
                        text=text,
                        fetched_at=datetime.now(UTC),
                    )

                    metrics.pages += 1

                    results.put_nowait(page)

                    if metrics.pages >= max_pages:
                        stopped.set()
                        return

                    for link in links:
                        enqueue(link)

                finally:
                    frontier.task_done()

        async def supervise() -> None:
            try:
                async with asyncio.TaskGroup() as group:
                    workers = [group.create_task(worker()) for _ in range(concurrency)]

                    completed = group.create_task(frontier.join())

                    limit_reached = group.create_task(stopped.wait())

                    await asyncio.wait(
                        [completed, limit_reached],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    stopped.set()

                    for task in workers:
                        task.cancel()

                    completed.cancel()
                    limit_reached.cancel()

            finally:
                while not frontier.empty():
                    frontier.get_nowait()
                    frontier.task_done()

                metrics.queue_depth = 0

                results.put_nowait(None)

        supervisor = asyncio.create_task(supervise())

        try:
            while True:
                page = await results.get()

                if page is None:
                    await supervisor
                    break

                result_slots.release()

                yield page

        finally:
            stopped.set()

            if not supervisor.done():
                supervisor.cancel()

            try:
                await supervisor
            except asyncio.CancelledError:
                pass

import asyncio
from urllib.robotparser import RobotFileParser

import httpx

from findex.crawler.fetch import (
    USER_AGENT,
    RequestGate,
    fetch,
    unrestricted,
)


class RobotsCache:
    def __init__(
        self,
        client: httpx.AsyncClient,
        gate: RequestGate = unrestricted,
    ) -> None:
        self.client = client
        self.gate = gate
        self.cache: dict[str, RobotFileParser] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    async def get_parser(self, url: str) -> RobotFileParser:
        parsed = httpx.URL(url)

        origin = str(
            parsed.copy_with(
                path="/",
                query=None,
                fragment=None,
            )
        ).rstrip("/")

        lock = self.locks.setdefault(
            origin,
            asyncio.Lock(),
        )

        async with lock:
            if origin in self.cache:
                return self.cache[origin]

            robots_url = f"{origin}/robots.txt"
            parser = RobotFileParser(robots_url)

            result = await fetch(
                self.client,
                robots_url,
                gate=self.gate,
            )

            if result.status == 200:
                content = result.content.decode(
                    "utf-8",
                    errors="replace",
                )
                parser.parse(content.splitlines())

            elif result.status in (404, 410):
                parser.parse(
                    [
                        "User-agent: *",
                        "Disallow:",
                    ]
                )

            else:
                parser.parse(
                    [
                        "User-agent: *",
                        "Disallow: /",
                    ]
                )

            self.cache[origin] = parser
            return parser

    async def allowed(self, url: str) -> bool:
        parser = await self.get_parser(url)
        return parser.can_fetch(USER_AGENT, url)

    async def crawl_delay(self, url: str) -> float:
        parser = await self.get_parser(url)
        delay = parser.crawl_delay(USER_AGENT)

        if delay is None:
            delay = parser.crawl_delay("*")

        return float(delay or 0)

import asyncio
import logging
import random
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import perf_counter

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "FindexCrawler/0.6 (+https://github.com/8489279-web)"

RequestGate = Callable[[str], AbstractAsyncContextManager[None]]


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    status: int
    content: bytes
    elapsed: float
    attempts: int
    error: str | None = None
    location: str | None = None

    @property
    def size(self) -> int:
        return len(self.content)


@asynccontextmanager
async def unrestricted(url: str) -> AsyncGenerator[None, None]:
    yield


def retry_delay(
    attempt: int,
    retry_after: str | None = None,
) -> float:
    delay = min(30.0, 0.5 * 2**attempt)
    delay += random.uniform(0.0, 1.0)

    if retry_after is not None:
        try:
            return max(delay, float(retry_after))
        except ValueError:
            try:
                date = parsedate_to_datetime(retry_after)

                if date.tzinfo is None:
                    date = date.replace(tzinfo=UTC)

                seconds = (date - datetime.now(UTC)).total_seconds()
                return max(delay, seconds)

            except (ValueError, TypeError, OverflowError):
                pass

    return delay


async def fetch(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 10.0,
    gate: RequestGate = unrestricted,
) -> FetchResult:
    start = perf_counter()
    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            async with gate(url):
                async with asyncio.timeout(timeout):
                    response = await client.get(
                        url,
                        headers={"User-Agent": USER_AGENT},
                        follow_redirects=False,
                    )

            status = response.status_code
            elapsed = perf_counter() - start

            logger.info(
                "url=%s status=%s bytes=%s elapsed=%.6f attempt=%s",
                url,
                status,
                len(response.content),
                elapsed,
                attempt + 1,
            )

            retryable = status == 429 or 500 <= status <= 599

            if retryable and attempt < max_retries:
                delay = retry_delay(
                    attempt,
                    response.headers.get("Retry-After"),
                )

                logger.warning(
                    "Retry url=%s status=%s delay=%.3f",
                    url,
                    status,
                    delay,
                )

                await asyncio.sleep(delay)
                continue

            return FetchResult(
                url=url,
                status=status,
                content=response.content,
                elapsed=elapsed,
                attempts=attempt + 1,
                error=f"HTTP {status}" if status >= 400 else None,
                location=response.headers.get("Location"),
            )

        except (TimeoutError, httpx.TimeoutException):
            logger.warning(
                "url=%s status=timeout bytes=0 elapsed=%.6f attempt=%s",
                url,
                perf_counter() - start,
                attempt + 1,
            )

            if attempt < max_retries:
                await asyncio.sleep(retry_delay(attempt))
                continue

            return FetchResult(
                url=url,
                status=0,
                content=b"",
                elapsed=perf_counter() - start,
                attempts=attempt + 1,
                error="Timeout",
            )

        except httpx.RequestError as error:
            logger.warning(
                "url=%s status=error bytes=0 elapsed=%.6f error=%s",
                url,
                perf_counter() - start,
                error,
            )

            return FetchResult(
                url=url,
                status=0,
                content=b"",
                elapsed=perf_counter() - start,
                attempts=attempt + 1,
                error=str(error),
            )

    raise RuntimeError("Unexpected retry state")

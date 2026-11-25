import asyncio
from time import perf_counter

import httpx


async def main() -> None:
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8001",
        timeout=30.0,
    ) as client:
        await client.get("/search", params={"q": "asyncio"})
        async def request() -> float:
            start = perf_counter()
            response = await client.get(
                "/search",
                params={"q": "asyncio"},
            )
            response.raise_for_status()
            return (perf_counter() - start) * 1000
        start = perf_counter()
        results = await asyncio.gather(
            *(request() for _ in range(20))
        )
        elapsed = perf_counter() - start
        print(f"Requests: {len(results)}")
        print(f"Total time: {elapsed * 1000:.3f} ms")
        print(f"Average latency: {sum(results) / len(results):.3f} ms")
        print(f"Min latency: {min(results):.3f} ms")
        print(f"Max latency: {max(results):.3f} ms")
        print(f"Requests/sec: {len(results) / elapsed:.3f}")
if __name__ == "__main__":
    asyncio.run(main())

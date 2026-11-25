import asyncio
import json
import logging
from contextlib import aclosing
from dataclasses import asdict
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from queue import SimpleQueue
from time import perf_counter

from rich.console import Console
from rich.live import Live
from rich.table import Table

from findex.crawler.crawl import CrawlStats, crawl


async def run_crawler(
    seed: str,
    *,
    max_pages: int,
    concurrency: int,
    per_host: int,
    out: Path,
    min_delay: float = 0.1,
) -> int:
    console = Console()
    start = perf_counter()
    pages = 0
    stats = CrawlStats()

    await asyncio.to_thread(
        out.parent.mkdir,
        parents=True,
        exist_ok=True,
    )

    def dashboard() -> Table:
        elapsed = perf_counter() - start

        table = Table(title="Async crawler")
        table.add_column("Parameter")
        table.add_column("Value")

        table.add_row("Seed", seed)
        table.add_row(
            "Pages fetched",
            f"{stats.pages}/{max_pages}",
        )
        table.add_row("Pages saved", str(pages))
        table.add_row("Concurrency", str(concurrency))
        table.add_row("Per-host limit", str(per_host))
        table.add_row("In-flight", str(stats.in_flight))
        table.add_row("Errors", str(stats.errors))
        table.add_row("Queue depth", str(stats.queue_depth))
        table.add_row("Elapsed", f"{elapsed:.2f} s")
        table.add_row(
            "Pages/s",
            f"{pages / max(elapsed, 0.001):.2f}",
        )
        table.add_row("Output", str(out))

        return table

    file = await asyncio.to_thread(
        out.open,
        "w",
        encoding="utf-8",
    )

    live = Live(
        dashboard(),
        console=console,
        auto_refresh=False,
    )

    async def refresh_dashboard() -> None:
        while True:
            await asyncio.to_thread(
                live.update,
                dashboard(),
                refresh=True,
            )
            await asyncio.sleep(0.25)

    try:
        await asyncio.to_thread(live.start)

        refresh_task = asyncio.create_task(refresh_dashboard())

        try:
            async with aclosing(
                crawl(
                    [seed],
                    max_pages=max_pages,
                    concurrency=concurrency,
                    per_host=per_host,
                    min_delay=min_delay,
                    stats=stats,
                )
            ) as stream:
                async for page in stream:
                    record = asdict(page)
                    record["fetched_at"] = page.fetched_at.isoformat()

                    line = json.dumps(
                        record,
                        ensure_ascii=False,
                    )

                    await asyncio.to_thread(
                        file.write,
                        line + "\n",
                    )

                    await asyncio.to_thread(file.flush)

                    pages += 1

        finally:
            refresh_task.cancel()

            try:
                await refresh_task
            except asyncio.CancelledError:
                pass

            await asyncio.to_thread(
                live.update,
                dashboard(),
                refresh=True,
            )

    finally:
        await asyncio.to_thread(live.stop)
        await asyncio.to_thread(file.close)

    elapsed = perf_counter() - start

    console.print(f"Pages fetched: {pages}")
    console.print(f"Wall time: {elapsed:.3f} s")
    console.print(f"Pages/s: {pages / max(elapsed, 0.001):.3f}")
    console.print(f"Errors: {stats.errors}")
    console.print(f"Saved to: {out}")
    console.print("Log: crawl.log")

    return pages


def execute_crawl(
    seed: str,
    *,
    max_pages: int,
    concurrency: int,
    per_host: int,
    out: Path,
    min_delay: float = 0.1,
) -> int:
    log_queue: SimpleQueue[logging.LogRecord] = SimpleQueue()

    queue_handler = QueueHandler(log_queue)

    file_handler = logging.FileHandler(
        "crawl.log",
        mode="w",
        encoding="utf-8",
    )

    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )

    logger = logging.getLogger("findex.crawler")
    previous_level = logger.level
    previous_propagate = logger.propagate

    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(queue_handler)

    listener = QueueListener(
        log_queue,
        file_handler,
    )

    listener.start()

    try:
        return asyncio.run(
            run_crawler(
                seed,
                max_pages=max_pages,
                concurrency=concurrency,
                per_host=per_host,
                out=out,
                min_delay=min_delay,
            ),
            debug=True,
        )

    finally:
        listener.stop()
        logger.removeHandler(queue_handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        file_handler.close()

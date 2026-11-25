import csv
import os
import sys
from pathlib import Path
from statistics import median
from threading import Event, Thread
from time import perf_counter, process_time

import psutil

from findex.index import BuildMetrics, ExecutorName, build_index


def measure(
    executor: ExecutorName,
    workers: int,
) -> tuple[float, float, float, float]:
    wall_times: list[float] = []
    cpu_times: list[float] = []
    rss_values: list[float] = []
    merge_times: list[float] = []

    process = psutil.Process()

    for _ in range(3):
        metrics = BuildMetrics()
        stop = Event()
        rss_samples = [process.memory_info().rss]

        def monitor(
            stop: Event = stop,
            rss_samples: list[int] = rss_samples,
        ) -> None:
            while not stop.wait(0.001):
                rss_samples.append(process.memory_info().rss)

        monitor_thread = Thread(
            target=monitor,
            daemon=True,
        )

        monitor_thread.start()

        wall_start = perf_counter()
        cpu_start = process_time()

        try:
            index = build_index(
                "data",
                with_positions=True,
                workers=workers,
                executor=executor,
                metrics=metrics,
            )

            wall_elapsed = perf_counter() - wall_start
            cpu_elapsed = process_time() - cpu_start

            cpu_elapsed += metrics.worker_cpu_seconds

            rss_samples.append(process.memory_info().rss)

            del index

        finally:
            stop.set()
            monitor_thread.join()

        wall_times.append(wall_elapsed)
        cpu_times.append(cpu_elapsed)
        rss_values.append(max(rss_samples) / (1024**2))
        merge_times.append(metrics.merge_seconds)

    return (
        median(wall_times),
        median(cpu_times),
        median(rss_values),
        median(merge_times),
    )


def main() -> None:
    cpu_count = os.cpu_count() or 1
    worker_counts = sorted({1, 2, 4, 8, cpu_count})
    gil_enabled = sys._is_gil_enabled()

    print(f"Python: {sys.version}")
    print(f"GIL enabled: {gil_enabled}")
    print(f"Logical CPUs: {cpu_count}")
    print("Repeats: 3")
    print()

    baseline = measure("serial", 1)

    rows: list[list[str | int | float]] = []

    print(
        f"{'Executor':<14}"
        f"{'Workers':>8}"
        f"{'Wall (s)':>12}"
        f"{'CPU (s)':>12}"
        f"{'RSS (MiB)':>12}"
        f"{'Merge (s)':>12}"
        f"{'Speedup':>10}"
    )

    print("-" * 80)

    configurations: list[tuple[ExecutorName, int]] = [("serial", 1)]

    for workers in worker_counts:
        configurations.append(("threads", workers))
        configurations.append(("processes", workers))

    for executor, workers in configurations:
        if executor == "serial":
            wall, cpu, rss, merge_time = baseline
        else:
            wall, cpu, rss, merge_time = measure(
                executor,
                workers,
            )

        speedup = baseline[0] / wall

        rows.append(
            [
                executor,
                workers,
                wall,
                cpu,
                rss,
                merge_time,
                speedup,
            ]
        )

        print(
            f"{executor:<14}"
            f"{workers:>8}"
            f"{wall:>12.6f}"
            f"{cpu:>12.6f}"
            f"{rss:>12.2f}"
            f"{merge_time:>12.6f}"
            f"{speedup:>10.3f}"
        )

    output = Path("benchmark_gil.csv" if gil_enabled else "benchmark_nogil.csv")

    with output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "executor",
                "workers",
                "wall_seconds",
                "cpu_seconds",
                "peak_rss_mib",
                "merge_seconds",
                "speedup",
            ]
        )

        writer.writerows(rows)

    print()
    print(f"Results saved: {output}")


if __name__ == "__main__":
    main()

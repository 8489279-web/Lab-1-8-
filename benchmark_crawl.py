import csv
import re
import subprocess
import sys
import time
from pathlib import Path

import psutil

results = []
output = Path("benchmarks/lab6")
output.mkdir(parents=True, exist_ok=True)

for concurrency in (1, 5, 20):
    print(f"\nTesting concurrency={concurrency}...")

    log_path = output / f"c{concurrency}.txt"

    command = [
        sys.executable,
        "-m",
        "findex.cli",
        "crawl",
        "http://127.0.0.1:8000",
        "--max-pages",
        "200",
        "--concurrency",
        str(concurrency),
        "--per-host",
        "5",
        "--min-delay",
        "0.01",
        "--out",
        str(output / f"crawl_c{concurrency}.jsonl"),
    ]

    peak_rss = 0

    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
        )

        monitored = psutil.Process(process.pid)

        while process.poll() is None:
            try:
                rss = sum(
                    p.memory_info().rss
                    for p in [monitored, *monitored.children(recursive=True)]
                    if p.is_running()
                )
                peak_rss = max(peak_rss, rss)
            except psutil.NoSuchProcess:
                break

            time.sleep(0.02)

        if process.wait() != 0:
            raise RuntimeError(f"Benchmark failed: {log_path}")

    text = log_path.read_text(encoding="utf-8")

    pages = int(re.findall(r"Pages fetched: (\d+)", text)[-1])
    wall = float(re.findall(r"Wall time: ([\d.]+)", text)[-1])
    speed = float(re.findall(r"Pages/s: ([\d.]+)", text)[-1])
    errors = int(re.findall(r"Errors: (\d+)", text)[-1])

    row = {
        "Concurrency": concurrency,
        "Pages": pages,
        "Wall(s)": wall,
        "Pages/s": speed,
        "Errors": errors,
        "Peak RSS (MiB)": round(peak_rss / 1024**2, 2),
    }

    results.append(row)
    print(row)

with (output / "results.csv").open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

print("\nBenchmark completed.")
print("Results: benchmarks/lab6/results.csv")

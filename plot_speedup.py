import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_results(filename: str) -> list[dict[str, str]]:
    with Path(filename).open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main() -> None:
    gil = read_results("benchmark_gil.csv")
    nogil = read_results("benchmark_nogil.csv")

    plt.figure(figsize=(10, 6))

    configurations = [
        (gil, "threads", "Threads with GIL"),
        (gil, "processes", "Processes with GIL"),
        (nogil, "threads", "Threads without GIL"),
        (nogil, "processes", "Processes without GIL"),
    ]

    for rows, executor, label in configurations:
        selected = [
            row for row in rows
            if row["executor"] == executor
        ]

        selected.sort(
            key=lambda row: int(row["workers"])
        )

        workers = [
            int(row["workers"])
            for row in selected
        ]

        speedup = [
            float(row["speedup"])
            for row in selected
        ]

        plt.plot(
            workers,
            speedup,
            marker="o",
            linewidth=2,
            label=label,
        )

    workers = sorted({
        int(row["workers"])
        for row in gil
    })

    plt.plot(
        workers,
        workers,
        linestyle="--",
        label="Ideal speedup",
    )

    plt.axhline(
        y=1,
        linestyle=":",
        label="Sequential baseline",
    )

    plt.title("Parallel indexing speedup")
    plt.xlabel("Number of workers")
    plt.ylabel("Speedup")
    plt.xticks(workers)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig("speedup.png", dpi=200)
    plt.close()

    print("Graph saved: speedup.png")


if __name__ == "__main__":
    main()

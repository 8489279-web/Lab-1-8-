import pickle
import tracemalloc
from array import array
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Literal

from findex.corpus import stream_corpus
from findex.index import Posting, build_index
from findex.search import EngineName, search


@dataclass
class PlainPosting:
    doc_id: int
    tf: int


Variant = Literal["plain", "slots", "array"]

PostingList = list[PlainPosting | Posting] | array[int]


def build_variant(
    directory: str | Path,
    variant: Variant,
) -> dict[str, PostingList]:

    postings: dict[str, PostingList] = {}

    for doc_id, _, tokens in stream_corpus(directory):
        counts = Counter(tokens)

        for term, tf in counts.items():
            if variant == "plain":
                items = postings.setdefault(term, [])

                if isinstance(items, list):
                    items.append(PlainPosting(doc_id, tf))

            elif variant == "slots":
                items = postings.setdefault(term, [])

                if isinstance(items, list):
                    items.append(Posting(doc_id, tf))

            else:
                items = postings.setdefault(term, array("I"))

                if isinstance(items, array):
                    items.extend([doc_id, tf])

    return postings


def benchmark_variant(variant: Variant) -> None:
    tracemalloc.start()

    postings = build_variant("data", variant)

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    filename = Path(f"benchmark_{variant}.bin")

    with filename.open("wb") as file:
        pickle.dump(postings, file)

    start = perf_counter()

    with filename.open("rb") as file:
        pickle.load(file)

    load_time = (perf_counter() - start) * 1000

    print(f"\nVariant: {variant}")
    print(f"Peak memory: {peak} bytes")
    print(f"File size: {filename.stat().st_size} bytes")
    print(f"Load time: {load_time:.3f} ms")

    filename.unlink()


def benchmark_search() -> None:
    index = build_index("data")

    queries = [
        "search AND python",
        "is AND a",
        "search OR python",
        "is OR a",
    ]

    engines: tuple[EngineName, ...] = (
        "merge",
        "set",
    )

    for query in queries:
        print(f"\nQuery: {query}")

        for engine in engines:
            start = perf_counter()

            for _ in range(1000):
                search(index, query, engine)

            elapsed = (perf_counter() - start) * 1000

            print(f"{engine}: {elapsed:.3f} ms")


def main() -> None:
    variants: tuple[Variant, ...] = (
        "plain",
        "slots",
        "array",
    )

    for variant in variants:
        benchmark_variant(variant)

    benchmark_search()


if __name__ == "__main__":
    main()

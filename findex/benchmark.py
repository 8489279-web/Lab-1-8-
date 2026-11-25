import pickle
import tracemalloc

from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass
from time import perf_counter
from pathlib import Path

from findex.corpus import stream_corpus
from findex.index import Posting


@dataclass
class PlainPosting:
    doc_id: int
    tf: int


def build_variant(directory, variant):
    postings = defaultdict(
        lambda: array("I") if variant == "array" else []
    )

    for doc_id, path, tokens in stream_corpus(directory):
        for term, tf in Counter(tokens).items():
            if variant == "plain":
                postings[term].append(
                    PlainPosting(doc_id, tf)
                )

            elif variant == "slots":
                postings[term].append(
                    Posting(doc_id, tf)
                )

            else:
                postings[term].extend([doc_id, tf])

    return dict(postings)


def benchmark(variant):
    tracemalloc.start()

    start = perf_counter()
    postings = build_variant("data", variant)
    build_time = perf_counter() - start

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    path = Path(f"benchmark_{variant}.bin")

    with path.open("wb") as f:
        pickle.dump(postings, f)

    start = perf_counter()

    with path.open("rb") as f:
        pickle.load(f)

    load_time = perf_counter() - start

    print(f"\nRepresentation: {variant}")
    print(f"Peak memory: {peak} bytes")
    print(f"File size: {path.stat().st_size} bytes")
    print(f"Build time: {build_time * 1000:.3f} ms")
    print(f"Load time: {load_time * 1000:.3f} ms")

def benchmark_search():
    from findex.index import build_index
    from findex.search import search

    index = build_index("data")

    terms = sorted(
        index.postings,
        key=lambda t: len(index.postings[t])
    )

    common = terms[-2:]
    rare = terms[:2]

    queries = [
        " AND ".join(common),
        " AND ".join(rare),
        " OR ".join(common),
        " OR ".join(rare)
    ]

    print("\nSearch benchmark:")

    for query in queries:
        print(f"\nQuery: {query}")

        assert search(index, query, "merge") == search(
            index, query, "set"
        )

        for engine in ("merge", "set"):
            start = perf_counter()

            for _ in range(1000):
                search(index, query, engine)

            elapsed = perf_counter() - start

            print(
                f"{engine}: {elapsed * 1000:.3f} ms"
            )

if __name__ == "__main__":
    for variant in ("plain", "slots", "array"):
        benchmark(variant)

    benchmark_search()
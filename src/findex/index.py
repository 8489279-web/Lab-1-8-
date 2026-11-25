import logging
from collections import Counter, defaultdict
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from functools import cached_property
from multiprocessing import get_context
from pathlib import Path
from time import perf_counter, process_time
from typing import Literal

from findex.corpus import corpus_paths, iter_documents, tokenize
from findex.utils import timed

ExecutorName = Literal["serial", "threads", "processes"]


@dataclass
class BuildMetrics:
    merge_seconds: float = 0.0
    worker_cpu_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class Posting:
    doc_id: int
    tf: int
    positions: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class DocMeta:
    path: str
    title: str


@dataclass
class Index:
    postings: dict[str, list[Posting]]
    doc_lengths: dict[int, int]
    doc_meta: dict[int, DocMeta]

    def __len__(self) -> int:
        return len(self.postings)

    def __contains__(self, term: str) -> bool:
        return term in self.postings

    def __getitem__(self, term: str) -> list[Posting]:
        return self.postings[term]

    def __iter__(self) -> Iterator[str]:
        return iter(self.postings)

    def __repr__(self) -> str:
        return f"Index(terms={len(self)}, docs={self.num_docs})"

    @property
    def num_docs(self) -> int:
        return len(self.doc_lengths)

    @cached_property
    def avg_doc_length(self) -> float:
        if not self.doc_lengths:
            return 0.0

        return sum(self.doc_lengths.values()) / self.num_docs

    def doc_length(self, doc_id: int) -> int:
        return self.doc_lengths[doc_id]

    def df(self, term: str) -> int:
        return len(self.postings.get(term, []))


def count_documents(path: Path) -> int:
    if path.suffix.lower() == ".txt":
        return 1

    with path.open(encoding="utf-8-sig") as file:
        return sum(1 for line in file if line.strip())


def build_partial(
    paths: list[Path],
    start_id: int = 1,
    with_positions: bool = False,
) -> Index:
    postings: dict[str, list[Posting]] = defaultdict(list)
    doc_lengths: dict[int, int] = {}
    doc_meta: dict[int, DocMeta] = {}

    documents = (document for path in paths for document in iter_documents(path))

    for doc_id, document in enumerate(
        documents,
        start=start_id,
    ):
        tokens = tokenize(document.text)
        counts = Counter(tokens)

        positions: dict[str, list[int]] = defaultdict(list)

        if with_positions:
            for position, term in enumerate(tokens):
                positions[term].append(position)

        doc_lengths[doc_id] = len(tokens)

        doc_meta[doc_id] = DocMeta(
            document.path,
            document.title,
        )

        for term, tf in counts.items():
            postings[term].append(
                Posting(
                    doc_id,
                    tf,
                    tuple(positions[term]),
                )
            )

    return Index(
        dict(postings),
        doc_lengths,
        doc_meta,
    )


def build_partial_measured(
    paths: list[Path],
    start_id: int,
    with_positions: bool,
) -> tuple[Index, float]:
    start = process_time()

    index = build_partial(
        paths,
        start_id,
        with_positions,
    )

    return index, process_time() - start


@timed
def merge(partials: list[Index]) -> Index:
    postings: dict[str, list[Posting]] = defaultdict(list)
    doc_lengths: dict[int, int] = {}
    doc_meta: dict[int, DocMeta] = {}

    for partial in partials:
        doc_lengths.update(partial.doc_lengths)
        doc_meta.update(partial.doc_meta)

        for term, items in partial.postings.items():
            postings[term].extend(items)

    for items in postings.values():
        items.sort(key=lambda p: p.doc_id)

    return Index(
        dict(postings),
        doc_lengths,
        doc_meta,
    )


@timed
def build_index(
    directory: str | Path,
    with_positions: bool = False,
    workers: int = 1,
    executor: ExecutorName = "serial",
    metrics: BuildMetrics | None = None,
) -> Index:
    if workers < 1:
        raise ValueError("Workers must be at least 1")

    if metrics is not None:
        metrics.merge_seconds = 0.0
        metrics.worker_cpu_seconds = 0.0

    paths = corpus_paths(directory)

    if not paths:
        return Index({}, {}, {})

    partials: list[Index] = []

    if executor == "serial":
        partials.append(build_partial(paths, 1, with_positions))

    else:
        workers = min(workers, len(paths))
        chunk_size = (len(paths) + workers - 1) // workers

        chunks: list[tuple[list[Path], int]] = []

        next_id = 1

        for i in range(0, len(paths), chunk_size):
            chunk = paths[i : i + chunk_size]

            chunks.append((chunk, next_id))

            next_id += sum(count_documents(path) for path in chunk)

        try:
            if executor == "threads":
                with ThreadPoolExecutor(
                    max_workers=workers,
                ) as pool:
                    futures = [
                        pool.submit(
                            build_partial,
                            chunk,
                            start_id,
                            with_positions,
                        )
                        for chunk, start_id in chunks
                    ]

                    partials = [future.result() for future in futures]

            elif executor == "processes":
                with ProcessPoolExecutor(
                    max_workers=workers,
                    mp_context=get_context("spawn"),
                ) as process_pool:
                    process_futures = [
                        process_pool.submit(
                            build_partial_measured,
                            chunk,
                            start_id,
                            with_positions,
                        )
                        for chunk, start_id in chunks
                    ]

                    for future in process_futures:
                        partial, cpu_seconds = future.result()
                        partials.append(partial)

                        if metrics is not None:
                            metrics.worker_cpu_seconds += cpu_seconds

            else:
                raise ValueError("Unknown executor")

        except Exception:
            logging.getLogger(__name__).exception("Index worker failed")
            raise

    merge_start = perf_counter()

    result = merge(partials)

    if metrics is not None:
        metrics.merge_seconds = perf_counter() - merge_start

    return result


def main() -> None:
    import argparse
    import tracemalloc

    from findex.index import build_index
    from findex.store import save

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "directory",
        nargs="?",
        default="data",
    )

    parser.add_argument(
        "--out",
        default="index.bin",
    )

    parser.add_argument(
        "--positions",
        action="store_true",
    )

    args = parser.parse_args()

    tracemalloc.start()
    start = perf_counter()

    index = build_index(
        args.directory,
        args.positions,
    )

    elapsed = perf_counter() - start

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    save(index, args.out)

    print("Documents:", index.num_docs)
    print("Terms:", len(index))
    print("Average document length:", index.avg_doc_length)
    print(f"Elapsed time: {elapsed:.6f} s")
    print(f"Peak memory: {peak} bytes")
    print("Index saved:", args.out)


if __name__ == "__main__":
    main()

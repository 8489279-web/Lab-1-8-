
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from findex.corpus import stream_corpus
from findex.utils import timed


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
        return (
            f"Index(terms={len(self)}, "
            f"docs={self.num_docs})"
        )

    @property
    def num_docs(self) -> int:
        return len(self.doc_lengths)

    @cached_property
    def avg_doc_length(self) -> float:
        if not self.doc_lengths:
            return 0.0

        return (
            sum(self.doc_lengths.values())
            / self.num_docs
        )

    def doc_length(self, doc_id: int) -> int:
        return self.doc_lengths[doc_id]

    def df(self, term: str) -> int:
        return len(self.postings.get(term, []))


@timed
def build_index(
    directory: str | Path,
    with_positions: bool = False,
) -> Index:
    postings: dict[str, list[Posting]] = defaultdict(list)
    doc_lengths: dict[int, int] = {}
    doc_meta: dict[int, DocMeta] = {}

    for doc_id, path, tokens in stream_corpus(directory):
        counts = Counter(tokens)

        positions: dict[int | str, list[int]] = defaultdict(list)

        if with_positions:
            for position, term in enumerate(tokens):
                positions[term].append(position)

        doc_lengths[doc_id] = len(tokens)

        doc_meta[doc_id] = DocMeta(
            str(path),
            path.stem,
        )

        for term, tf in counts.items():
            postings[term].append(
                Posting(
                    doc_id,
                    tf,
                    tuple(positions[term]),
                )
            )

    for items in postings.values():
        items.sort(key=lambda p: p.doc_id)

    return Index(
        dict(postings),
        doc_lengths,
        doc_meta,
    )


def main() -> None:
    import argparse
    import tracemalloc
    from time import perf_counter

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

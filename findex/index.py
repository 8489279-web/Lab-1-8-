from findex.utils import timed

from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import cached_property
from findex.corpus import stream_corpus


@dataclass(frozen=True, slots=True)
class Posting:
    doc_id: int
    tf: int
    positions: tuple = ()


@dataclass(frozen=True, slots=True)
class DocMeta:
    path: str
    title: str


@dataclass
class Index:
    postings: dict
    doc_lengths: dict
    doc_meta: dict

    def __len__(self):
        return len(self.postings)

    def __contains__(self, term):
        return term in self.postings

    def __getitem__(self, term):
        return self.postings[term]

    def __iter__(self):
        return iter(self.postings)

    def __repr__(self):
        return f"Index(terms={len(self)}, docs={self.num_docs})"

    @property
    def num_docs(self):
        return len(self.doc_lengths)

    @cached_property
    def avg_doc_length(self):
        if not self.doc_lengths:
            return 0.0
        return sum(self.doc_lengths.values()) / self.num_docs

    def doc_length(self, doc_id):
        return self.doc_lengths[doc_id]

    def df(self, term):
        return len(self.postings.get(term, []))


@timed
def build_index(directory, with_positions=False):
    postings = defaultdict(list)
    doc_lengths = {}
    doc_meta = {}

    for doc_id, path, tokens in stream_corpus(directory):
        counts = Counter(tokens)
        positions = defaultdict(list)

        if with_positions:
            for position, term in enumerate(tokens):
                positions[term].append(position)

        doc_lengths[doc_id] = len(tokens)
        doc_meta[doc_id] = DocMeta(str(path), path.stem)

        for term, tf in counts.items():
            postings[term].append(
                Posting(
                    doc_id,
                    tf,
                    tuple(positions[term])
                )
            )

    for items in postings.values():
        items.sort(key=lambda p: p.doc_id)

    return Index(dict(postings), doc_lengths, doc_meta)


def main():
    import argparse
    import tracemalloc
    from time import perf_counter
    from findex.store import save
    from findex.index import build_index

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="data")
    parser.add_argument("--out", default="index.bin")
    parser.add_argument("--positions", action="store_true")
    args = parser.parse_args()

    tracemalloc.start()
    start = perf_counter()

    index = build_index(
        args.directory,
        with_positions=args.positions
    )

    save(index, args.out)

    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Documents: {len(index.doc_meta)}")
    print(f"Unique terms: {len(index.postings)}")
    print(f"Positions enabled: {args.positions}")
    print(f"Index saved: {args.out}")
    print(f"Elapsed time: {elapsed:.3f} s")
    print(f"Peak memory: {peak} bytes")


if __name__ == "__main__":
    main()

from collections import Counter, defaultdict
from dataclasses import dataclass
from findex.corpus import stream_corpus


@dataclass(frozen=True, slots=True)
class Posting:
    doc_id: int
    tf: int


@dataclass(frozen=True, slots=True)
class DocMeta:
    path: str
    title: str


@dataclass
class Index:
    postings: dict
    doc_lengths: dict
    doc_meta: dict


def build_index(directory):
    postings = defaultdict(list)
    doc_lengths = {}
    doc_meta = {}

    for doc_id, path, tokens in stream_corpus(directory):
        counts = Counter(tokens)

        doc_lengths[doc_id] = len(tokens)
        doc_meta[doc_id] = DocMeta(str(path), path.stem)

        for term, tf in counts.items():
            postings[term].append(Posting(doc_id, tf))

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
    args = parser.parse_args()

    tracemalloc.start()
    start = perf_counter()

    index = build_index(args.directory)
    save(index, args.out)

    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Documents: {len(index.doc_meta)}")
    print(f"Unique terms: {len(index.postings)}")
    print(f"Index saved: {args.out}")
    print(f"Elapsed time: {elapsed:.3f} s")
    print(f"Peak memory: {peak} bytes")


if __name__ == "__main__":
    main()
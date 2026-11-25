from findex.utils import timed

import pickle
import json
from pathlib import Path
from dataclasses import asdict
from time import perf_counter
from contextlib import contextmanager

from findex.index import Index, Posting, DocMeta, build_index


def save(index, path):
    path = Path(path)

    if path.suffix == ".json":
        data = {
            "postings": {
                term: [asdict(p) for p in items]
                for term, items in index.postings.items()
            },
            "doc_lengths": index.doc_lengths,
            "doc_meta": {
                doc_id: asdict(meta)
                for doc_id, meta in index.doc_meta.items()
            }
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    else:
        with path.open("wb") as f:
            pickle.dump(index, f)


@timed
def load(path):
    path = Path(path)

    if path.suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return Index(
            postings={
                term: [
                    Posting(
                        doc_id=p["doc_id"],
                        tf=p["tf"],
                        positions=tuple(p.get("positions", []))
                    )
                    for p in items
                ]
                for term, items in data["postings"].items()
            },
            doc_lengths={
                int(k): v
                for k, v in data["doc_lengths"].items()
            },
            doc_meta={
                int(k): DocMeta(**v)
                for k, v in data["doc_meta"].items()
            }
        )

    # Never load untrusted pickle files:
    # they can execute arbitrary code.
    with path.open("rb") as f:
        return pickle.load(f)


@contextmanager
def open_index(path):
    index = load(path)
    try:
        yield index
    finally:
        del index


if __name__ == "__main__":
    index = build_index("data", with_positions=True)

    for filename in ("index.bin", "index.json"):
        start = perf_counter()
        save(index, filename)
        save_time = perf_counter() - start

        start = perf_counter()
        loaded = load(filename)
        load_time = perf_counter() - start

        print(f"\nFormat: {filename}")
        print(f"File size: {Path(filename).stat().st_size} bytes")
        print(f"Save time: {save_time * 1000:.3f} ms")
        print(f"Load time: {load_time * 1000:.3f} ms")
        print(f"Documents: {len(loaded.doc_meta)}")
        print(f"Unique terms: {len(loaded.postings)}")
        print(f"Verification: {index == loaded}")

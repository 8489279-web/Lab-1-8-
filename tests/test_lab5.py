from collections import Counter, defaultdict
from pathlib import Path

import pytest

from findex.corpus import tokenize
from findex.index import (
    BuildMetrics,
    DocMeta,
    ExecutorName,
    Index,
    Posting,
    build_index,
    build_partial,
    merge,
)


def test_legacy_index_equivalence(
    tiny_corpus: Path,
) -> None:
    postings: dict[str, list[Posting]] = defaultdict(list)
    lengths: dict[int, int] = {}
    metadata: dict[int, DocMeta] = {}

    paths = sorted(tiny_corpus.rglob("*.txt"))

    for doc_id, path in enumerate(paths, start=1):
        tokens = tokenize(path.read_text(encoding="utf-8-sig"))

        lengths[doc_id] = len(tokens)
        metadata[doc_id] = DocMeta(str(path), path.stem)

        for term, count in Counter(tokens).items():
            positions = tuple(i for i, token in enumerate(tokens) if token == term)

            postings[term].append(Posting(doc_id, count, positions))

    expected = Index(
        dict(postings),
        lengths,
        metadata,
    )

    actual = merge([build_partial(paths, 1, True)])

    assert actual == expected


@pytest.mark.parametrize(
    "executor",
    ["threads", "processes"],
)
def test_worker_failure(
    tmp_path: Path,
    executor: ExecutorName,
) -> None:
    (tmp_path / "invalid.txt").write_bytes(b"\xff\xfe\xff")

    with pytest.raises(UnicodeDecodeError):
        build_index(
            tmp_path,
            workers=2,
            executor=executor,
        )


@pytest.mark.parametrize(
    "executor",
    ["serial", "threads", "processes"],
)
def test_build_metrics(
    tiny_corpus: Path,
    executor: ExecutorName,
) -> None:
    metrics = BuildMetrics()

    index = build_index(
        tiny_corpus,
        workers=2,
        executor=executor,
        metrics=metrics,
    )

    assert index.num_docs > 0
    assert metrics.merge_seconds > 0
    assert metrics.worker_cpu_seconds >= 0

    if executor != "processes":
        assert metrics.worker_cpu_seconds == 0

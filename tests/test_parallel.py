from pathlib import Path

import pytest

from findex.index import ExecutorName, build_index, build_partial, merge


@pytest.mark.parametrize("executor", ["threads", "processes"])
@pytest.mark.parametrize("workers", [1, 2, 4, 8])
@pytest.mark.parametrize("with_positions", [False, True])
def test_parallel_equivalence(
    tiny_corpus: Path,
    executor: ExecutorName,
    workers: int,
    with_positions: bool,
) -> None:
    expected = build_index(
        tiny_corpus,
        with_positions=with_positions,
    )

    actual = build_index(
        tiny_corpus,
        with_positions=with_positions,
        workers=workers,
        executor=executor,
    )

    assert actual == expected


@pytest.mark.parametrize(
    "executor",
    ["serial", "threads", "processes"],
)
def test_empty_corpus(
    tmp_path: Path,
    executor: ExecutorName,
) -> None:
    index = build_index(
        tmp_path,
        workers=2,
        executor=executor,
    )

    assert index.num_docs == 0
    assert len(index) == 0


@pytest.mark.parametrize("workers", [0, -1])
def test_invalid_workers(
    tiny_corpus: Path,
    workers: int,
) -> None:
    with pytest.raises(ValueError):
        build_index(tiny_corpus, workers=workers)


def test_merge_partials(tiny_corpus: Path) -> None:
    paths = sorted(tiny_corpus.rglob("*.txt"))

    first = build_partial(
        paths[:2],
        start_id=1,
        with_positions=True,
    )

    second = build_partial(
        paths[2:],
        start_id=3,
        with_positions=True,
    )

    actual = merge([second, first])
    expected = build_index(
        tiny_corpus,
        with_positions=True,
    )

    assert actual == expected


def test_merge_empty() -> None:
    index = merge([])

    assert index.num_docs == 0
    assert len(index) == 0

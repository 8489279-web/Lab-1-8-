import pytest

from findex.index import Index
from findex.search import (
    EngineName,
    merge_and,
    merge_not,
    merge_or,
    search,
)


def test_merge_and() -> None:
    assert merge_and([1, 2, 4], [2, 3, 4]) == [2, 4]


def test_merge_or() -> None:
    assert merge_or([1, 2, 4], [2, 3, 4]) == [1, 2, 3, 4]


def test_merge_not() -> None:
    assert merge_not([1, 2, 4], [2, 3, 4]) == [1]


def test_merge_and_empty() -> None:
    assert merge_and([], [1, 2]) == []


def test_merge_or_empty() -> None:
    assert merge_or([], [1, 2]) == [1, 2]


def test_merge_not_empty() -> None:
    assert merge_not([1, 2], []) == [1, 2]


@pytest.mark.parametrize("engine", ["merge", "set"])
@pytest.mark.parametrize(
    "query, expected",
    [
        ("python", [1, 2, 4]),
        ("python AND search", [4]),
        ("python OR search", [1, 2, 3, 4]),
        ("NOT python", [3, 5]),
        ("python NOT search", [1, 2]),
        ("python search", [4]),
        ("unknownword", []),
        ("", []),
    ],
)
def test_boolean_search(
    tiny_index: Index,
    engine: EngineName,
    query: str,
    expected: list[int],
) -> None:
    assert search(tiny_index, query, engine) == expected


def test_engines_equivalent(tiny_index: Index) -> None:
    query = "python OR search"

    assert search(tiny_index, query, "merge") == search(
        tiny_index, query, "set"
    )


def test_invalid_query(tiny_index: Index) -> None:
    with pytest.raises(ValueError):
        search(tiny_index, "python AND")

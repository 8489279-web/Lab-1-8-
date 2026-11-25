from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from findex.index import build_index
from findex.search import merge_and, merge_not, merge_or
from findex.store import load, save

documents = st.lists(
    st.lists(
        st.sampled_from(["python", "search", "index", "data", "engine"]),
        min_size=0,
        max_size=30,
    ),
    min_size=1,
    max_size=10,
)


def create_corpus(
    directory: Path,
    texts: list[list[str]],
) -> None:
    for i, words in enumerate(texts):
        path = directory / f"doc{i:03d}.txt"
        path.write_text(" ".join(words), encoding="utf-8")


@pytest.mark.slow
@settings(max_examples=50, deadline=None)
@given(texts=documents)
def test_index_roundtrip(texts: list[list[str]]) -> None:
    with TemporaryDirectory() as directory:
        path = Path(directory)
        create_corpus(path, texts)

        index = build_index(path, with_positions=True)

        for extension in (".bin", ".json"):
            filename = path / ("index" + extension)
            save(index, filename)

            assert load(filename) == index


@pytest.mark.slow
@settings(max_examples=50, deadline=None)
@given(texts=documents)
def test_postings_are_sorted(texts: list[list[str]]) -> None:
    with TemporaryDirectory() as directory:
        path = Path(directory)
        create_corpus(path, texts)

        index = build_index(path, with_positions=True)

        for postings in index.postings.values():
            ids = [posting.doc_id for posting in postings]

            assert ids == sorted(set(ids))


@given(
    a=st.sets(st.integers(min_value=0, max_value=1000)),
    b=st.sets(st.integers(min_value=0, max_value=1000)),
)
def test_merge_matches_sets(
    a: set[int],
    b: set[int],
) -> None:
    left = sorted(a)
    right = sorted(b)

    assert merge_and(left, right) == sorted(a & b)
    assert merge_or(left, right) == sorted(a | b)
    assert merge_not(left, right) == sorted(a - b)

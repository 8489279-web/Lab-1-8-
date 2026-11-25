import pytest

from findex.index import build_index
from findex.numpy_index import NumpyIndex
from findex.numpy_scoring import numpy_search


@pytest.fixture
def corpus(tmp_path):
    for i in range(100):
        path = tmp_path / f"doc{i}.txt"

        path.write_text(
            f"python asyncio search document {i}",
            encoding="utf-8",
        )

    return tmp_path


def test_benchmark_build_index(benchmark, corpus):
    benchmark(build_index, corpus)


def test_benchmark_search(benchmark, corpus):
    index = build_index(corpus)
    arrays = NumpyIndex.from_index(index)

    benchmark(
        numpy_search,
        index,
        arrays,
        "python asyncio search",
    )

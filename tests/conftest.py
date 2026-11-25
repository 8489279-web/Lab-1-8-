
from pathlib import Path

import pytest

from findex.index import Index, build_index


@pytest.fixture
def tiny_corpus(tmp_path: Path) -> Path:
    documents = {
        "doc1.txt": "Python is a programming language.",
        "doc2.txt": "Python supports dictionaries and sets.",
        "doc3.txt": "Search engines use an inverted index.",
        "doc4.txt": "Python Python search engine.",
        "doc5.txt": "Українська мова та програмування.",
    }

    for filename, content in documents.items():
        path = tmp_path / filename
        path.write_text(content, encoding="utf-8")

    return tmp_path


@pytest.fixture
def tiny_index(tiny_corpus: Path) -> Index:
    return build_index(
        tiny_corpus,
        with_positions=True,
    )

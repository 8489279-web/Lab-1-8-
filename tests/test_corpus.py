from pathlib import Path

import pytest

from findex.corpus import stream_corpus, tokenize


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello World", ["hello", "world"]),
        ("PYTHON Python python", ["python", "python", "python"]),
        ("Hello, world!", ["hello", "world"]),
        ("", []),
        ("   ", []),
        ("123 456", ["123", "456"]),
        ("hello_world", ["hello_world"]),
        (
            "\u041f\u0440\u0438\u0432\u0456\u0442, \u0441\u0432\u0456\u0442\u0435!",
            [
                "\u043f\u0440\u0438\u0432\u0456\u0442",
                "\u0441\u0432\u0456\u0442\u0435",
            ],
        ),
        (
            "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430 \u041c\u041e\u0412\u0410",
            [
                "\u0443\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430",
                "\u043c\u043e\u0432\u0430",
            ],
        ),
        (
            "\u3053\u3093\u306b\u3061\u306f \u4e16\u754c",
            ["\u3053\u3093\u306b\u3061\u306f", "\u4e16\u754c"],
        ),
        ("Python\nJava\tRust", ["python", "java", "rust"]),
        ("!@#$%", []),
    ],
)
def test_tokenize(text: str, expected: list[str]) -> None:
    assert tokenize(text) == expected


def test_stream_corpus_count(tiny_corpus: Path) -> None:
    documents = list(stream_corpus(tiny_corpus))
    assert len(documents) == 5


def test_stream_corpus_ids(tiny_corpus: Path) -> None:
    documents = list(stream_corpus(tiny_corpus))
    ids = [doc_id for doc_id, _, _ in documents]
    assert ids == [1, 2, 3, 4, 5]


def test_stream_corpus_tokens(tiny_corpus: Path) -> None:
    documents = list(stream_corpus(tiny_corpus))
    assert documents[0][2] == [
        "python",
        "is",
        "a",
        "programming",
        "language",
    ]


def test_stream_empty_corpus(tmp_path: Path) -> None:
    assert list(stream_corpus(tmp_path)) == []

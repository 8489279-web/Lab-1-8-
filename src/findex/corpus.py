
import re
from collections.abc import Iterator
from pathlib import Path


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def stream_corpus(
    directory: str | Path,
) -> Iterator[tuple[int, Path, list[str]]]:
    for doc_id, path in enumerate(
        sorted(Path(directory).rglob("*.txt")), start=1
    ):
        text = path.read_text(encoding="utf-8-sig")

        yield doc_id, path, tokenize(text)


if __name__ == "__main__":
    for doc_id, path, tokens in stream_corpus("data"):
        print(doc_id, path.name, tokens)

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True, slots=True)
class Document:
    path: str
    title: str
    text: str


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def corpus_paths(source: str | Path) -> list[Path]:
    path = Path(source)

    if path.is_file():
        if path.suffix.lower() in (".txt", ".jsonl"):
            return [path]

        raise ValueError("Unsupported file format")

    return sorted(
        item
        for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() in (".txt", ".jsonl")
    )


def iter_documents(
    source: str | Path,
) -> Iterator[Document]:
    for path in corpus_paths(source):
        if path.suffix.lower() == ".txt":
            yield Document(
                path=str(path),
                title=path.stem,
                text=path.read_text(encoding="utf-8-sig"),
            )
            continue

        with path.open(
            encoding="utf-8-sig",
        ) as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue

                raw: object = json.loads(line)

                if not isinstance(raw, dict):
                    raise TypeError(f"Invalid JSONL record: {path}:{line_number}")

                record = cast(dict[str, object], raw)

                url = record.get("url")
                title = record.get("title")
                text = record.get("text")

                if not (
                    isinstance(url, str)
                    and isinstance(title, str)
                    and isinstance(text, str)
                ):
                    raise TypeError(f"Invalid document: {path}:{line_number}")

                yield Document(
                    path=url,
                    title=title or url,
                    text=text,
                )


def stream_corpus(
    directory: str | Path,
) -> Iterator[tuple[int, Path, list[str]]]:
    for doc_id, path in enumerate(
        sorted(Path(directory).rglob("*.txt")),
        start=1,
    ):
        text = path.read_text(encoding="utf-8-sig")

        yield doc_id, path, tokenize(text)


if __name__ == "__main__":
    for doc_id, path, tokens in stream_corpus("data"):
        print(doc_id, path.name, tokens)

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from findex.corpus import iter_documents
from findex.index import Index
from findex.scoring import SearchResult


def chunk_document(
    text: str,
    tokenizer: object,
    chunk_size: int = 220,
    overlap: int = 40,
) -> list[str]:
    tokens = tokenizer.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]

    if not tokens:
        return []

    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(tokens), step):
        chunk = tokenizer.decode(
            tokens[start : start + chunk_size],
            skip_special_tokens=True,
        )

        if chunk.strip():
            chunks.append(chunk)

        if start + chunk_size >= len(tokens):
            break

    return chunks


def build_semantic_index(
    corpus_dir: str | Path,
    output_dir: str | Path = "docs/semantic",
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(model_name)
    tokenizer = model.tokenizer

    texts: list[str] = []
    doc_ids: list[int] = []

    for doc_id, document in enumerate(
        iter_documents(corpus_dir),
        start=1,
    ):
        chunks = chunk_document(
            document.text,
            tokenizer,
        )

        for chunk in chunks:
            texts.append(
                f"{document.title}\n{chunk}"
            )
            doc_ids.append(doc_id)

    if not texts:
        raise ValueError("No document chunks found")

    embeddings: NDArray[np.float32] = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    np.save(output / "embeddings.npy", embeddings)

    np.save(
        output / "chunk_doc_ids.npy",
        np.asarray(doc_ids, dtype=np.int32),
    )

    metadata = {
        "model": model_name,
        "chunks": len(texts),
        "documents": len(set(doc_ids)),
        "dimensions": int(embeddings.shape[1]),
    }

    (output / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


class SemanticSearcher:
    def __init__(
        self,
        index: Index,
        directory: str | Path = "docs/semantic",
    ) -> None:
        directory = Path(directory)

        self.index = index
        self.embeddings = np.load(
            directory / "embeddings.npy"
        )
        self.doc_ids = np.load(
            directory / "chunk_doc_ids.npy"
        )

        metadata = json.loads(
            (directory / "metadata.json").read_text(
                encoding="utf-8"
            )
        )

        self.model = SentenceTransformer(
            metadata["model"]
        )

    def search(
        self,
        query: str,
        k: int = 10,
    ) -> list[SearchResult]:
        if not query.strip() or k <= 0:
            return []

        query_vector = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

        similarities = self.embeddings @ query_vector

        best_scores: dict[int, float] = {}

        for doc_id, score in zip(
            self.doc_ids.tolist(),
            similarities.tolist(),
            strict=True,
        ):
            best_scores[doc_id] = max(
                best_scores.get(doc_id, -1.0),
                score,
            )

        ordered = sorted(
            best_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )

        return [
            SearchResult(
                doc_id=doc_id,
                score=score,
                title=self.index.doc_meta[doc_id].title,
            )
            for doc_id, score in ordered[:k]
        ]
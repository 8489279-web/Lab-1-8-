import math
from typing import Literal

import numpy as np

from findex.index import Index
from findex.numpy_index import NumpyIndex
from findex.query import parse
from findex.ranking import positive_terms
from findex.scoring import SearchResult


def numpy_search(
    index: Index,
    arrays: NumpyIndex,
    query: str,
    scorer: Literal["bm25", "tfidf"] = "bm25",
    k: int = 10,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[SearchResult]:
    if not query.strip() or k <= 0:
        return []

    tree = parse(query)

    candidates = np.array(
        sorted(tree.evaluate(index)),
        dtype=np.int32,
    )

    if candidates.size == 0:
        return []

    scores = np.zeros(
        arrays.doc_lengths.size,
        dtype=np.float64,
    )

    for term in positive_terms(tree):
        posting = arrays.postings.get(term)

        if posting is None:
            continue

        ids = posting.doc_ids
        tfs = posting.tfs.astype(np.float64)
        df = ids.size
        n = arrays.num_docs

        if df == 0 or n == 0:
            continue

        if scorer == "tfidf":
            values = tfs * math.log(n / df)

        else:
            avgdl = arrays.avg_doc_length

            if avgdl == 0:
                continue

            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))

            lengths = arrays.doc_lengths[ids]

            norm = k1 * (1 - b + b * lengths / avgdl)

            values = idf * (tfs * (k1 + 1)) / (tfs + norm)

        scores[ids] += values

    candidate_scores = scores[candidates]
    count = min(k, candidates.size)

    if count < candidates.size:
        partition = np.argpartition(
            candidate_scores,
            -count,
        )[-count:]

        threshold = candidate_scores[partition].min()

        selected = candidates[candidate_scores >= threshold]
    else:
        selected = candidates

    order = np.lexsort((selected, -scores[selected]))

    selected = selected[order][:count]

    return [
        SearchResult(
            doc_id=int(doc_id),
            score=float(scores[doc_id]),
            title=index.doc_meta[int(doc_id)].title,
        )
        for doc_id in selected
    ]

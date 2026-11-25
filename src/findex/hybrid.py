from findex.index import Index
from findex.ranking import search as keyword_search
from findex.scoring import BM25, Scorer, SearchResult
from findex.semantic import SemanticSearcher


def hybrid_search(
    index: Index,
    semantic: SemanticSearcher,
    query: str,
    scorer: Scorer | None = None,
    k: int = 10,
    rrf_k: int = 60,
    candidate_k: int = 50,
) -> list[SearchResult]:
    if not query.strip() or k <= 0:
        return []

    if scorer is None:
        scorer = BM25()

    keyword_results = keyword_search(
        index,
        query,
        scorer,
        candidate_k,
    )

    semantic_results = semantic.search(
        query,
        candidate_k,
    )

    scores: dict[int, float] = {}

    for results in (
        keyword_results,
        semantic_results,
    ):
        for rank, result in enumerate(results, start=1):
            scores[result.doc_id] = (
                scores.get(result.doc_id, 0.0)
                + 1.0 / (rrf_k + rank)
            )

    ordered = sorted(
        scores.items(),
        key=lambda item: (-item[1], item[0]),
    )

    return [
        SearchResult(
            doc_id=doc_id,
            score=score,
            title=index.doc_meta[doc_id].title,
        )
        for doc_id, score in ordered[:k]
    ]
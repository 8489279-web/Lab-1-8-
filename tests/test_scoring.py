import pytest

from findex.index import DocMeta, Index, Posting
from findex.ranking import search
from findex.scoring import BM25, TfIdf, get_scorer


@pytest.mark.parametrize("scorer", [TfIdf(), BM25()])
def test_rare_term_score(tiny_index: Index, scorer) -> None:
    rare = tiny_index["programming"][0]
    common = tiny_index["python"][0]

    assert scorer.score("programming", rare, tiny_index) > (
        scorer.score("python", common, tiny_index)
    )


@pytest.mark.parametrize("scorer", [TfIdf(), BM25()])
def test_unknown_term(tiny_index: Index, scorer) -> None:
    assert scorer.score(
        "unknownword", Posting(1, 1), tiny_index
    ) == 0.0


@pytest.mark.parametrize("scorer", [TfIdf(), BM25()])
def test_frequency_increases_score(tiny_index: Index, scorer) -> None:
    low = Posting(1, 1)
    high = Posting(1, 2)

    assert scorer.score("python", high, tiny_index) > (
        scorer.score("python", low, tiny_index)
    )


def test_bm25_saturation(tiny_index: Index) -> None:
    scorer = BM25()

    def score(tf: int) -> float:
        return scorer.score("python", Posting(1, tf), tiny_index)

    assert score(2) - score(1) > score(20) - score(19)


def test_bm25_document_length() -> None:
    index = Index(
        postings={
            "python": [Posting(1, 1), Posting(2, 1)]
        },
        doc_lengths={1: 10, 2: 100},
        doc_meta={
            1: DocMeta("short.txt", "short"),
            2: DocMeta("long.txt", "long"),
        },
    )

    scorer = BM25()

    assert scorer.score("python", Posting(1, 1), index) > (
        scorer.score("python", Posting(2, 1), index)
    )


@pytest.mark.parametrize("scorer", [TfIdf(), BM25()])
def test_ranking_order(tiny_index: Index, scorer) -> None:
    results = search(tiny_index, "python", scorer)
    scores = [result.score for result in results]

    assert scores == sorted(scores, reverse=True)
    assert results[0].doc_id == 4


def test_top_k(tiny_index: Index) -> None:
    results = search(tiny_index, "python", BM25(), k=2)
    assert len(results) == 2


def test_empty_query(tiny_index: Index) -> None:
    assert search(tiny_index, "") == []


def test_no_results(tiny_index: Index) -> None:
    assert search(tiny_index, "unknownword") == []


def test_get_tfidf() -> None:
    assert isinstance(get_scorer("tfidf"), TfIdf)


def test_get_bm25() -> None:
    assert isinstance(get_scorer("bm25"), BM25)

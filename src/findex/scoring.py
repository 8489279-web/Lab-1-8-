
import math
from dataclasses import dataclass, field
from typing import Literal, Protocol

from findex.index import Index, Posting

ScorerName = Literal["tfidf", "bm25"]


class Scorer(Protocol):
    def score(
        self,
        term: str,
        posting: Posting,
        index: Index,
    ) -> float:
        ...


class TfIdf:
    def score(
        self,
        term: str,
        posting: Posting,
        index: Index,
    ) -> float:
        df = index.df(term)

        if df == 0 or index.num_docs == 0:
            return 0.0

        return posting.tf * math.log(
            index.num_docs / df
        )


class BM25:
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b

    def score(
        self,
        term: str,
        posting: Posting,
        index: Index,
    ) -> float:
        df = index.df(term)
        n = index.num_docs

        if df == 0 or n == 0:
            return 0.0

        avgdl = index.avg_doc_length

        if avgdl == 0:
            return 0.0

        dl = index.doc_length(posting.doc_id)
        tf = posting.tf

        idf = math.log(
            1 + (n - df + 0.5) / (df + 0.5)
        )

        numerator = tf * (self.k1 + 1)

        denominator = tf + self.k1 * (
            1 - self.b + self.b * dl / avgdl
        )

        return idf * numerator / denominator


@dataclass(order=True)
class SearchResult:
    doc_id: int = field(compare=False)
    score: float
    title: str = field(compare=False)


def check_scorers() -> tuple[Scorer, Scorer]:
    tfidf: Scorer = TfIdf()
    bm25: Scorer = BM25()

    return tfidf, bm25


def get_scorer(name: ScorerName) -> Scorer:
    if name == "tfidf":
        return TfIdf()

    return BM25()

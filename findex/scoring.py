
from math import log
from typing import Protocol
from dataclasses import dataclass, field

from findex.index import Index, Posting


class Scorer(Protocol):
    def score(
        self, term: str, posting: Posting, index: Index
    ) -> float:
        ...


class TfIdf:
    def score(self, term, posting, index):
        df = index.df(term)

        if df == 0 or index.num_docs == 0:
            return 0.0

        tf = 1 + log(posting.tf)
        idf = log(index.num_docs / df)

        return tf * idf

    def __call__(self, term, posting, index):
        return self.score(term, posting, index)


@dataclass
class BM25:
    k1: float = 1.5
    b: float = 0.75

    def score(self, term, posting, index):
        df = index.df(term)
        n = index.num_docs

        if df == 0 or index.avg_doc_length == 0:
            return 0.0

        tf = posting.tf
        dl = index.doc_length(posting.doc_id)
        avgdl = index.avg_doc_length

        idf = log(1 + (n - df + 0.5) / (df + 0.5))

        numerator = tf * (self.k1 + 1)

        denominator = tf + self.k1 * (
            1 - self.b + self.b * dl / avgdl
        )

        return idf * numerator / denominator

    def __call__(self, term, posting, index):
        return self.score(term, posting, index)


@dataclass(order=True)
class SearchResult:
    doc_id: int = field(compare=False)
    score: float
    title: str = field(compare=False)


from collections import defaultdict
from heapq import nlargest

from findex.corpus import tokenize
from findex.scoring import BM25, TfIdf, SearchResult
from findex.query import parse, Term, Phrase, And, Or, Not
from findex.cache import QueryCache
from findex.utils import timed


def positive_terms(node, negated=False):
    if isinstance(node, Term):
        return [] if negated else [node.value]

    if isinstance(node, Phrase):
        return [] if negated else tokenize(node.value)

    if isinstance(node, Not):
        return positive_terms(node.operand, not negated)

    if isinstance(node, (And, Or)):
        return (
            positive_terms(node.left, negated)
            + positive_terms(node.right, negated)
        )

    return []


@timed
def search(index, query, scorer=BM25(), k=10, cache=None):
    if not query.strip():
        return []

    tree = parse(query)

    if cache is not None:
        candidates = set(cache.search(query))
    else:
        candidates = tree.evaluate(index)

    scores = defaultdict(float)

    for doc_id in sorted(candidates):
        scores[doc_id] = 0.0

    for term in positive_terms(tree):
        for posting in index.postings.get(term, []):
            if posting.doc_id in candidates:
                scores[posting.doc_id] += scorer.score(
                    term, posting, index
                )

    results = (
        SearchResult(
            doc_id=doc_id,
            score=score,
            title=index.doc_meta[doc_id].title
        )
        for doc_id, score in scores.items()
    )

    return nlargest(k, results)


if __name__ == "__main__":
    import argparse
    from findex.store import open_index
    from findex.snippets import make_snippet

    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--index", default="index.bin")
    parser.add_argument(
        "--scorer",
        choices=["tfidf", "bm25"],
        default="bm25"
    )
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()

    scorer = BM25() if args.scorer == "bm25" else TfIdf()

    with open_index(args.index) as index:
        cache = QueryCache(index)

        for attempt in range(args.repeat):
            print(f"\nRequest: {attempt + 1}")
            print("Query:", args.query)
            print("Scorer:", args.scorer)

            results = search(
                index, args.query, scorer, args.k, cache
            )

            for rank, result in enumerate(results, 1):
                print(
                    f"\n{rank}. {result.title} | "
                    f"ID: {result.doc_id} | "
                    f"Score: {result.score:.6f}"
                )

                print(
                    "Snippet:",
                    make_snippet(
                        index, result.doc_id, args.query
                    )
                )

        print("\nCache statistics:")
        print(cache.cache_info())

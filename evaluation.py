
from findex.ranking import search
from findex.scoring import BM25, TfIdf
from findex.store import open_index

queries = [
    ("programming language", {"doc1"}),
    ("dictionaries AND sets", {"doc1"}),
    ('"inverted index"', {"doc2", "doc4"}),
    ('"hash tables"', {"doc3"}),
    ("keys AND values", {"doc3"}),
    ('"boolean queries"', {"doc4"}),
    ('"data structures"', {"doc5"}),
    ('"memory optimization"', {"doc5"}),
    ('"text documents"', {"doc2"}),
    ('"search engines"', {"doc2", "doc4"})
]


def precision_at_5(results, relevant):
    found = {result.title for result in results[:5]}
    return len(found & relevant) / 5


with open_index("index.bin") as index:
    tfidf_scores = []
    bm25_scores = []

    print(f"{'Query':30} {'TF-IDF':>10} {'BM25':>10}")
    print("-" * 52)

    for query, relevant in queries:
        tfidf_results = search(
            index, query, TfIdf(), k=5
        )

        bm25_results = search(
            index, query, BM25(), k=5
        )

        p_tfidf = precision_at_5(
            tfidf_results, relevant
        )

        p_bm25 = precision_at_5(
            bm25_results, relevant
        )

        tfidf_scores.append(p_tfidf)
        bm25_scores.append(p_bm25)

        print(
            f"{query:30} "
            f"{p_tfidf:10.2f} "
            f"{p_bm25:10.2f}"
        )

    print("-" * 52)

    print(
        "Mean Precision@5 TF-IDF:",
        round(sum(tfidf_scores) / len(queries), 4)
    )

    print(
        "Mean Precision@5 BM25:",
        round(sum(bm25_scores) / len(queries), 4)
    )

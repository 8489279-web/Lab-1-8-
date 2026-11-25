
from findex.store import load
from findex.index import Index, Posting
from findex.scoring import BM25, TfIdf

index = load("index.bin")
bm25 = BM25()
tfidf = TfIdf()

# Check 1
rare = min(index.postings, key=index.df)
common = max(index.postings, key=index.df)

rare_posting = Posting(index[rare][0].doc_id, 1)
common_posting = Posting(index[common][0].doc_id, 1)

rare_score = tfidf.score(rare, rare_posting, index)
common_score = tfidf.score(common, common_posting, index)

print("CHECK 1: Rare vs common term")
print(f"{rare}: {rare_score:.6f}")
print(f"{common}: {common_score:.6f}")
print("PASS:", rare_score > common_score)

# Check 2
term = "python"
doc_id = index[term][0].doc_id

s1 = bm25.score(term, Posting(doc_id, 1), index)
s2 = bm25.score(term, Posting(doc_id, 2), index)
s19 = bm25.score(term, Posting(doc_id, 19), index)
s20 = bm25.score(term, Posting(doc_id, 20), index)

print("\nCHECK 2: BM25 saturation")
print(f"Gain 1 -> 2: {s2 - s1:.6f}")
print(f"Gain 19 -> 20: {s20 - s19:.6f}")
print("PASS:", 0 < s20 - s19 < s2 - s1)

# Check 3
short_id = min(index.doc_lengths, key=index.doc_length)
long_id = max(index.doc_lengths, key=index.doc_length)

short_score = bm25.score(
    term, Posting(short_id, 1), index
)

long_score = bm25.score(
    term, Posting(long_id, 1), index
)

print("\nCHECK 3: Document length")
print(f"Short document: {index.doc_length(short_id)} words")
print(f"Score: {short_score:.6f}")
print(f"Long document: {index.doc_length(long_id)} words")
print(f"Score: {long_score:.6f}")
print("PASS:", short_score > long_score)

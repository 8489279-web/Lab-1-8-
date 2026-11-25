from pathlib import Path

from findex.index import Index, Posting, build_index


def test_document_count(tiny_index: Index) -> None:
    assert tiny_index.num_docs == 5


def test_term_exists(tiny_index: Index) -> None:
    assert "python" in tiny_index


def test_unknown_term(tiny_index: Index) -> None:
    assert "unknownword" not in tiny_index


def test_document_frequency(tiny_index: Index) -> None:
    assert tiny_index.df("python") == 3


def test_term_frequency(tiny_index: Index) -> None:
    posting = tiny_index["python"][-1]
    assert posting.doc_id == 4
    assert posting.tf == 2


def test_positions(tiny_index: Index) -> None:
    posting = tiny_index["python"][-1]
    assert posting.positions == (0, 1)


def test_document_length(tiny_index: Index) -> None:
    assert tiny_index.doc_length(1) == 5


def test_document_title(tiny_index: Index) -> None:
    assert tiny_index.doc_meta[1].title == "doc1"


def test_postings_sorted(tiny_index: Index) -> None:
    for postings in tiny_index.postings.values():
        ids = [p.doc_id for p in postings]
        assert ids == sorted(ids)


def test_without_positions(tiny_corpus: Path) -> None:
    index = build_index(tiny_corpus)
    assert index["python"][0].positions == ()


def test_empty_index(tmp_path: Path) -> None:
    index = build_index(tmp_path)
    assert index.num_docs == 0
    assert len(index) == 0
    assert index.avg_doc_length == 0.0


def test_posting_defaults() -> None:
    posting = Posting(1, 2)
    assert posting.doc_id == 1
    assert posting.tf == 2
    assert posting.positions == ()

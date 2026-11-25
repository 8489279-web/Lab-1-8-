import pytest

from findex.index import Index
from findex.query import And, Not, Or, Phrase, Query, Term, parse


@pytest.mark.parametrize(
    "query, expected",
    [
        ("python", Term("python")),
        ("PYTHON", Term("python")),
        ("python AND search", And(Term("python"), Term("search"))),
        ("python OR search", Or(Term("python"), Term("search"))),
        ("NOT python", Not(Term("python"))),
        ("python search", And(Term("python"), Term("search"))),
        ('"search engine"', Phrase("search engine")),
        (
            "python OR search AND engine",
            Or(Term("python"), And(Term("search"), Term("engine"))),
        ),
        (
            "(python OR search) AND engine",
            And(Or(Term("python"), Term("search")), Term("engine")),
        ),
        ("NOT NOT python", Not(Not(Term("python")))),
    ],
)
def test_parser_tree(query: str, expected: Query) -> None:
    assert parse(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "",
        "python AND",
        "OR python",
        "(python OR search",
        '"search engine',
        "python )",
    ],
)
def test_invalid_query(query: str) -> None:
    with pytest.raises(ValueError):
        parse(query)


@pytest.mark.parametrize(
    "query, expected",
    [
        ("python", {1, 2, 4}),
        ("python AND search", {4}),
        ("python OR search", {1, 2, 3, 4}),
        ("NOT python", {3, 5}),
        ('"python python"', {4}),
        ('"search engine"', {4}),
        ('"engine search"', set()),
        ("unknownword", set()),
    ],
)
def test_query_evaluation(
    tiny_index: Index,
    query: str,
    expected: set[int],
) -> None:
    assert parse(query).evaluate(tiny_index) == expected

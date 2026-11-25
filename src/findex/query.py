
from __future__ import annotations

import re
from dataclasses import dataclass

from findex.corpus import tokenize
from findex.index import Index


class Query:
    def __and__(self, other: Query) -> And:
        return And(self, other)

    def __or__(self, other: Query) -> Or:
        return Or(self, other)

    def __invert__(self) -> Not:
        return Not(self)

    def evaluate(self, index: Index) -> set[int]:
        raise NotImplementedError


@dataclass(frozen=True)
class Term(Query):
    value: str

    def evaluate(self, index: Index) -> set[int]:
        return {
            p.doc_id
            for p in index.postings.get(self.value, [])
        }


@dataclass(frozen=True)
class Phrase(Query):
    value: str

    def evaluate(self, index: Index) -> set[int]:
        words = tokenize(self.value)

        if not words:
            return set()

        postings = [
            {
                p.doc_id: p.positions
                for p in index.postings.get(word, [])
            }
            for word in words
        ]

        candidates = set(postings[0])

        for items in postings[1:]:
            candidates &= set(items)

        results: set[int] = set()

        for doc_id in candidates:
            positions = [
                set(items[doc_id])
                for items in postings
            ]

            for start in positions[0]:
                if all(
                    start + i in positions[i]
                    for i in range(len(words))
                ):
                    results.add(doc_id)
                    break

        return results


@dataclass(frozen=True)
class And(Query):
    left: Query
    right: Query

    def evaluate(self, index: Index) -> set[int]:
        return (
            self.left.evaluate(index)
            & self.right.evaluate(index)
        )


@dataclass(frozen=True)
class Or(Query):
    left: Query
    right: Query

    def evaluate(self, index: Index) -> set[int]:
        return (
            self.left.evaluate(index)
            | self.right.evaluate(index)
        )


@dataclass(frozen=True)
class Not(Query):
    operand: Query

    def evaluate(self, index: Index) -> set[int]:
        return (
            set(index.doc_meta)
            - self.operand.evaluate(index)
        )


class Parser:
    def __init__(self, query: str) -> None:
        self.tokens: list[str] = re.findall(
            r'"[^"]*"|\(|\)|[^\s()"]+',
            query,
        )

        if query.count('"') % 2:
            raise ValueError("Unclosed quotation mark")

        self.position = 0

    def peek(self) -> str | None:
        if self.position < len(self.tokens):
            return self.tokens[self.position]

        return None

    def consume(self) -> str | None:
        token = self.peek()
        self.position += 1
        return token

    def parse(self) -> Query:
        result = self.parse_or()

        if self.peek() is not None:
            raise ValueError("Unexpected token")

        return result

    def parse_or(self) -> Query:
        left = self.parse_and()

        while self.peek() == "OR":
            self.consume()
            left = Or(left, self.parse_and())

        return left

    def parse_and(self) -> Query:
        left = self.parse_not()

        while self.peek() not in (None, "OR", ")"):
            if self.peek() == "AND":
                self.consume()

            left = And(left, self.parse_not())

        return left

    def parse_not(self) -> Query:
        if self.peek() == "NOT":
            self.consume()
            return Not(self.parse_not())

        return self.parse_atom()

    def parse_atom(self) -> Query:
        token = self.consume()

        if token is None:
            raise ValueError("Unexpected end of query")

        if token == "(":
            result = self.parse_or()

            if self.consume() != ")":
                raise ValueError("Missing closing parenthesis")

            return result

        if token.startswith('"'):
            return Phrase(token[1:-1].lower())

        if token in ("AND", "OR", ")"):
            raise ValueError("Unexpected operator")

        return Term(token.lower())


def parse(query: str) -> Query:
    return Parser(query).parse()

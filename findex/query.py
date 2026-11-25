
import re
from dataclasses import dataclass
from findex.corpus import tokenize


class Query:
    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)

    def __invert__(self):
        return Not(self)

    def evaluate(self, index):
        raise NotImplementedError


@dataclass(frozen=True)
class Term(Query):
    value: str

    def evaluate(self, index):
        return {
            p.doc_id
            for p in index.postings.get(self.value, [])
        }


@dataclass(frozen=True)
class Phrase(Query):
    value: str

    def evaluate(self, index):
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

        results = set()

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

    def evaluate(self, index):
        return (
            self.left.evaluate(index)
            & self.right.evaluate(index)
        )


@dataclass(frozen=True)
class Or(Query):
    left: Query
    right: Query

    def evaluate(self, index):
        return (
            self.left.evaluate(index)
            | self.right.evaluate(index)
        )


@dataclass(frozen=True)
class Not(Query):
    operand: Query

    def evaluate(self, index):
        return (
            set(index.doc_meta)
            - self.operand.evaluate(index)
        )


class Parser:
    def __init__(self, query):
        self.tokens = re.findall(
            r'"[^"]*"|\(|\)|[^\s()"]+| uniqueNeverMatch',
            query
        )
        if query.count('"') % 2:
            raise ValueError("Unclosed quotation mark")

        self.position = 0

    def peek(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def consume(self):
        token = self.peek()
        self.position += 1
        return token

    def parse(self):
        result = self.parse_or()

        if self.peek() is not None:
            raise ValueError("Unexpected token")

        return result

    def parse_or(self):
        left = self.parse_and()

        while self.peek() == "OR":
            self.consume()
            left = Or(left, self.parse_and())

        return left

    def parse_and(self):
        left = self.parse_not()

        while self.peek() not in (None, "OR", ")"):
            if self.peek() == "AND":
                self.consume()

            left = And(left, self.parse_not())

        return left

    def parse_not(self):
        if self.peek() == "NOT":
            self.consume()
            return Not(self.parse_not())

        return self.parse_atom()

    def parse_atom(self):
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


def parse(query):
    return Parser(query).parse()

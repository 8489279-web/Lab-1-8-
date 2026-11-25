
import argparse
import tracemalloc
from time import perf_counter
from typing import Literal

from findex.index import Index
from findex.store import load

EngineName = Literal["merge", "set"]


def merge_and(a: list[int], b: list[int]) -> list[int]:
    result: list[int] = []
    i = j = 0

    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            result.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1

    return result


def merge_or(a: list[int], b: list[int]) -> list[int]:
    result: list[int] = []
    i = j = 0

    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            result.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1

    result.extend(a[i:])
    result.extend(b[j:])

    return result


def merge_not(a: list[int], b: list[int]) -> list[int]:
    result: list[int] = []
    i = j = 0

    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        elif a[i] < b[j]:
            result.append(a[i])
            i += 1
        else:
            j += 1

    result.extend(a[i:])

    return result


def get_docs(index: Index, term: str) -> list[int]:
    return [
        p.doc_id
        for p in index.postings.get(term.lower(), [])
    ]


def search(
    index: Index,
    query: str,
    engine: EngineName = "merge",
) -> list[int]:
    tokens = query.lower().split()

    if not tokens:
        return []

    all_docs = sorted(index.doc_meta)

    def intersection(
        a: list[int], b: list[int]
    ) -> list[int]:
        if engine == "set":
            return sorted(set(a) & set(b))
        return merge_and(a, b)

    def union(
        a: list[int], b: list[int]
    ) -> list[int]:
        if engine == "set":
            return sorted(set(a) | set(b))
        return merge_or(a, b)

    def difference(
        a: list[int], b: list[int]
    ) -> list[int]:
        if engine == "set":
            return sorted(set(a) - set(b))
        return merge_not(a, b)

    position = 0

    def operand() -> list[int]:
        nonlocal position

        if position >= len(tokens):
            raise ValueError("Missing operand")

        token = tokens[position]
        position += 1

        if token == "not":
            return difference(all_docs, operand())

        if token in ("and", "or"):
            raise ValueError("Unexpected operator")

        return get_docs(index, token)

    result = operand()

    while position < len(tokens):
        operator = tokens[position]

        if operator in ("and", "or"):
            position += 1
        else:
            operator = "and"

        right = operand()

        if operator == "and":
            result = intersection(result, right)
        else:
            result = union(result, right)

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index")
    parser.add_argument("query")
    parser.add_argument(
        "--engine",
        choices=["merge", "set"],
        default="merge",
    )
    args = parser.parse_args()

    engine: EngineName = (
        "set" if args.engine == "set" else "merge"
    )

    index = load(args.index)

    tracemalloc.start()
    start = perf_counter()

    results = search(index, args.query, engine)

    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("Results:", results)
    print("Documents found:", len(results))
    print(f"Elapsed time: {elapsed:.6f} s")
    print(f"Peak memory: {peak} bytes")


if __name__ == "__main__":
    main()

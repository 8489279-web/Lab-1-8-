import argparse
import tracemalloc
from time import perf_counter


def merge_and(a, b):
    result = []
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


def merge_or(a, b):
    result = []
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


def merge_not(a, b):
    result = []
    j = 0
    for doc_id in a:
        while j < len(b) and b[j] < doc_id:
            j += 1
        if j == len(b) or b[j] != doc_id:
            result.append(doc_id)
    return result


def get_docs(index, term):
    return [p.doc_id for p in index.postings.get(term.lower(), [])]


def search(index, query, engine='merge'):
    tokens = query.lower().split()
    if not tokens:
        return []
    if engine == 'set':
        op_and = lambda a, b: sorted(set(a) & set(b))
        op_or = lambda a, b: sorted(set(a) | set(b))
        op_not = lambda a, b: sorted(set(a) - set(b))
    else:
        op_and, op_or, op_not = merge_and, merge_or, merge_not
    all_docs = sorted(index.doc_meta)
    i = 0

    def operand():
        nonlocal i
        if i >= len(tokens):
            raise ValueError('Missing search term')
        if tokens[i] == 'not':
            i += 1
            return op_not(all_docs, operand())
        if tokens[i] in ('and', 'or'):
            raise ValueError('Unexpected operator')
        docs = get_docs(index, tokens[i])
        i += 1
        return docs

    result = operand()
    while i < len(tokens):
        operator = tokens[i]
        if operator in ('and', 'or'):
            i += 1
        else:
            operator = 'and'
        docs = operand()
        result = op_or(result, docs) if operator == 'or' else op_and(result, docs)
    return result


def main():
    from findex.store import load
    parser = argparse.ArgumentParser()
    parser.add_argument('index_path')
    parser.add_argument('query')
    parser.add_argument('--engine', choices=['merge', 'set'], default='merge')
    args = parser.parse_args()
    tracemalloc.start()
    start = perf_counter()
    index = load(args.index_path)
    ids = search(index, args.query, args.engine)
    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f'Query: {args.query}')
    print(f'Engine: {args.engine}')
    print(f'Found documents: {len(ids)}')
    for doc_id in ids:
        print(doc_id, index.doc_meta[doc_id].title)
    print(f'Elapsed time: {elapsed:.6f} s')
    print(f'Peak memory: {peak} bytes')


if __name__ == '__main__':
    main()

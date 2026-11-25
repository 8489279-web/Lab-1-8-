
from functools import lru_cache

from findex.query import parse
from findex.utils import timed


class QueryCache:
    def __init__(self, index):
        self.index = index

        @lru_cache(maxsize=256)
        def cached(query):
            tree = parse(query)
            return tuple(sorted(tree.evaluate(self.index)))

        self._cached = cached

    @timed
    def search(self, query):
        before = self._cached.cache_info().hits

        results = self._cached(query)

        after = self._cached.cache_info().hits

        if after > before:
            print("[CACHE] HIT")
        else:
            print("[CACHE] MISS")

        return results

    def cache_info(self):
        return self._cached.cache_info()

    def clear(self):
        self._cached.cache_clear()

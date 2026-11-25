
import logging
from functools import lru_cache

from findex.index import Index
from findex.query import parse
from findex.utils import timed

logger = logging.getLogger(__name__)


class QueryCache:
    def __init__(self, index: Index) -> None:
        self.index = index

        @lru_cache(maxsize=256)
        def cached(query: str) -> tuple[int, ...]:
            tree = parse(query)
            return tuple(sorted(tree.evaluate(self.index)))

        self._cached = cached

    @timed
    def search(self, query: str) -> tuple[int, ...]:
        before = self._cached.cache_info().hits
        results = self._cached(query)
        after = self._cached.cache_info().hits

        if after > before:
            logger.info("[CACHE] HIT")
        else:
            logger.info("[CACHE] MISS")

        return results

    def cache_info(self) -> tuple[int, int, int | None, int]:
        return self._cached.cache_info()

    def clear(self) -> None:
        self._cached.cache_clear()

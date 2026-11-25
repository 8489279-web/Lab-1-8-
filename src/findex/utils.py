import logging
from collections.abc import Callable
from functools import wraps
from time import perf_counter

logger = logging.getLogger(__name__)


def timed[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()

        try:
            return func(*args, **kwargs)
        finally:
            logger.info(
                "[TIMED] %s: %.3f ms",
                func.__name__,
                (perf_counter() - start) * 1000,
            )

    return wrapper

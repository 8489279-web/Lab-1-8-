
from functools import wraps
from time import perf_counter


def timed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()

        try:
            return func(*args, **kwargs)
        finally:
            elapsed = (perf_counter() - start) * 1000
            print(f"[TIMED] {func.__name__}: {elapsed:.3f} ms")

    return wrapper

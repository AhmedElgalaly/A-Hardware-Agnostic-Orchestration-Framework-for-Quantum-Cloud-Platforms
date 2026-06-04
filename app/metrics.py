from __future__ import annotations

from time import perf_counter
from typing import Callable, TypeVar


T = TypeVar("T")


def timed_ms(callback: Callable[[], T]) -> tuple[T, float]:
    started = perf_counter()
    result = callback()
    return result, round((perf_counter() - started) * 1000, 3)

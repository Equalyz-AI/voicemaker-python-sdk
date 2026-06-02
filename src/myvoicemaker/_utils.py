from __future__ import annotations

import time
from typing import Callable, TypeVar

from ._errors import TimeoutError

T = TypeVar("T")

_DEFAULT_INTERVAL = 2.0
_DEFAULT_TIMEOUT = 120.0


def poll(
    job_id: str,
    fn: Callable[[], T],
    is_done: Callable[[T], bool],
    interval_seconds: float = _DEFAULT_INTERVAL,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> T:
    deadline = time.monotonic() + timeout_seconds
    while True:
        result = fn()
        if is_done(result):
            return result
        if time.monotonic() >= deadline:
            raise TimeoutError(job_id, timeout_seconds)
        time.sleep(interval_seconds)

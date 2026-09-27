"""Shared burst limit for POST /api/compare. No IP, no cookie."""

from __future__ import annotations

import threading
from collections import deque
from time import monotonic

# Normal slider use (200 ms debounce) stays under this; a tight loop hits 429.
_WINDOW_SEC = 60.0
_MAX_CALLS = 90

_lock = threading.Lock()
_times: deque[float] = deque()


def allow_compare(now: float | None = None) -> bool:
    """Return True and record one slot, or False when the shared window is full."""
    moment = now if now is not None else monotonic()
    cutoff = moment - _WINDOW_SEC
    with _lock:
        while _times and _times[0] < cutoff:
            _times.popleft()
        if len(_times) >= _MAX_CALLS:
            return False
        _times.append(moment)
        return True


def reset_compare_limit_for_tests() -> None:
    with _lock:
        _times.clear()

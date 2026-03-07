from __future__ import annotations

import time
from typing import Dict


class EventDeduper:
    def __init__(self) -> None:
        self._seen: Dict[str, float] = {}

    def should_accept(self, key: str, window_sec: float) -> bool:
        now = time.time()
        last_seen = self._seen.get(key)

        if last_seen is not None and now - last_seen < window_sec:
            return False

        self._seen[key] = now
        self._purge(now, window_sec)
        return True

    def _purge(self, now: float, window_sec: float) -> None:
        expire_before = now - max(window_sec * 10, 60.0)
        stale_keys = [
            key for key, timestamp in self._seen.items() if timestamp < expire_before
        ]
        for key in stale_keys:
            self._seen.pop(key, None)
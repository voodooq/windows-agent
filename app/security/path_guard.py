from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class PathGuard:
    def __init__(self, allowed_roots: Iterable[str] | None = None):
        self.allowed_roots = [self._normalize(root) for root in (allowed_roots or [])]

    def _normalize(self, path: str | Path) -> Path:
        raw = os.path.expandvars(os.path.expanduser(str(path)))
        return Path(raw).resolve()

    def is_allowed(self, path: str | Path) -> bool:
        if not self.allowed_roots:
            return False

        resolved = self._normalize(path)
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def validate(self, path: str | Path) -> tuple[bool, str | None]:
        resolved = self._normalize(path)
        if self.is_allowed(resolved):
            return True, None

        if not self.allowed_roots:
            return False, "no allowed roots configured"

        allowed = ", ".join(str(root) for root in self.allowed_roots)
        return False, f"path outside allowed roots: {resolved}; allowed_roots={allowed}"

    def describe(self) -> list[str]:
        return [str(root) for root in self.allowed_roots]
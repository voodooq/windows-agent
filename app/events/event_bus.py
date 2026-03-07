from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List

from app.schemas.event import Event


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                print(f"[EventBus] handler error for event={event.type}: {exc}")

    def handler_count(self, event_type: str) -> int:
        return len(self._handlers.get(event_type, []))
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class EventLogger:
    def __init__(self, path: str = "data/events.jsonl") -> None:
        self.path = Path(path)

    def log(
        self,
        event_type: str,
        payload: Dict[str, Any],
        *,
        accepted: bool | None = None,
        ignore_reason: str | None = None,
        created_goal_id: str | None = None,
        goal_text: str | None = None,
        goal_priority: int | None = None,
        debounce_hit: bool = False,
        dedupe_hit: bool = False,
        source: str | None = None,
        notes: list[str] | None = None,
    ) -> str:
        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "payload": payload,
            "accepted": accepted,
            "ignore_reason": ignore_reason,
            "created_goal_id": created_goal_id,
            "goal_text": goal_text,
            "goal_priority": goal_priority,
            "debounce_hit": debounce_hit,
            "dedupe_hit": dedupe_hit,
            "source": source,
            "notes": notes or [],
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record["event_id"]
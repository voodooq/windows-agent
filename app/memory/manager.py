from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.schemas.reflection import ReflectionResult


class MemoryManager:
    def __init__(self, path: str = "data/memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(
                json.dumps({"tasks": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save_task(self, record: Dict[str, Any]) -> None:
        data = self.load()
        data.setdefault("tasks", []).append(record)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def recent_task_summaries(self, limit: int = 5) -> List[Dict[str, Any]]:
        data = self.load()
        tasks = data.get("tasks", [])
        summaries: List[Dict[str, Any]] = []
        for task in tasks[-limit:]:
            reflection = task.get("reflection", {})
            summaries.append(
                {
                    "timestamp": task.get("timestamp"),
                    "goal": task.get("goal"),
                    "result_ok": task.get("result", {}).get("ok"),
                    "step_count": len(task.get("result", {}).get("steps", [])),
                    "outcome": reflection.get("outcome"),
                    "lessons": reflection.get("lessons", []),
                }
            )
        return summaries

    def build_reflection_record(self, reflection: ReflectionResult) -> Dict[str, Any]:
        return reflection.model_dump()
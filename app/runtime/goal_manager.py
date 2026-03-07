from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.schemas.goal import Goal


class GoalManager:
    def __init__(self, path: str = "data/goals.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(
                json.dumps({"goals": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_goal(self, goal: Goal) -> None:
        data = self._load()
        data.setdefault("goals", []).append(goal.model_dump())
        self._save(data)

    def list_goals(self) -> List[Goal]:
        data = self._load()
        return [Goal.model_validate(item) for item in data.get("goals", [])]

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        for goal in self.list_goals():
            if goal.id == goal_id:
                return goal
        return None

    def list_open_goals(self) -> List[Goal]:
        return [
            goal
            for goal in self.list_goals()
            if goal.status in {"pending", "active", "blocked"}
        ]

    def find_open_goal_by_text(self, text: str) -> Optional[Goal]:
        normalized = text.strip()
        for goal in self.list_open_goals():
            if goal.text.strip() == normalized:
                return goal
        return None

    def get_active_goal(self) -> Optional[Goal]:
        goals = self.list_goals()

        active = [goal for goal in goals if goal.status == "active"]
        if active:
            active.sort(key=lambda goal: goal.priority)
            return active[0]

        pending = [goal for goal in goals if goal.status == "pending"]
        if pending:
            pending.sort(key=lambda goal: goal.priority)
            goal = pending[0]
            self.update_status(goal.id, "active")
            return self.get_goal(goal.id)

        return None

    def update_status(
        self,
        goal_id: str,
        status: str,
        progress_note: str | None = None,
    ) -> None:
        data = self._load()
        now = datetime.utcnow().isoformat()

        for item in data.get("goals", []):
            if item.get("id") == goal_id:
                item["status"] = status
                item["updated_at"] = now
                if progress_note is not None:
                    item["progress_note"] = progress_note
                break

        self._save(data)

    def increment_retry(self, goal_id: str) -> None:
        data = self._load()
        now = datetime.utcnow().isoformat()

        for item in data.get("goals", []):
            if item.get("id") == goal_id:
                item["retry_count"] = int(item.get("retry_count", 0)) + 1
                item["updated_at"] = now
                break

        self._save(data)
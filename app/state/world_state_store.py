from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.schemas.world_state import WorldState


class WorldStateStore:
    def __init__(self, path: str = "data/world_state.json") -> None:
        self.path = Path(path)

    def load(self) -> WorldState:
        if not self.path.exists():
            return WorldState()

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return WorldState(**data)
        except Exception:
            return WorldState()

    def save(self, state: WorldState) -> WorldState:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state.timestamp = datetime.utcnow().isoformat()
        self.path.write_text(
            json.dumps(state.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return state

    def update_from_observation(
        self,
        observed: WorldState,
        watched_paths: List[str] | None = None,
    ) -> WorldState:
        state = self.load()
        state.active_window = observed.active_window
        state.open_windows = observed.open_windows[:50]
        state.known_files = observed.known_files[:100]
        state.last_tool = observed.last_tool
        state.last_tool_ok = observed.last_tool_ok
        state.last_error = observed.last_error
        state.notes = observed.notes[-20:]
        if watched_paths is not None:
            state.watched_paths = watched_paths[:20]
        return self.save(state)

    def append_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        ignored_reason: str | None = None,
        decision: str | None = None,
        decision_code: str | None = None,
        reason: str | None = None,
    ) -> WorldState:
        state = self.load()
        event_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "payload": payload,
        }
        if ignored_reason:
            event_record["ignored_reason"] = ignored_reason
        if decision:
            event_record["decision"] = decision
        if decision_code:
            event_record["decision_code"] = decision_code
        if reason:
            event_record["reason"] = reason
        state.recent_events = self._append_limited(state.recent_events, event_record, 50)
        return self.save(state)

    def append_goal(
        self,
        goal_id: str,
        text: str,
        priority: int,
        trigger_type: str,
        status: str = "pending",
    ) -> WorldState:
        state = self.load()
        goal_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "goal_id": goal_id,
            "text": text,
            "priority": priority,
            "trigger_type": trigger_type,
            "status": status,
        }
        state.recent_goals = self._append_limited(state.recent_goals, goal_record, 20)
        return self.save(state)

    def append_tool(
        self,
        tool_name: str,
        ok: bool | None,
        error: str | None = None,
        failure_code: str | None = None,
    ) -> WorldState:
        state = self.load()
        tool_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "ok": ok,
        }
        if error:
            tool_record["error"] = error
        if failure_code:
            tool_record["failure_code"] = failure_code
        state.recent_tools = self._append_limited(state.recent_tools, tool_record, 20)
        state.last_tool = tool_name
        state.last_tool_ok = ok
        if error:
            state.last_error = error
        return self.save(state)

    def append_failure(
        self,
        source: str,
        message: str,
        context: Dict[str, Any] | None = None,
        failure_code: str | None = None,
    ) -> WorldState:
        state = self.load()
        failure_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "message": message,
        }
        if context:
            failure_record["context"] = context
        if failure_code:
            failure_record["failure_code"] = failure_code
        state.recent_failures = self._append_limited(
            state.recent_failures,
            failure_record,
            20,
        )
        state.last_error = message
        return self.save(state)

    def add_new_file(self, path: str) -> WorldState:
        state = self.load()
        state.new_files = self._append_unique_limited(state.new_files, path, 50)
        state.known_files = self._append_unique_limited(state.known_files, path, 100)
        return self.save(state)

    def add_note(self, note: str) -> WorldState:
        state = self.load()
        state.notes = self._append_limited(state.notes, note, 20)
        return self.save(state)

    def set_watched_paths(self, paths: List[str]) -> WorldState:
        state = self.load()
        state.watched_paths = paths[:20]
        return self.save(state)

    def set_bad_state(self, bad_state: Dict[str, Any] | None) -> WorldState:
        state = self.load()
        state.bad_state = bad_state or {}
        return self.save(state)

    def update_goal_status(
        self,
        goal_id: str,
        status: str,
        detail: str | None = None,
    ) -> WorldState:
        state = self.load()
        updated_goals: List[Dict[str, Any]] = []

        for item in state.recent_goals:
            record = dict(item)
            if record.get("goal_id") == goal_id:
                record["status"] = status
                record["updated_at"] = datetime.utcnow().isoformat()
                if detail:
                    record["detail"] = detail
            updated_goals.append(record)

        state.recent_goals = updated_goals[-20:]
        if detail and status == "failed":
            state.last_error = detail
        return self.save(state)

    def build_summary(
        self,
        event_limit: int = 5,
        goal_limit: int = 5,
        failure_limit: int = 5,
        tool_limit: int = 5,
        new_file_limit: int = 10,
    ) -> Dict[str, Any]:
        state = self.load()
        return {
            "recent_events_summary": state.recent_events[-event_limit:],
            "recent_goals_summary": state.recent_goals[-goal_limit:],
            "recent_failures_summary": state.recent_failures[-failure_limit:],
            "recent_tools_summary": state.recent_tools[-tool_limit:],
            "new_files": state.new_files[-new_file_limit:],
            "watched_paths": state.watched_paths[:20],
            "last_error": state.last_error,
            "last_tool": state.last_tool,
            "last_tool_ok": state.last_tool_ok,
            "bad_state": state.bad_state,
        }

    def _append_limited(self, items: List[Any], value: Any, limit: int) -> List[Any]:
        return (items + [value])[-limit:]

    def _append_unique_limited(self, items: List[str], value: str, limit: int) -> List[str]:
        updated = [item for item in items if item != value]
        updated.append(value)
        return updated[-limit:]
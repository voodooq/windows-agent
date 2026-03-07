from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.config import load_config
from app.memory.manager import MemoryManager
from app.tools.files import get_allowed_roots
from app.daemon import AgentDaemon
from app.runtime.goal_manager import GoalManager
from app.state.approval_store import ApprovalStore
from app.state.world_state_store import WorldStateStore


class AgentController:
    def __init__(self, config_path: str = "configs/default.yaml") -> None:
        self.config_path = config_path
        self.config = load_config(config_path)
        self.daemon = AgentDaemon(config_path=config_path)
        self.goal_manager = GoalManager(
            path=str(self.config.runtime.get("goals_path", "data/goals.json"))
        )
        self.world_state_store = WorldStateStore(
            path=str(self.config.runtime.get("world_state_path", "data/world_state.json"))
        )
        self.approval_store = ApprovalStore(
            path=str(self.config.runtime.get("approval_store_path", "data/approvals.json"))
        )
        self.memory = MemoryManager(path=str(self.config.runtime.get("memory_path", "data/memory.json")))
        self.event_log_path = Path(
            str(self.config.runtime.get("event_log_path", "data/events.jsonl"))
        )
        self._daemon_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _peek_active_goal(self) -> dict[str, Any] | None:
        goals = self.goal_manager.list_goals()
        active = [goal for goal in goals if goal.status == "active"]
        if active:
            active.sort(key=lambda goal: (goal.priority, goal.updated_at))
            return active[0].model_dump()

        pending = [goal for goal in goals if goal.status == "pending"]
        if pending:
            pending.sort(key=lambda goal: (goal.priority, goal.updated_at))
            return pending[0].model_dump()

        return None

    def start_daemon(self) -> bool:
        with self._lock:
            if self._daemon_thread and self._daemon_thread.is_alive():
                return False

            self._daemon_thread = threading.Thread(
                target=self.daemon.run_forever,
                kwargs={"sleep_sec": 1.0},
                daemon=True,
                name="agent-daemon-thread",
            )
            self._daemon_thread.start()
            return True

    def stop_daemon(self) -> bool:
        with self._lock:
            running = self.is_running()
            self.daemon.stop()
            return running

    def is_running(self) -> bool:
        thread_alive = bool(self._daemon_thread and self._daemon_thread.is_alive())
        return self.daemon.is_running() or thread_alive

    def pause_auto_goals(self) -> None:
        self.daemon.pause_auto_goals()

    def resume_auto_goals(self) -> None:
        self.daemon.resume_auto_goals()

    def add_goal(self, text: str, priority: int = 5, trigger_type: str = "manual") -> dict[str, Any]:
        normalized = text.strip()
        if not normalized:
            raise ValueError("goal text cannot be empty")

        goal = self.daemon.add_goal(
            normalized,
            priority=priority,
            trigger_type=trigger_type,
        )
        return goal.model_dump()

    def get_status_summary(self) -> dict[str, Any]:
        snapshot = self.daemon.get_status_snapshot()
        current_state = self.world_state_store.load()
        open_goals = self.goal_manager.list_open_goals()
        all_goals = self.goal_manager.list_goals()

        pending_approvals = self.approval_store.list_pending()

        snapshot.update(
            {
                "running": self.is_running(),
                "app_name": self.config.app.get("name", "windows-agent"),
                "notes": current_state.notes[-5:],
                "recent_failure_count": len(current_state.recent_failures),
                "recent_tool_count": len(current_state.recent_tools),
                "total_goal_count": len(all_goals),
                "open_goal_count": len(open_goals),
                "pending_approval_count": len(pending_approvals),
                "bad_state": current_state.bad_state,
                "bad_state_severity": (current_state.bad_state or {}).get("severity", "normal"),
                "autonomy_mode": (current_state.bad_state or {}).get("autonomy_mode", "normal"),
            }
        )
        return snapshot

    def get_recent_goals(self, limit: int = 10) -> list[dict[str, Any]]:
        goals = self.goal_manager.list_goals()
        goals.sort(key=lambda goal: goal.updated_at, reverse=True)
        return [goal.model_dump() for goal in goals[:limit]]

    def get_active_goal(self) -> dict[str, Any] | None:
        return self._peek_active_goal()

    def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        state = self.world_state_store.load()
        return list(reversed(state.recent_events[-limit:]))

    def get_recent_tools(self, limit: int = 20) -> list[dict[str, Any]]:
        state = self.world_state_store.load()
        return list(reversed(state.recent_tools[-limit:]))

    def get_recent_failures(self, limit: int = 10) -> list[dict[str, Any]]:
        state = self.world_state_store.load()
        return list(reversed(state.recent_failures[-limit:]))

    def get_recent_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.event_log_path.exists():
            return []

        lines = self.event_log_path.read_text(encoding="utf-8").splitlines()
        records: list[dict[str, Any]] = []

        for line in reversed(lines[-limit:]):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"raw": line})

        return records

    def get_pending_approvals(self, limit: int = 20) -> list[dict[str, Any]]:
        approvals = self.approval_store.list_pending()
        approvals.sort(key=lambda item: item.created_at, reverse=True)
        return [item.model_dump() for item in approvals[:limit]]

    def get_recent_memory_tasks(self, limit: int = 5) -> list[dict[str, Any]]:
        tasks = self.memory.load().get("tasks", [])
        return list(reversed(tasks[-limit:]))

    def get_latest_task_details(self) -> dict[str, Any] | None:
        tasks = self.memory.load().get("tasks", [])
        if not tasks:
            return None
        return tasks[-1]

    def get_allowed_roots(self) -> list[str]:
        return get_allowed_roots()

    def approve_approval(self, approval_id: str, note: str | None = None) -> dict[str, Any]:
        result = self.approval_store.resolve(approval_id, approved=True, note=note)
        if result is None:
            raise ValueError("approval request not found")
        return result.model_dump()

    def reject_approval(self, approval_id: str, note: str | None = None) -> dict[str, Any]:
        result = self.approval_store.resolve(approval_id, approved=False, note=note)
        if result is None:
            raise ValueError("approval request not found")
        return result.model_dump()

    def get_dashboard_data(self) -> dict[str, Any]:
        latest_task = self.get_latest_task_details()
        status = self.get_status_summary()
        status["allowed_roots"] = self.get_allowed_roots()

        return {
            "status": status,
            "active_goal": self.get_active_goal(),
            "recent_goals": self.get_recent_goals(limit=10),
            "recent_events": self.get_recent_events(limit=20),
            "recent_tools": self.get_recent_tools(limit=20),
            "recent_failures": self.get_recent_failures(limit=10),
            "recent_logs": self.get_recent_logs(limit=20),
            "pending_approvals": self.get_pending_approvals(limit=20),
            "latest_task": latest_task,
            "recent_memory_tasks": self.get_recent_memory_tasks(limit=5),
            "allowed_roots": self.get_allowed_roots(),
        }

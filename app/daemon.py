from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.events.event_bus import EventBus
from app.events.event_deduper import EventDeduper
from app.events.file_watcher import FileWatcher
from app.events.scheduler import Scheduler
from app.runtime.agent_runtime import AgentRuntime
from app.runtime.goal_factory import GoalFactory
from app.runtime.goal_manager import GoalManager
from app.runtime.state_analyzer import StateAnalyzer
from app.schemas.decision_codes import DecisionCode
from app.schemas.event import Event
from app.schemas.failure_codes import FailureCode
from app.schemas.goal import Goal
from app.state.event_logger import EventLogger
from app.state.world_state_store import WorldStateStore

console = Console()


class AgentDaemon:
    def __init__(self, config_path: str = "configs/default.yaml") -> None:
        self.config_path = config_path
        self.config = load_config(config_path)
        self.runtime = AgentRuntime(self.config)
        self.goal_manager = GoalManager(
            path=str(self.config.runtime.get("goals_path", "data/goals.json"))
        )
        self.world_state_store = WorldStateStore(
            path=str(self.config.runtime.get("world_state_path", "data/world_state.json"))
        )
        self.event_bus = EventBus()
        self.scheduler = Scheduler(self.event_bus)
        self.event_deduper = EventDeduper()
        self.goal_factory = GoalFactory(
            config=self.config,
            goal_manager=self.goal_manager,
            event_deduper=self.event_deduper,
        )
        self.state_analyzer = StateAnalyzer()
        self.event_logger = EventLogger(
            path=str(self.config.runtime.get("event_log_path", "data/events.jsonl"))
        )
        self.file_watcher = FileWatcher(self.event_bus)
        self._running = False
        self._auto_goals_paused = False

        self._register_handlers()
        self._register_default_jobs()
        self._register_watchers()

    def _register_handlers(self) -> None:
        self.event_bus.subscribe("goal.created", self.on_goal_created)
        self.event_bus.subscribe("goal.run_pending", self.on_run_pending_goals)
        self.event_bus.subscribe("system.heartbeat", self.on_heartbeat)
        self.event_bus.subscribe("file.changed", self.on_file_changed)

    def _register_default_jobs(self) -> None:
        self.scheduler.add_interval_job(
            name="heartbeat",
            interval_sec=10,
            event_type="system.heartbeat",
            payload_factory=lambda: {"source": "scheduler"},
        )
        self.scheduler.add_interval_job(
            name="run_pending_goals",
            interval_sec=5,
            event_type="goal.run_pending",
            payload_factory=lambda: {},
        )

    def _register_watchers(self) -> None:
        watch_conf = self._file_watch_config()
        if not watch_conf.get("enabled", False):
            return

        recursive = bool(watch_conf.get("recursive", False))
        watched_paths: list[str] = []
        for path in watch_conf.get("paths", []):
            resolved = str(Path(path).resolve())
            self.file_watcher.watch_path(path, recursive=recursive)
            watched_paths.append(resolved)
            console.print(f"[cyan]Watching path:[/cyan] {resolved}")
        if watched_paths:
            self.world_state_store.set_watched_paths(watched_paths)

    def _file_watch_config(self) -> dict:
        return self.config.data.get("watchers", {}).get("file_watch", {})

    def on_goal_created(self, event: Event) -> None:
        console.print(f"[cyan][Event][/cyan] goal.created -> {event.payload}")

    def on_file_changed(self, event: Event) -> None:
        self._refresh_bad_state()
        payload = event.payload or {}
        action = payload.get("action", "created")
        raw_path = payload.get("path")

        summary_payload = {"action": action, "path": raw_path}
        current_state = self.world_state_store.load()
        bad_state = current_state.bad_state or {}
        if self._auto_goals_paused:
            decision = self.goal_factory.decide_from_event(event).model_copy(
                update={
                    "accepted": False,
                    "reason": "auto_goals_paused",
                    "decision_code": DecisionCode.SUPPRESSED_BY_BAD_STATE.value,
                    "metadata": {
                        "action": action,
                        "path": raw_path,
                        "paused": True,
                    },
                }
            )
        elif bad_state.get("recommended_action") == "pause_auto_goal_creation":
            decision = self._bad_state_goal_decision(event, raw_path, action, bad_state)
        else:
            decision = self.goal_factory.decide_from_event(event)
        normalized_path = decision.metadata.get("path", raw_path)
        summary_payload["path"] = normalized_path

        self.world_state_store.append_event(
            "file.changed",
            summary_payload,
            ignored_reason=None if decision.accepted else decision.reason,
            decision="accepted" if decision.accepted else "ignored",
            decision_code=decision.decision_code,
            reason=decision.reason,
        )

        if action == "created" and normalized_path:
            self.world_state_store.add_new_file(normalized_path)

        if not decision.accepted:
            if decision.reason == "debounced":
                console.print(f"[dim]Debounced file event:[/dim] {action} {normalized_path}")
            elif decision.reason == "duplicate_goal_suppressed":
                console.print(
                    f"[dim]Suppressed duplicate goal:[/dim] "
                    f"{decision.metadata.get('goal_text', '')}"
                )
            elif decision.reason == "open_goal_exists":
                console.print(
                    f"[dim]Open goal already exists:[/dim] "
                    f"{decision.metadata.get('goal_text', '')}"
                )

            self.event_logger.log(
                event_type=event.type,
                payload=summary_payload,
                accepted=False,
                ignore_reason=decision.reason,
                goal_text=decision.goal_text or decision.metadata.get("goal_text"),
                goal_priority=decision.priority,
                debounce_hit=decision.debounce_hit,
                dedupe_hit=decision.dedupe_hit,
                source="daemon.on_file_changed",
                notes=[decision.reason],
            )
            self.world_state_store.add_note(f"file event ignored: {decision.reason}")
            return

        console.print(f"[blue][File Event][/blue] {action}: {normalized_path}")
        goal = self.add_goal(
            decision.goal_text or "",
            priority=decision.priority or 3,
            trigger_type=decision.trigger_type,
        )
        self.event_logger.log(
            event_type=event.type,
            payload=summary_payload,
            accepted=True,
            created_goal_id=goal.id,
            goal_text=goal.text,
            goal_priority=goal.priority,
            debounce_hit=decision.debounce_hit,
            dedupe_hit=decision.dedupe_hit,
            source="daemon.on_file_changed",
            notes=[decision.reason],
        )

    def on_run_pending_goals(self, event: Event) -> None:
        if self._auto_goals_paused:
            return

        goal = self.goal_manager.get_active_goal()
        if not goal:
            return

        console.print(f"[yellow]Running goal:[/yellow] {goal.id} | {goal.text}")
        try:
            run_output = self.runtime.run(goal.text)
            ok = bool(run_output.get("result", {}).get("ok"))

            if ok:
                self.goal_manager.update_status(
                    goal.id,
                    "completed",
                    "goal finished successfully",
                )
                self.world_state_store.update_goal_status(
                    goal.id,
                    "completed",
                    "goal finished successfully",
                )
                console.print(f"[green]Goal completed:[/green] {goal.id}")
            else:
                steps = run_output.get("result", {}).get("steps", [])
                pending_approval_step = next(
                    (
                        step
                        for step in steps
                        if (step.get("exec_result") or {}).get("requires_approval")
                    ),
                    None,
                )
                if pending_approval_step:
                    approval_id = (pending_approval_step.get("exec_result") or {}).get("approval_id")
                    self.goal_manager.update_status(
                        goal.id,
                        "blocked",
                        f"waiting for approval: {approval_id}",
                    )
                    self.world_state_store.update_goal_status(
                        goal.id,
                        "blocked",
                        f"waiting for approval: {approval_id}",
                    )
                    console.print(
                        f"[yellow]Goal waiting for approval:[/yellow] {goal.id} | {approval_id}"
                    )
                    return

                self.goal_manager.increment_retry(goal.id)
                updated = self.goal_manager.get_goal(goal.id)
                retry_limit = int(self.config.runtime.get("max_goal_retries", 2))

                if updated and updated.retry_count > retry_limit:
                    self.goal_manager.update_status(
                        goal.id,
                        "failed",
                        "retry limit reached",
                    )
                    self.world_state_store.update_goal_status(
                        goal.id,
                        "failed",
                        "retry limit reached",
                    )
                    replanned = run_output.get("result", {}).get("replanned", {})
                    self.world_state_store.append_failure(
                        source="daemon",
                        message="retry limit reached",
                        context={
                            "goal_id": goal.id,
                            "goal_text": goal.text,
                            "recovery_mode": replanned.get("recovery_mode"),
                            "recovery_code": replanned.get("recovery_code"),
                        },
                        failure_code=FailureCode.RETRY_LIMIT_REACHED.value,
                    )
                    console.print(f"[red]Goal failed:[/red] {goal.id}")
                else:
                    self.goal_manager.update_status(
                        goal.id,
                        "pending",
                        "will retry after failure",
                    )
                    self.world_state_store.update_goal_status(
                        goal.id,
                        "pending",
                        "will retry after failure",
                    )
                    console.print(f"[magenta]Goal replanned for retry:[/magenta] {goal.id}")

        except Exception as exc:
            self.goal_manager.increment_retry(goal.id)
            updated = self.goal_manager.get_goal(goal.id)
            retry_limit = int(self.config.runtime.get("max_goal_retries", 2))

            if updated and updated.retry_count > retry_limit:
                self.goal_manager.update_status(
                    goal.id,
                    "failed",
                    f"runtime exception: {exc}",
                )
                self.world_state_store.update_goal_status(
                    goal.id,
                    "failed",
                    f"runtime exception: {exc}",
                )
                self.world_state_store.append_failure(
                    source="daemon",
                    message=f"runtime exception: {exc}",
                    context={"goal_id": goal.id, "goal_text": goal.text},
                    failure_code=FailureCode.RUNTIME_EXCEPTION.value,
                )
            else:
                self.goal_manager.update_status(
                    goal.id,
                    "pending",
                    f"runtime exception, will retry: {exc}",
                )
                self.world_state_store.update_goal_status(
                    goal.id,
                    "pending",
                    f"runtime exception, will retry: {exc}",
                )
            console.print(f"[red]Daemon run error:[/red] {exc}")

    def on_heartbeat(self, event: Event) -> None:
        self._refresh_bad_state()
        console.print("[blue]heartbeat[/blue]")

    def _refresh_bad_state(self) -> None:
        current_state = self.world_state_store.load()
        analyzed = self.state_analyzer.analyze(current_state)
        if analyzed.get("is_bad_state"):
            self.world_state_store.set_bad_state(analyzed)
        else:
            self.world_state_store.set_bad_state({})

    def _bad_state_goal_decision(
        self,
        event: Event,
        raw_path: str | None,
        action: str,
        bad_state: dict,
    ):
        return self.goal_factory.decide_from_event(event).model_copy(
            update={
                "accepted": False,
                "reason": "suppressed_by_bad_state",
                "decision_code": DecisionCode.SUPPRESSED_BY_BAD_STATE.value,
                "metadata": {
                    "action": action,
                    "path": raw_path,
                    "bad_state": bad_state,
                },
            }
        )

    def add_goal(
        self,
        text: str,
        priority: int = 5,
        trigger_type: str = "manual",
    ) -> Goal:
        goal = Goal(
            id=str(uuid.uuid4()),
            text=text,
            priority=priority,
            trigger_type=trigger_type,
        )
        self.goal_manager.add_goal(goal)
        self.world_state_store.append_goal(
            goal_id=goal.id,
            text=goal.text,
            priority=goal.priority,
            trigger_type=goal.trigger_type,
            status=goal.status,
        )
        self.event_bus.publish(Event(type="goal.created", payload=goal.model_dump()))
        return goal

    def run_forever(self, sleep_sec: float = 1.0) -> None:
        self._running = True
        self.world_state_store.add_note("agent daemon started")
        console.print(Panel("Agent Daemon Started", style="green"))

        try:
            self.file_watcher.start()
            while self._running:
                self.scheduler.tick()
                time.sleep(sleep_sec)
        except KeyboardInterrupt:
            console.print("[red]Daemon stopped by user[/red]")
        finally:
            self.file_watcher.stop()
            self._running = False

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def pause_auto_goals(self) -> None:
        self._auto_goals_paused = True
        self.world_state_store.add_note("auto goals paused")

    def resume_auto_goals(self) -> None:
        self._auto_goals_paused = False
        self.world_state_store.add_note("auto goals resumed")

    def auto_goals_paused(self) -> bool:
        return self._auto_goals_paused

    def get_status_snapshot(self) -> dict:
        current_state = self.world_state_store.load()
        open_goals = self.goal_manager.list_open_goals()
        goals = self.goal_manager.list_goals()

        active_goals = [goal for goal in goals if goal.status == "active"]
        if active_goals:
            active_goals.sort(key=lambda goal: (goal.priority, goal.updated_at))
            active_goal = active_goals[0]
        else:
            pending_goals = [goal for goal in goals if goal.status == "pending"]
            pending_goals.sort(key=lambda goal: (goal.priority, goal.updated_at))
            active_goal = pending_goals[0] if pending_goals else None

        bad_state = current_state.bad_state or {}

        return {
            "running": self._running,
            "auto_goals_paused": self._auto_goals_paused,
            "mode": self.config.app.get("mode", "unknown"),
            "active_goal": active_goal.model_dump() if active_goal else None,
            "open_goal_count": len(open_goals),
            "watched_paths": current_state.watched_paths,
            "last_tool": current_state.last_tool,
            "last_tool_ok": current_state.last_tool_ok,
            "last_error": current_state.last_error,
            "bad_state": bad_state,
            "bad_state_severity": bad_state.get("severity", "normal"),
            "autonomy_mode": bad_state.get("autonomy_mode", "normal"),
        }


if __name__ == "__main__":
    daemon = AgentDaemon()
    daemon.run_forever()
from __future__ import annotations

from pathlib import Path

from app.config import Config
from app.events.event_deduper import EventDeduper
from app.runtime.goal_manager import GoalManager
from app.schemas.decision_codes import DecisionCode
from app.schemas.event import Event
from app.schemas.goal_decision import GoalDecision


class GoalFactory:
    def __init__(
        self,
        config: Config,
        goal_manager: GoalManager,
        event_deduper: EventDeduper,
    ) -> None:
        self.config = config
        self.goal_manager = goal_manager
        self.event_deduper = event_deduper

    def decide_from_event(self, event: Event) -> GoalDecision:
        if event.type == "file.changed":
            return self._decide_file_changed(event)

        return GoalDecision(
            accepted=False,
            reason="unsupported_event_type",
            decision_code=DecisionCode.UNSUPPORTED_EVENT_TYPE.value,
            event_type=event.type,
            metadata={"payload": event.payload},
        )

    def _decide_file_changed(self, event: Event) -> GoalDecision:
        watch_conf = self._file_watch_config()
        payload = event.payload or {}
        raw_path = payload.get("path")
        action = payload.get("action", "created")

        if not watch_conf.get("create_goal_on_new_file", True):
            return GoalDecision(
                accepted=False,
                reason="goal_creation_disabled",
                decision_code=DecisionCode.GOAL_CREATION_DISABLED.value,
                event_type=event.type,
                metadata={"action": action, "path": raw_path},
            )

        if not raw_path:
            return GoalDecision(
                accepted=False,
                reason="missing_path",
                decision_code=DecisionCode.MISSING_PATH.value,
                event_type=event.type,
                metadata={"action": action, "path": raw_path},
            )

        path = self._normalize_path(raw_path)
        should_ignore, ignore_reason = self._should_ignore_file_event(action, path)
        if should_ignore:
            return GoalDecision(
                accepted=False,
                reason=ignore_reason or "filtered_by_watch_config",
                decision_code=(ignore_reason or "filtered_by_watch_config"),
                event_type=event.type,
                metadata={"action": action, "path": path},
            )

        debounce_sec = float(watch_conf.get("debounce_sec", 2.0))
        dedupe_window_sec = float(
            watch_conf.get(
                "dedupe_window_sec",
                self._goal_factory_config().get("suppress_duplicate_goal_window_sec", 15.0),
            )
        )

        event_key = f"file.changed:{action}:{path}"
        if not self.event_deduper.should_accept(event_key, debounce_sec):
            return GoalDecision(
                accepted=False,
                reason="debounced",
                decision_code=DecisionCode.DEBOUNCED.value,
                event_type=event.type,
                event_key=event_key,
                debounce_hit=True,
                metadata={"action": action, "path": path},
            )

        goal_text = self._build_goal_text_from_file_event(path)
        goal_key = f"goal.from_file:{goal_text}"
        if not self.event_deduper.should_accept(goal_key, dedupe_window_sec):
            return GoalDecision(
                accepted=False,
                reason="duplicate_goal_suppressed",
                decision_code=DecisionCode.DUPLICATE_GOAL_SUPPRESSED.value,
                event_type=event.type,
                event_key=event_key,
                goal_key=goal_key,
                dedupe_hit=True,
                metadata={"action": action, "path": path, "goal_text": goal_text},
            )

        suppress_if_open_goal_exists = bool(
            self._goal_factory_config().get("suppress_if_open_goal_exists", True)
        )
        if suppress_if_open_goal_exists and self.goal_manager.find_open_goal_by_text(goal_text):
            return GoalDecision(
                accepted=False,
                reason="open_goal_exists",
                decision_code=DecisionCode.OPEN_GOAL_EXISTS.value,
                event_type=event.type,
                event_key=event_key,
                goal_key=goal_key,
                metadata={"action": action, "path": path, "goal_text": goal_text},
            )

        return GoalDecision(
            accepted=True,
            reason="accepted",
            decision_code=DecisionCode.ACCEPTED.value,
            event_type=event.type,
            goal_text=goal_text,
            priority=int(watch_conf.get("goal_priority_on_new_file", 3)),
            trigger_type=str(self._goal_factory_config().get("default_trigger_type", "event")),
            event_key=event_key,
            goal_key=goal_key,
            metadata={"action": action, "path": path},
        )

    def _file_watch_config(self) -> dict:
        return self.config.data.get("watchers", {}).get("file_watch", {})

    def _goal_factory_config(self) -> dict:
        return self.config.data.get("goal_factory", {})

    def _normalize_path(self, path: str) -> str:
        return str(Path(path).resolve())

    def _should_ignore_file_event(self, action: str, path: str) -> tuple[bool, str | None]:
        watch_conf = self._file_watch_config()
        allowed_actions = set(watch_conf.get("include_actions", ["created", "modified"]))
        if action not in allowed_actions:
            return True, "filtered_by_action"

        file_path = Path(path)
        suffix = file_path.suffix.lower()
        name = file_path.name

        ignore_suffixes = {item.lower() for item in watch_conf.get("ignore_suffixes", [])}
        extra_low_value_suffixes = {
            item.lower() for item in self._goal_factory_config().get("low_value_suffixes", [])
        }
        all_ignore_suffixes = ignore_suffixes | extra_low_value_suffixes
        if suffix and suffix in all_ignore_suffixes:
            return True, "filtered_by_suffix"

        ignore_prefixes = tuple(watch_conf.get("ignore_prefixes", []))
        extra_low_value_prefixes = tuple(
            self._goal_factory_config().get("low_value_prefixes", [])
        )
        all_ignore_prefixes = ignore_prefixes + extra_low_value_prefixes
        if all_ignore_prefixes and name.startswith(all_ignore_prefixes):
            return True, "filtered_by_prefix"

        return False, None

    def _build_goal_text_from_file_event(self, path: str) -> str:
        file_path = Path(path)
        suffix = file_path.suffix.lower()

        if suffix in {".txt", ".md", ".json", ".csv"}:
            return f"读取文件 {path} 并总结其内容"
        if suffix == ".pdf":
            return f"检测到新的 PDF 文件 {path}，列出其基本信息并规划后续整理步骤"
        return f"列出文件 {path} 的基本信息并记录"
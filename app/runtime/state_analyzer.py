from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from app.schemas.world_state import WorldState


class StateAnalyzer:
    def analyze(self, state: WorldState) -> Dict[str, Any]:
        signals: List[str] = []
        signal_scores: Dict[str, int] = {}

        recent_failures = state.recent_failures[-5:]
        recent_goals = state.recent_goals[-10:]
        recent_tools = state.recent_tools[-10:]
        recent_events = state.recent_events[-10:]
        new_files = state.new_files[-10:]

        failed_goals = [item for item in recent_goals if item.get("status") == "failed"]
        conservative_recoveries = [
            item
            for item in recent_failures
            if item.get("context", {}).get("recovery_mode") == "conservative_recovery"
        ]

        repeated_goal_texts = self._repeated_goal_texts(recent_goals)
        repeated_failed_tools = self._repeated_failed_tools(recent_tools)
        repeated_paths = self._repeated_event_paths(recent_events)

        if len(recent_failures) >= 3:
            self._add_signal(signals, signal_scores, "recent_failure_spike", 3)

        if recent_goals and len(failed_goals) >= max(2, len(recent_goals) // 2):
            self._add_signal(signals, signal_scores, "goal_failure_rate_high", 3)

        if repeated_failed_tools:
            self._add_signal(signals, signal_scores, "repeated_tool_failures", 2)

        if repeated_paths:
            self._add_signal(signals, signal_scores, "duplicate_path_event_pressure", 2)

        if len(new_files) >= 5:
            self._add_signal(signals, signal_scores, "recent_new_file_burst", 1)

        if len(conservative_recoveries) >= 2:
            self._add_signal(signals, signal_scores, "recovery_mode_conservative_repeated", 2)

        if repeated_goal_texts:
            self._add_signal(signals, signal_scores, "repeated_goal_pressure", 2)

        failure_rate = round(
            (len(failed_goals) / len(recent_goals)) if recent_goals else 0.0,
            2,
        )
        pressure_score = sum(signal_scores.values())
        severity = self._severity_for_score(pressure_score)
        autonomy_mode = self._autonomy_mode_for_severity(severity)
        recommended_action = self._recommended_action_for_severity(severity)
        is_bad_state = severity in {"medium", "high", "critical"}

        return {
            "is_bad_state": is_bad_state,
            "severity": severity,
            "signals": signals,
            "signal_scores": signal_scores,
            "pressure_score": pressure_score,
            "failure_rate": failure_rate,
            "repeated_failed_tools": repeated_failed_tools,
            "repeated_paths": repeated_paths,
            "repeated_goal_texts": repeated_goal_texts,
            "autonomy_mode": autonomy_mode,
            "recommended_action": recommended_action,
        }

    def _add_signal(
        self,
        signals: List[str],
        signal_scores: Dict[str, int],
        signal_name: str,
        score: int,
    ) -> None:
        signals.append(signal_name)
        signal_scores[signal_name] = score

    def _repeated_failed_tools(self, recent_tools: List[Dict[str, Any]]) -> List[str]:
        tool_failures = [
            item.get("tool")
            for item in recent_tools
            if item.get("ok") is False and item.get("tool")
        ]
        tool_failure_counts = Counter(tool_failures)
        return [tool_name for tool_name, count in tool_failure_counts.items() if count >= 2]

    def _repeated_event_paths(self, recent_events: List[Dict[str, Any]]) -> List[str]:
        event_paths = [
            str(item.get("payload", {}).get("path", "")).strip()
            for item in recent_events
            if str(item.get("payload", {}).get("path", "")).strip()
        ]
        path_counts = Counter(event_paths)
        return [path for path, count in path_counts.items() if count >= 3]

    def _repeated_goal_texts(self, recent_goals: List[Dict[str, Any]]) -> List[str]:
        goal_texts = [
            str(item.get("text", "")).strip()
            for item in recent_goals
            if str(item.get("text", "")).strip()
        ]
        goal_counts = Counter(goal_texts)
        return [text for text, count in goal_counts.items() if count >= 3]

    def _severity_for_score(self, score: int) -> str:
        if score >= 7:
            return "critical"
        if score >= 5:
            return "high"
        if score >= 2:
            return "medium"
        if score == 1:
            return "low"
        return "normal"

    def _autonomy_mode_for_severity(self, severity: str) -> str:
        if severity == "critical":
            return "inspect_only"
        if severity == "high":
            return "conservative"
        if severity == "medium":
            return "guarded"
        return "normal"

    def _recommended_action_for_severity(self, severity: str) -> str:
        if severity == "critical":
            return "pause_auto_goal_creation"
        if severity == "high":
            return "approval_only_for_medium_and_high_risk"
        if severity == "medium":
            return "degrade_to_conservative_goal_creation"
        return "continue"

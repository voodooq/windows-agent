from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.recovery_codes import RecoveryCode
from app.schemas.verification import VerificationResult


class Replanner:
    def replan(
        self,
        goal_text: str,
        failed_step: Dict[str, Any],
        tool_result: Dict[str, Any],
        verification_result: VerificationResult,
        world_state,
        world_state_summary: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        tool = failed_step.get("tool")
        args = failed_step.get("args", {})
        reason = verification_result.reason or tool_result.get("error") or "unknown"

        recent_failures = self._summary_list(world_state_summary, "recent_failures_summary")
        recent_tools = self._summary_list(world_state_summary, "recent_tools_summary")
        recent_goals = self._summary_list(world_state_summary, "recent_goals_summary")
        recent_events = self._summary_list(world_state_summary, "recent_events_summary")
        new_files = self._summary_list(world_state_summary, "new_files")

        same_tool_failure_count = self._count_failures_for_tool(recent_failures, tool)
        recent_same_tool_failed = self._recent_same_tool_failed(recent_tools, tool)
        recent_similar_goal_failed = self._recent_similar_goal_failed(recent_goals, goal_text)
        recent_file_event_count = self._recent_file_event_count(recent_events)
        recent_new_files_count = len(new_files)
        last_tool = self._summary_value(world_state_summary, "last_tool")
        last_tool_ok = self._summary_value(world_state_summary, "last_tool_ok")

        recovery_mode, recovery_code = self._choose_recovery_decision(
            same_tool_failure_count=same_tool_failure_count,
            recent_same_tool_failed=recent_same_tool_failed,
            recent_similar_goal_failed=recent_similar_goal_failed,
            recent_file_event_count=recent_file_event_count,
            recent_new_files_count=recent_new_files_count,
        )

        suggestions = self._build_suggestions(
            tool=tool,
            args=args,
            recovery_mode=recovery_mode,
            recent_same_tool_failed=recent_same_tool_failed,
            recent_new_files_count=recent_new_files_count,
        )

        reasoning_summary = self._build_reasoning_summary(
            tool=tool,
            reason=reason,
            recovery_mode=recovery_mode,
            same_tool_failure_count=same_tool_failure_count,
            recent_same_tool_failed=recent_same_tool_failed,
            recent_similar_goal_failed=recent_similar_goal_failed,
            recent_file_event_count=recent_file_event_count,
            recent_new_files_count=recent_new_files_count,
        )

        return {
            "goal": goal_text,
            "reasoning_summary": reasoning_summary,
            "recovery_mode": recovery_mode,
            "recovery_code": recovery_code,
            "steps": suggestions,
            "context": {
                "last_tool": tool,
                "last_error": reason,
                "failure_code": verification_result.failure_code,
                "visible_windows": len(getattr(world_state, "open_windows", [])),
                "same_tool_failure_count": same_tool_failure_count,
                "recent_same_tool_failed": recent_same_tool_failed,
                "recent_similar_goal_failed": recent_similar_goal_failed,
                "recent_file_event_count": recent_file_event_count,
                "recent_new_files_count": recent_new_files_count,
                "summary_last_tool": last_tool,
                "summary_last_tool_ok": last_tool_ok,
            },
        }

    def _summary_list(
        self,
        summary: Dict[str, Any] | None,
        key: str,
    ) -> List[Any]:
        if not summary:
            return []
        value = summary.get(key, [])
        return value if isinstance(value, list) else []

    def _summary_value(
        self,
        summary: Dict[str, Any] | None,
        key: str,
    ) -> Any:
        if not summary:
            return None
        return summary.get(key)

    def _count_failures_for_tool(
        self,
        recent_failures: List[Dict[str, Any]],
        tool: str | None,
    ) -> int:
        if not tool:
            return 0

        count = 0
        for item in recent_failures:
            context = item.get("context", {})
            if context.get("tool") == tool:
                count += 1
        return count

    def _recent_same_tool_failed(
        self,
        recent_tools: List[Dict[str, Any]],
        tool: str | None,
    ) -> bool:
        if not tool:
            return False

        for item in reversed(recent_tools[-3:]):
            if item.get("tool") == tool and item.get("ok") is False:
                return True
        return False

    def _recent_similar_goal_failed(
        self,
        recent_goals: List[Dict[str, Any]],
        goal_text: str,
    ) -> bool:
        normalized_goal = goal_text.strip()
        if not normalized_goal:
            return False

        for item in reversed(recent_goals[-5:]):
            if item.get("text", "").strip() == normalized_goal and item.get("status") == "failed":
                return True
        return False

    def _recent_file_event_count(
        self,
        recent_events: List[Dict[str, Any]],
    ) -> int:
        count = 0
        for item in recent_events:
            payload = item.get("payload", {})
            event_type = str(item.get("type", "")).lower()
            path_value = str(payload.get("path", "")).strip()
            if "file" in event_type or path_value:
                count += 1
        return count

    def _choose_recovery_decision(
        self,
        same_tool_failure_count: int,
        recent_same_tool_failed: bool,
        recent_similar_goal_failed: bool,
        recent_file_event_count: int,
        recent_new_files_count: int,
    ) -> tuple[str, str]:
        if recent_similar_goal_failed:
            return (
                "conservative_recovery",
                RecoveryCode.CONSERVATIVE_DUE_TO_SIMILAR_GOAL_FAILURE.value,
            )

        if same_tool_failure_count >= 2:
            return (
                "conservative_recovery",
                RecoveryCode.CONSERVATIVE_DUE_TO_REPEAT_TOOL_FAILURES.value,
            )

        if recent_same_tool_failed:
            return (
                "inspect_first",
                RecoveryCode.INSPECT_DUE_TO_RECENT_TOOL_FAILURE.value,
            )

        if recent_file_event_count >= 3 or recent_new_files_count > 0:
            return (
                "inspect_first",
                RecoveryCode.INSPECT_DUE_TO_FILE_ACTIVITY.value,
            )

        return "retry_direct", RecoveryCode.RETRY_AFTER_SINGLE_FAILURE.value

    def _build_suggestions(
        self,
        tool: str | None,
        args: Dict[str, Any],
        recovery_mode: str,
        recent_same_tool_failed: bool,
        recent_new_files_count: int,
    ) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []

        if tool == "open_app":
            suggestions.append(
                {
                    "id": "rp1",
                    "tool": "list_windows",
                    "args": {},
                    "expected": "inspect current windows before retrying open_app",
                    "risk_level": "low",
                }
            )
        elif tool in {"wait_for_window", "focus_window"}:
            suggestions.append(
                {
                    "id": "rp1",
                    "tool": "list_windows",
                    "args": {},
                    "expected": "find actual window title",
                    "risk_level": "low",
                }
            )
        elif tool == "click_element":
            suggestions.append(
                {
                    "id": "rp1",
                    "tool": "get_window_texts",
                    "args": {
                        "window_title": args.get("window_title", ""),
                    },
                    "expected": "inspect visible texts before clicking again",
                    "risk_level": "low",
                }
            )
        elif tool == "type_text":
            suggestions.append(
                {
                    "id": "rp1",
                    "tool": "list_windows",
                    "args": {},
                    "expected": "inspect active windows before typing again",
                    "risk_level": "low",
                }
            )
        elif tool in {"write_text", "move_file", "create_dir"}:
            target_path = args.get("path") or args.get("dst") or "."
            suggestions.append(
                {
                    "id": "rp1",
                    "tool": "list_files",
                    "args": {"path": str(target_path)},
                    "expected": "inspect target directory state",
                    "risk_level": "low",
                }
            )

        if tool in {"write_text", "move_file", "create_dir"} and recent_new_files_count > 0:
            if not suggestions:
                suggestions.append(
                    {
                        "id": "rp1",
                        "tool": "list_files",
                        "args": {"path": str(args.get("path") or args.get("dst") or ".")},
                        "expected": "inspect target directory state",
                        "risk_level": "low",
                    }
                )
            suggestions[0]["expected"] = "inspect target directory state and recent new files"

        if recovery_mode == "conservative_recovery":
            return suggestions[:1]

        if recovery_mode == "inspect_first" and tool in {"focus_window", "wait_for_window"}:
            if recent_same_tool_failed:
                suggestions.append(
                    {
                        "id": "rp2",
                        "tool": "get_window_texts",
                        "args": {
                            "window_title": args.get("window_title", ""),
                        },
                        "expected": "inspect window texts after listing windows",
                        "risk_level": "low",
                    }
                )

        return suggestions

    def _build_reasoning_summary(
        self,
        tool: str | None,
        reason: str,
        recovery_mode: str,
        same_tool_failure_count: int,
        recent_same_tool_failed: bool,
        recent_similar_goal_failed: bool,
        recent_file_event_count: int,
        recent_new_files_count: int,
    ) -> str:
        details: List[str] = [f"Replanned after failure in {tool}: {reason}"]

        if same_tool_failure_count:
            details.append(f"same tool failures in recent history={same_tool_failure_count}")
        if recent_same_tool_failed:
            details.append("recent same tool attempt already failed")
        if recent_similar_goal_failed:
            details.append("similar goal recently failed")
        if recent_file_event_count:
            details.append(f"recent file events={recent_file_event_count}")
        if recent_new_files_count:
            details.append(f"recent new files={recent_new_files_count}")

        if recovery_mode == "conservative_recovery":
            details.append("using conservative low-risk recovery")
        elif recovery_mode == "inspect_first":
            details.append("using inspect-first recovery")
        else:
            details.append("using direct retry-oriented recovery")

        return "; ".join(details)
from __future__ import annotations

from enum import StrEnum


class RecoveryCode(StrEnum):
    RETRY_AFTER_SINGLE_FAILURE = "retry_after_single_failure"
    INSPECT_DUE_TO_RECENT_TOOL_FAILURE = "inspect_due_to_recent_tool_failure"
    INSPECT_DUE_TO_FILE_ACTIVITY = "inspect_due_to_file_activity"
    CONSERVATIVE_DUE_TO_REPEAT_TOOL_FAILURES = "conservative_due_to_repeat_tool_failures"
    CONSERVATIVE_DUE_TO_SIMILAR_GOAL_FAILURE = "conservative_due_to_similar_goal_failure"
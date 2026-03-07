from __future__ import annotations

from enum import StrEnum


class DecisionCode(StrEnum):
    ACCEPTED = "accepted"
    UNSUPPORTED_EVENT_TYPE = "unsupported_event_type"
    GOAL_CREATION_DISABLED = "goal_creation_disabled"
    MISSING_PATH = "missing_path"
    FILTERED_BY_ACTION = "filtered_by_action"
    FILTERED_BY_SUFFIX = "filtered_by_suffix"
    FILTERED_BY_PREFIX = "filtered_by_prefix"
    DEBOUNCED = "debounced"
    DUPLICATE_GOAL_SUPPRESSED = "duplicate_goal_suppressed"
    OPEN_GOAL_EXISTS = "open_goal_exists"
    SUPPRESSED_BY_BAD_STATE = "suppressed_by_bad_state"
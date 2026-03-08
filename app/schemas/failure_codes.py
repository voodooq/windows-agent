from __future__ import annotations

from enum import StrEnum


class FailureCode(StrEnum):
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    DIRECTORY_NOT_FOUND_AFTER_CREATE = "directory_not_found_after_create"
    FILE_NOT_FOUND_AFTER_WRITE = "file_not_found_after_write"
    DESTINATION_NOT_FOUND_AFTER_MOVE = "destination_not_found_after_move"
    WINDOW_NOT_VERIFIED = "window_not_verified"
    WINDOW_TEXT_READ_FAILED = "window_text_read_failed"
    RETRY_LIMIT_REACHED = "retry_limit_reached"
    RUNTIME_EXCEPTION = "runtime_exception"
    WRONG_TARGET = "wrong_target"
    STALE_UI = "stale_ui"
    ELEMENT_NOT_INTERACTABLE = "element_not_interactable"
    GROUNDING_FAILED = "grounding_failed"
    VISUAL_VERIFICATION_MISMATCH = "visual_verification_mismatch"
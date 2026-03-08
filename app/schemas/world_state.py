from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorldState(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    active_window: Optional[str] = None
    open_windows: List[Dict[str, Any]] = Field(default_factory=list)
    known_files: List[str] = Field(default_factory=list)
    last_tool: Optional[str] = None
    last_tool_ok: Optional[bool] = None
    last_error: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    recent_events: List[Dict[str, Any]] = Field(default_factory=list)
    recent_goals: List[Dict[str, Any]] = Field(default_factory=list)
    recent_failures: List[Dict[str, Any]] = Field(default_factory=list)
    recent_tools: List[Dict[str, Any]] = Field(default_factory=list)
    watched_paths: List[str] = Field(default_factory=list)
    new_files: List[str] = Field(default_factory=list)
    bad_state: Dict[str, Any] = Field(default_factory=dict)

    # Visual/computer-use state
    screenshot_path: Optional[str] = None
    annotated_screenshot_path: Optional[str] = None
    screenshot_metadata: Dict[str, Any] = Field(default_factory=dict)
    ui_elements: List[Dict[str, Any]] = Field(default_factory=list)
    screen_summary: Optional[str] = None
    ocr_text: List[str] = Field(default_factory=list)
    last_action_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    recent_trajectories: List[Dict[str, Any]] = Field(default_factory=list)
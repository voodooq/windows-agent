from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class GoalDecision(BaseModel):
    accepted: bool
    reason: str
    decision_code: str
    event_type: str
    goal_text: Optional[str] = None
    priority: Optional[int] = None
    trigger_type: str = "event"
    event_key: Optional[str] = None
    goal_key: Optional[str] = None
    debounce_hit: bool = False
    dedupe_hit: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    id: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "pending"
    goal_text: str = ""
    step_id: str = ""
    tool: str = ""
    args: Dict[str, Any] = Field(default_factory=dict)
    expected: Optional[str] = None
    risk_level: str = "low"
    reason: str = ""
    requested_by: str = "executor"
    bad_state: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    resolution_note: Optional[str] = None
    resolved_at: Optional[str] = None
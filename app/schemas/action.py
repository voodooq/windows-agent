from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Action(BaseModel):
    id: str = Field(..., description="Unique step id")
    tool: str = Field(..., description="Tool name to call")
    args: Dict[str, Any] = Field(default_factory=dict)
    expected: Optional[str] = None
    risk_level: str = "low"
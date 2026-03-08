from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Action(BaseModel):
    id: str = Field(..., description="Unique step id")
    tool: str = Field(..., description="Tool name to call")
    args: Dict[str, Any] = Field(default_factory=dict)
    expected: Optional[str] = None
    risk_level: str = "low"
    
    # Best-of-N support
    candidates: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative tool/args for this step")
    score: Optional[float] = None
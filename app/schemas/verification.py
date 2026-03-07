from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VerificationResult(BaseModel):
    ok: bool
    reason: Optional[str] = None
    failure_code: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    method: str = "rule_based"
    details: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.failure_codes import FailureCode
from app.schemas.recovery_codes import RecoveryCode


class ReflectionResult(BaseModel):
    outcome: str = Field(..., description="success or failure")
    failure_type: Optional[FailureCode] = None
    reason: Optional[str] = None
    evidence: Optional[str] = None
    recovery_plan: Optional[str] = None
    suggested_recovery_code: Optional[RecoveryCode] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    failed_steps: List[str] = Field(default_factory=list)
    lessons: List[str] = Field(default_factory=list)
    action_artifacts: Dict[str, Any] = Field(default_factory=dict)
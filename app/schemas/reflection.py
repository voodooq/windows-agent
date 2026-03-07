from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Reflection(BaseModel):
    outcome: str = Field(..., description="success or failure")
    failed_step: Optional[str] = None
    root_causes: List[str] = Field(default_factory=list)
    lessons: List[str] = Field(default_factory=list)
    memory_writes: List[str] = Field(default_factory=list)
    should_write_memory: bool = True
    skill_candidate: bool = False
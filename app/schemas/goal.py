from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Goal(BaseModel):
    id: str
    text: str
    status: str = "pending"  # pending / active / blocked / completed / failed / cancelled
    priority: int = 5
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    trigger_type: str = "manual"  # manual / scheduled / event
    progress_note: Optional[str] = None
    retry_count: int = 0
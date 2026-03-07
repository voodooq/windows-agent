from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    ok: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
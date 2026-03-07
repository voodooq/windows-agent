from __future__ import annotations

from typing import List

from pydantic import BaseModel

from app.schemas.action import Action


class Plan(BaseModel):
    goal: str
    reasoning_summary: str
    steps: List[Action]
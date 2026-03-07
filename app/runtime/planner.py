from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from pydantic import ValidationError

from app.llm.base import BaseLLMClient
from app.schemas.plan import Plan
from app.tools.registry import ToolRegistry


class Planner:
    def __init__(self, llm: BaseLLMClient, tool_registry: ToolRegistry):
        self.llm = llm
        self.tool_registry = tool_registry
        self.system_prompt = Path("app/prompts/planner_system.txt").read_text(encoding="utf-8")

    def create_plan(
        self,
        user_goal: str,
        memory_summaries: List[Dict[str, Any]] | None = None,
        world_state_summary: Dict[str, Any] | None = None,
    ) -> Plan:
        memory_summaries = memory_summaries or []
        world_state_summary = world_state_summary or {}

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "goal": user_goal,
                        "available_tools": self.tool_registry.get_tool_specs(),
                        "recent_memory": memory_summaries,
                        "world_state_summary": world_state_summary,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ]

        raw = self.llm.chat_json(messages=messages, temperature=0.1, max_tokens=1800)
        payload = self._parse_plan_json(raw)
        return Plan.model_validate(payload)

    def _parse_plan_json(self, raw: str) -> Dict[str, Any]:
        text = raw.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if fenced:
            candidate = fenced.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as e:
                raise ValueError(f"planner returned invalid JSON: {e}\nraw={raw}") from e

        raise ValueError(f"planner returned non-JSON response: {raw}")
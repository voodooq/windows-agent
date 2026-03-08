from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.llm.base import BaseLLMClient
from app.schemas.reflection import ReflectionResult


class Reflector:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm
        self.system_prompt = Path("app/prompts/reflector_system.txt").read_text(encoding="utf-8")

    def reflect(
        self, 
        goal: str, 
        execution_result: Dict[str, Any],
        world_state_summary: Dict[str, Any] | None = None
    ) -> ReflectionResult:
        world_state_summary = world_state_summary or {}
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "goal": goal,
                        "execution_result": execution_result,
                        "world_state_summary": world_state_summary,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ]

        raw = self.llm.chat_json(messages=messages, temperature=0.0, max_tokens=1200)
        try:
            payload = json.loads(raw)
            return ReflectionResult.model_validate(payload)
        except Exception:
            # Fallback to a basic failure reflection if LLM fails or returns garbage
            return ReflectionResult(
                outcome="failure",
                reason=f"LLM Reflection failed or returned invalid format: {raw[:200]}",
                confidence=0.0
            )
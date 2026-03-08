from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.llm.base import BaseLLMClient


class ActionScorer:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm
        prompt_path = Path("app/prompts/scorer_system.txt")
        self.system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else "Score the action..."

    def score_action(
        self, 
        goal: str, 
        action: Dict[str, Any], 
        world_state_summary: Dict[str, Any]
    ) -> Tuple[float, str]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": json.dumps({
                    "goal": goal,
                    "action": action,
                    "world_state": world_state_summary
                }, ensure_ascii=False)
            }
        ]
        
        try:
            raw = self.llm.chat_json(messages=messages, temperature=0.0)
            data = json.loads(raw)
            return float(data.get("score", 0.0)), data.get("reasoning", "no reasoning provided")
        except Exception:
            return 0.5, "scoring failed, defaulting to neutral"

    def select_best(
        self, 
        goal: str, 
        actions: List[Dict[str, Any]], 
        world_state_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not actions:
            return {}
        if len(actions) == 1:
            return actions[0]
            
        scored_actions = []
        for action in actions:
            score, reasoning = self.score_action(goal, action, world_state_summary)
            scored_actions.append((score, action))
            
        # Sort by score descending
        scored_actions.sort(key=lambda x: x[0], reverse=True)
        return scored_actions[0][1]

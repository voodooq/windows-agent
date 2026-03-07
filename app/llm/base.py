from __future__ import annotations

from typing import Any, Dict, List


class BaseLLMClient:
    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        raise NotImplementedError

    def chat_multimodal_json(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        images: List[Dict[str, Any]] | None = None,
    ) -> str:
        raise NotImplementedError

    def supports_multimodal(self) -> bool:
        return False
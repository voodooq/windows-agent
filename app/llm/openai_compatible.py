from __future__ import annotations

from typing import Any, Dict, List

from openai import OpenAI

from app.llm.base import BaseLLMClient


class OpenAICompatibleClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 120,
        responses_model: bool = False,
    ):
        self.model = model
        self.responses_model = responses_model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        if self.responses_model:
            response = self.client.responses.create(
                model=self.model,
                input=messages,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            return self._extract_text_from_response(response)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        message = resp.choices[0].message
        content = message.content or ""
        return self._extract_text_content(content)

    def chat_multimodal_json(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        images: List[Dict[str, Any]] | None = None,
    ) -> str:
        multimodal_messages = list(messages)
        if images:
            multimodal_messages = self._inject_images(messages=messages, images=images)

        if self.responses_model:
            response = self.client.responses.create(
                model=self.model,
                input=multimodal_messages,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            return self._extract_text_from_response(response)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=multimodal_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        message = resp.choices[0].message
        content = message.content or ""
        return self._extract_text_content(content)

    def supports_multimodal(self) -> bool:
        return True

    def _inject_images(
        self,
        messages: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not messages:
            return []

        enriched = list(messages)
        last = dict(enriched[-1])
        current_content = last.get("content", "")

        content_blocks: List[Dict[str, Any]] = []
        if isinstance(current_content, str):
            if current_content.strip():
                content_blocks.append({"type": "text", "text": current_content})
        elif isinstance(current_content, list):
            for item in current_content:
                if isinstance(item, dict):
                    content_blocks.append(item)

        for image in images:
            image_url = image.get("image_url")
            if image_url:
                content_blocks.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    }
                )

        last["content"] = content_blocks
        enriched[-1] = last
        return enriched

    def _extract_text_from_response(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text).strip()

        output = getattr(response, "output", None) or []
        parts: List[str] = []

        for item in output:
            content = getattr(item, "content", None) or []
            for c in content:
                text = getattr(c, "text", None)
                if text:
                    parts.append(str(text))

        return "\n".join(parts).strip()

    def _extract_text_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                else:
                    text = getattr(item, "text", None)
                    if text:
                        parts.append(str(text))
            return "\n".join(parts).strip()

        return str(content).strip()
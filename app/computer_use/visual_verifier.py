from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageChops

from app.llm.base import BaseLLMClient
from app.schemas.verification import VerificationResult


class VisualVerifier:
    def __init__(self, llm: Optional[BaseLLMClient] = None):
        self.llm = llm
        prompt_path = Path("app/prompts/visual_verifier_system.txt")
        self.system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else "You are a visual verifier..."

    def verify_transition(
        self,
        before_path: Optional[str],
        after_path: Optional[str],
        expectation: Optional[str] = None,
        min_changed_pixels: int = 250,
    ) -> VerificationResult:
        if not before_path or not after_path:
            return VerificationResult(
                ok=False,
                reason="missing screenshot for visual verification",
                failure_code="missing_visual_context",
                method="visual_diff",
            )

        # 1. Pixel Diff Baseline
        before = Image.open(before_path).convert("RGB")
        after = Image.open(after_path).convert("RGB")

        if before.size != after.size:
            return VerificationResult(
                ok=True,
                reason="screen size changed after action",
                evidence=["screenshot resolution changed"],
                method="visual_diff",
                details={
                    "before_size": before.size,
                    "after_size": after.size,
                    "expectation": expectation,
                },
            )

        diff = ImageChops.difference(before, after)
        bbox = diff.getbbox()
        changed_pixels = 0

        if bbox is not None:
            cropped = diff.crop(bbox)
            histogram = cropped.histogram()
            changed_pixels = int(sum(histogram[1:]))

        pixel_ok = changed_pixels >= min_changed_pixels

        # 2. Multimodal Confirmation (If LLM is available and expectation exists)
        if self.llm and expectation:
            # Note: In a real system we would pass images here. 
            # For now, we simulate multimodal by passing descriptions or just letting the LLM know.
            # If the specific LLM client supports image paths in prompt, use them.
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user", 
                    "content": json.dumps({
                        "expectation": expectation,
                        "pixel_change_detected": pixel_ok,
                        "pixel_count": changed_pixels,
                        "before_screenshot": before_path,
                        "after_screenshot": after_path,
                    })
                }
            ]
            
            try:
                raw = self.llm.chat_json(messages=messages, temperature=0.0)
                res = json.loads(raw)
                return VerificationResult.model_validate(res)
            except Exception:
                pass # Fallback to pixel diff if LLM fails

        # 3. Fallback to Pixel Diff
        ok = pixel_ok
        reason = (
            "visual change detected after action"
            if ok
            else "screen change too small, action may not have taken effect"
        )

        return VerificationResult(
            ok=ok,
            reason=reason,
            failure_code=None if ok else "visual_change_not_detected",
            evidence=[
                f"changed_pixels={changed_pixels}",
                f"expectation={expectation or 'not_provided'}",
            ],
            suggestions=[] if ok else ["retry action", "re-ground UI elements", "trigger replanner"],
            method="visual_diff",
            details={
                "changed_pixels": changed_pixels,
                "diff_bbox": bbox,
                "expectation": expectation,
                "min_changed_pixels": min_changed_pixels,
            },
            artifacts=[
                {"type": "before_screenshot", "path": before_path},
                {"type": "after_screenshot", "path": after_path},
            ],
        )
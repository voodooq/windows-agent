from __future__ import annotations

from typing import Any, Dict, Optional

from PIL import Image, ImageChops

from app.schemas.verification import VerificationResult


class VisualVerifier:
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

        ok = changed_pixels >= min_changed_pixels
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
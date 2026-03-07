from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pyautogui


class ScreenCapture:
    def __init__(self, artifacts_dir: str = "data/artifacts/screens"):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def capture_screen(self, prefix: str = "screen") -> Dict[str, Any]:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        image_path = self.artifacts_dir / f"{prefix}_{timestamp}.png"

        image = pyautogui.screenshot()
        image.save(image_path)

        width, height = image.size
        return {
            "ok": True,
            "path": str(image_path.resolve()),
            "width": width,
            "height": height,
            "timestamp": timestamp,
        }

    def save_image_copy(self, image, prefix: str = "annotated") -> Dict[str, Any]:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        image_path = self.artifacts_dir / f"{prefix}_{timestamp}.png"
        image.save(image_path)
        width, height = image.size
        return {
            "ok": True,
            "path": str(image_path.resolve()),
            "width": width,
            "height": height,
            "timestamp": timestamp,
        }
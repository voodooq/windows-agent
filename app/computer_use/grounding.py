from __future__ import annotations

from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont

from app.computer_use.screen import ScreenCapture


class GroundingProvider:
    def ground(self, image_path: str) -> Dict[str, Any]:
        raise NotImplementedError


class GridGroundingProvider(GroundingProvider):
    def __init__(
        self,
        screen_capture: ScreenCapture | None = None,
        columns: int = 4,
        rows: int = 3,
    ):
        self.screen_capture = screen_capture or ScreenCapture()
        self.columns = max(columns, 1)
        self.rows = max(rows, 1)

    def ground(self, image_path: str) -> Dict[str, Any]:
        image = Image.open(image_path)
        width, height = image.size
        box_width = width / self.columns
        box_height = height / self.rows

        elements: List[Dict[str, Any]] = []
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        font = ImageFont.load_default()

        box_id = 1
        for row in range(self.rows):
            for col in range(self.columns):
                left = int(col * box_width)
                top = int(row * box_height)
                right = int((col + 1) * box_width)
                bottom = int((row + 1) * box_height)

                element = {
                    "box_id": box_id,
                    "label": f"grid-{row + 1}-{col + 1}",
                    "bbox": {
                        "left": left,
                        "top": top,
                        "right": right,
                        "bottom": bottom,
                    },
                    "center": {
                        "x": int((left + right) / 2),
                        "y": int((top + bottom) / 2),
                    },
                    "confidence": 0.1,
                    "interactable": True,
                    "source": "grid_grounding_fallback",
                }
                elements.append(element)

                draw.rectangle((left, top, right, bottom), outline="red", width=2)
                draw.text((left + 4, top + 4), str(box_id), fill="red", font=font)
                box_id += 1

        annotated_result = self.screen_capture.save_image_copy(annotated, prefix="grounded")
        return {
            "ok": True,
            "elements": elements,
            "annotated_screenshot_path": annotated_result["path"],
            "provider": "grid_grounding_fallback",
            "image_size": {"width": width, "height": height},
        }
from __future__ import annotations

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont

from app.computer_use.screen import ScreenCapture


class GroundingProvider(ABC):
    @abstractmethod
    def ground(self, image_path: str) -> Dict[str, Any]:
        """进行 Grounding 识别，返回元素列表和标注后的图片路径"""
        pass


class GridGroundingProvider(GroundingProvider):
    def __init__(
        self,
        screen_capture: Optional[ScreenCapture] = None,
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


class UITarsGroundingProvider(GroundingProvider):
    """(TODO) 接入 UI-TARS 模型进行语义 grounding"""
    def ground(self, image_path: str) -> Dict[str, Any]:
        # TODO: 实现 UI-TARS 逻辑
        raise NotImplementedError("UITarsGroundingProvider is not yet implemented")


class HttpGroundingProvider(GroundingProvider):
    """(TODO) 接入外部 HTTP API 进行 grounding"""
    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url
        self.api_key = api_key

    def ground(self, image_path: str) -> Dict[str, Any]:
        # TODO: 实现 API 调用逻辑
        raise NotImplementedError("HttpGroundingProvider is not yet implemented")
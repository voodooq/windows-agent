from __future__ import annotations

from typing import Any, Dict, List

import pyautogui


class ComputerController:
    def __init__(self, pause_sec: float = 0.1):
        self.pause_sec = pause_sec
        pyautogui.PAUSE = pause_sec

    def click_box(
        self,
        box_id: int,
        elements: List[Dict[str, Any]],
        button: str = "left",
        clicks: int = 1,
    ) -> Dict[str, Any]:
        element = self._find_element(box_id=box_id, elements=elements)
        center = element["center"]
        pyautogui.click(center["x"], center["y"], clicks=clicks, button=button)
        return {
            "ok": True,
            "action": "click_box",
            "box_id": box_id,
            "point": center,
            "button": button,
            "clicks": clicks,
        }

    def move_to_box(self, box_id: int, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        element = self._find_element(box_id=box_id, elements=elements)
        center = element["center"]
        pyautogui.moveTo(center["x"], center["y"])
        return {
            "ok": True,
            "action": "move_to_box",
            "box_id": box_id,
            "point": center,
        }

    def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        pyautogui.write(text, interval=interval)
        return {
            "ok": True,
            "action": "type_text",
            "text": text,
            "interval": interval,
        }

    def press_keys(self, keys: List[str]) -> Dict[str, Any]:
        pyautogui.hotkey(*keys)
        return {
            "ok": True,
            "action": "press_keys",
            "keys": keys,
        }

    def scroll(self, clicks: int) -> Dict[str, Any]:
        pyautogui.scroll(clicks)
        return {
            "ok": True,
            "action": "scroll",
            "clicks": clicks,
        }

    def _find_element(self, box_id: int, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        for element in elements:
            if int(element.get("box_id", -1)) == int(box_id):
                return element
        raise ValueError(f"box_id not found in grounding result: {box_id}")
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.computer_use.grounding import GridGroundingProvider, GroundingProvider
from app.computer_use.screen import ScreenCapture
from app.schemas.world_state import WorldState
from app.tools.windows_ui import get_window_texts, list_windows


class Observer:
    def __init__(
        self,
        watch_paths: List[str] | None = None,
        enable_visual_observation: bool = False,
        screen_capture: ScreenCapture | None = None,
        grounding_provider: GroundingProvider | None = None,
    ):
        self.watch_paths = watch_paths or ["./workspace", "./data"]
        self.enable_visual_observation = enable_visual_observation
        self.screen_capture = screen_capture or ScreenCapture()
        self.grounding_provider = grounding_provider or GridGroundingProvider(
            screen_capture=self.screen_capture
        )

    def snapshot_windows(self, title_filter: str | None = None) -> Dict[str, Any]:
        result = list_windows(title_filter=title_filter)
        if not result.ok:
            return {"ok": False, "error": result.error, "windows": []}
        return {"ok": True, "windows": result.output.get("windows", [])}

    def window_exists(self, title: str) -> Dict[str, Any]:
        snapshot = self.snapshot_windows(title_filter=title)
        if not snapshot.get("ok"):
            return snapshot

        windows: List[Dict[str, Any]] = snapshot.get("windows", [])
        matched = [w for w in windows if title.lower() in str(w.get("title", "")).lower()]
        return {
            "ok": True,
            "exists": len(matched) > 0,
            "count": len(matched),
            "windows": matched,
        }

    def read_window_texts(self, title: str) -> Dict[str, Any]:
        result = get_window_texts(window_title=title)
        if not result.ok:
            return {"ok": False, "error": result.error, "texts": []}
        return {"ok": True, "texts": result.output.get("texts", [])}

    def file_exists(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        return {
            "ok": True,
            "exists": p.exists(),
            "path": str(p.resolve()),
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
        }

    def dir_exists(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        return {
            "ok": True,
            "exists": p.exists() and p.is_dir(),
            "path": str(p.resolve()),
            "is_dir": p.is_dir(),
        }

    def text_present_in_window(self, title: str, text: str) -> Dict[str, Any]:
        window_texts = self.read_window_texts(title)
        if not window_texts.get("ok"):
            return window_texts

        texts = window_texts.get("texts", [])
        matched = [item for item in texts if text.lower() in str(item.get("text", "")).lower()]
        return {
            "ok": True,
            "exists": len(matched) > 0,
            "matches": matched,
        }

    def observe(
        self,
        last_tool: str | None = None,
        last_tool_ok: bool | None = None,
        last_error: str | None = None,
    ) -> WorldState:
        active_window = None
        open_windows: List[Dict[str, Any]] = []
        known_files: List[str] = []
        notes: List[str] = []

        screenshot_path = None
        annotated_screenshot_path = None
        screenshot_metadata: Dict[str, Any] = {}
        ui_elements: List[Dict[str, Any]] = []
        screen_summary = None

        windows_snapshot = self.snapshot_windows()
        if windows_snapshot.get("ok"):
            open_windows = windows_snapshot.get("windows", [])[:50]
            if open_windows:
                active_window = str(open_windows[0].get("title") or "")
        else:
            err = windows_snapshot.get("error")
            if err:
                last_error = last_error or f"observer window error: {err}"
                notes.append(str(err))

        for path_str in self.watch_paths:
            p = Path(path_str)
            if not p.exists() or not p.is_dir():
                notes.append(f"watch path unavailable: {path_str}")
                continue

            try:
                for item in list(p.iterdir())[:50]:
                    known_files.append(str(item.resolve()))
            except Exception as exc:
                notes.append(f"watch path scan failed: {path_str}: {exc}")

        if self.enable_visual_observation:
            try:
                screenshot = self.screen_capture.capture_screen(prefix="observe")
                screenshot_path = screenshot.get("path")
                screenshot_metadata = {
                    "width": screenshot.get("width"),
                    "height": screenshot.get("height"),
                    "timestamp": screenshot.get("timestamp"),
                }
                screen_summary = (
                    f"Captured desktop screenshot {screenshot.get('width')}x{screenshot.get('height')}"
                )

                grounded = self.grounding_provider.ground(screenshot_path)
                ui_elements = grounded.get("elements", [])[:200]
                annotated_screenshot_path = grounded.get("annotated_screenshot_path")
                screenshot_metadata.update(
                    {
                        "grounding_provider": grounded.get("provider"),
                        "grounded_element_count": len(ui_elements),
                    }
                )
            except Exception as exc:
                notes.append(f"visual observation unavailable: {exc}")

        return WorldState(
            active_window=active_window,
            open_windows=open_windows,
            known_files=known_files[:100],
            last_tool=last_tool,
            last_tool_ok=last_tool_ok,
            last_error=last_error,
            notes=notes,
            screenshot_path=screenshot_path,
            annotated_screenshot_path=annotated_screenshot_path,
            screenshot_metadata=screenshot_metadata,
            ui_elements=ui_elements,
            screen_summary=screen_summary,
        )
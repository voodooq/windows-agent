from __future__ import annotations

import subprocess
import time
from typing import Optional

import pyautogui
from pywinauto import Application, Desktop
from pywinauto.findwindows import ElementNotFoundError

from app.schemas.tool_result import ToolResult


def open_app(path_or_name: str) -> ToolResult:
    try:
        proc = subprocess.Popen(path_or_name, shell=True)
        return ToolResult(
            ok=True,
            output={
                "pid": proc.pid,
                "path_or_name": path_or_name,
            },
        )
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def list_windows(title_filter: Optional[str] = None) -> ToolResult:
    try:
        windows = []
        for w in Desktop(backend="uia").windows():
            try:
                title = w.window_text()
                if title_filter and title_filter.lower() not in title.lower():
                    continue
                windows.append(
                    {
                        "title": title,
                        "class_name": w.class_name(),
                        "control_type": getattr(w.element_info, "control_type", None),
                        "handle": w.handle,
                    }
                )
            except Exception:
                continue

        return ToolResult(ok=True, output={"windows": windows})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def focus_window(title: str, timeout_sec: int = 10) -> ToolResult:
    try:
        app = Application(backend="uia").connect(title_re=f".*{title}.*", timeout=timeout_sec)
        win = app.top_window()
        if win.get_show_state() == 2: # Minimized
            win.restore()
        win.set_focus()
        return ToolResult(
            ok=True,
            output={
                "title": win.window_text(),
                "handle": win.handle,
            },
        )
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def wait_for_window(title: str, timeout_sec: int = 10) -> ToolResult:
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            wins = Desktop(backend="uia").windows()
            for w in wins:
                window_title = w.window_text()
                if title.lower() in window_title.lower():
                    return ToolResult(
                        ok=True,
                        output={"title": window_title, "handle": w.handle},
                    )
        except Exception:
            pass
        time.sleep(0.5)

    return ToolResult(ok=False, error=f"window not found within {timeout_sec}s: {title}")


def type_text(text: str, interval: float = 0.02) -> ToolResult:
    try:
        pyautogui.write(text, interval=interval)
        return ToolResult(ok=True, output={"typed": text})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def press_hotkey(keys: list[str]) -> ToolResult:
    try:
        pyautogui.hotkey(*keys)
        return ToolResult(ok=True, output={"keys": keys})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def click_element(
    window_title: str,
    control_type: Optional[str] = None,
    title: Optional[str] = None,
    auto_id: Optional[str] = None,
    timeout_sec: int = 10,
) -> ToolResult:
    try:
        app = Application(backend="uia").connect(title_re=f".*{window_title}.*", timeout=timeout_sec)
        win = app.top_window()

        criteria = {}
        if control_type:
            criteria["control_type"] = control_type
        if title:
            criteria["title"] = title
        if auto_id:
            criteria["auto_id"] = auto_id

        if not criteria:
            return ToolResult(ok=False, error="at least one of control_type/title/auto_id is required")

        elem = win.child_window(**criteria)
        elem.wait("exists ready", timeout=timeout_sec)
        wrapper = elem.wrapper_object()
        wrapper.click_input()

        return ToolResult(
            ok=True,
            output={
                "window_title": win.window_text(),
                "criteria": criteria,
            },
        )
    except ElementNotFoundError as e:
        return ToolResult(ok=False, error=f"element not found: {e}")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def get_window_texts(window_title: str, timeout_sec: int = 10) -> ToolResult:
    try:
        app = Application(backend="uia").connect(title_re=f".*{window_title}.*", timeout=timeout_sec)
        win = app.top_window()

        texts = []
        descendants = win.descendants()
        for d in descendants:
            try:
                txt = d.window_text()
                if txt:
                    texts.append(
                        {
                            "text": txt,
                            "control_type": getattr(d.element_info, "control_type", None),
                            "class_name": d.class_name(),
                        }
                    )
            except Exception:
                continue

        return ToolResult(ok=True, output={"texts": texts[:200]})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))
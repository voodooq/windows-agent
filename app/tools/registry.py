from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.computer_use.controller import ComputerController
from app.computer_use.grounding import GridGroundingProvider
from app.computer_use.screen import ScreenCapture
from app.schemas.tool_result import ToolResult
from app.tools.files import create_dir, list_files, move_file, read_text, write_text
from app.tools.shell import run_command
from app.tools.windows_ui import (
    click_element,
    focus_window,
    get_window_texts,
    list_windows,
    open_app,
    press_hotkey,
    type_text,
    wait_for_window,
)


class ToolRegistry:
    def __init__(
        self,
        command_timeout_sec: int = 60,
        blocked_commands: list[str] | None = None,
        allowed_apps: list[str] | None = None,
        enable_computer_use_tools: bool = False,
        grounding_columns: int = 4,
        grounding_rows: int = 3,
        computer_pause_sec: float = 0.1,
    ):
        self.command_timeout_sec = command_timeout_sec
        self.blocked_commands = [cmd.lower() for cmd in (blocked_commands or [])]
        self.allowed_apps = [app.lower() for app in (allowed_apps or [])]
        self.enable_computer_use_tools = enable_computer_use_tools

        self.screen_capture = ScreenCapture()
        self.grounding_provider = GridGroundingProvider(
            screen_capture=self.screen_capture,
            columns=grounding_columns,
            rows=grounding_rows,
        )
        self.computer_controller = ComputerController(pause_sec=computer_pause_sec)

        self.tools: Dict[str, Callable[..., Any]] = {
            "list_files": list_files,
            "create_dir": create_dir,
            "move_file": move_file,
            "read_text": read_text,
            "write_text": write_text,
            "run_command": self._run_command_wrapper,
            "open_app": self._open_app_wrapper,
            "list_windows": list_windows,
            "focus_window": focus_window,
            "wait_for_window": wait_for_window,
            "type_text": type_text,
            "press_hotkey": press_hotkey,
            "click_element": click_element,
            "get_window_texts": get_window_texts,
        }

        if self.enable_computer_use_tools:
            self.tools.update(
                {
                    "capture_screen": self._capture_screen,
                    "ground_screen": self._ground_screen,
                    "click_box": self._click_box,
                    "move_to_box": self._move_to_box,
                    "computer_type_text": self._computer_type_text,
                    "computer_press_keys": self._computer_press_keys,
                    "computer_scroll": self._computer_scroll,
                }
            )

    def _run_command_wrapper(self, command: str):
        command_lower = command.lower()
        for blocked in self.blocked_commands:
            if blocked and blocked in command_lower:
                raise ValueError(f"blocked command by policy: {blocked}")
        return run_command(command=command, timeout_sec=self.command_timeout_sec)

    def _open_app_wrapper(self, path_or_name: str):
        normalized = path_or_name.strip().lower()
        
        # 别名映射：将通用称呼转换为系统可执行命令
        aliases = {
            "browser": "start", # Windows 'start' 配合 URL 会打开默认浏览器，单独使用可尝试打开主页
            "浏览器": "start",
            "notepad": "notepad",
            "记事本": "notepad",
            "ppt": "powerpnt",
            "powerpoint": "powerpnt",
            "excel": "excel",
            "word": "winword",
            "calc": "calc",
            "计算器": "calc"
        }
        
        if normalized in aliases:
            # 如果是浏览器，'start' 需要一个目标，这里尝试打开一个空页面或根据上下文
            target = aliases[normalized]
            if normalized in ["browser", "浏览器"]:
                # 使用 start "" "https://www.bing.com" 来启动默认浏览器并打开必应
                return open_app(path_or_name='start "" "https://www.bing.com"')
            return open_app(path_or_name=target)

        # 改进策略：允许模糊匹配。如果输入包含允许的可执行文件名，或者可执行文件名包含输入关键字
        allowed = False
        for app in self.allowed_apps:
            if app in normalized or normalized in app:
                allowed = True
                break
        
        if self.allowed_apps and not allowed:
            raise ValueError(f"app not allowed by policy: {path_or_name}")
        return open_app(path_or_name=path_or_name)

    def _capture_screen(self, prefix: str = "tool_capture") -> ToolResult:
        result = self.screen_capture.capture_screen(prefix=prefix)
        return ToolResult(ok=True, output=result)

    def _ground_screen(self, image_path: str) -> ToolResult:
        result = self.grounding_provider.ground(image_path=image_path)
        return ToolResult(ok=True, output=result)

    def _click_box(
        self,
        box_id: int,
        elements: List[Dict[str, Any]],
        button: str = "left",
        clicks: int = 1,
    ) -> ToolResult:
        result = self.computer_controller.click_box(
            box_id=box_id,
            elements=elements,
            button=button,
            clicks=clicks,
        )
        return ToolResult(ok=True, output=result)

    def _move_to_box(self, box_id: int, elements: List[Dict[str, Any]]) -> ToolResult:
        result = self.computer_controller.move_to_box(box_id=box_id, elements=elements)
        return ToolResult(ok=True, output=result)

    def _computer_type_text(self, text: str, interval: float = 0.02) -> ToolResult:
        result = self.computer_controller.type_text(text=text, interval=interval)
        return ToolResult(ok=True, output=result)

    def _computer_press_keys(self, keys: List[str]) -> ToolResult:
        result = self.computer_controller.press_keys(keys=keys)
        return ToolResult(ok=True, output=result)

    def _computer_scroll(self, clicks: int) -> ToolResult:
        result = self.computer_controller.scroll(clicks=clicks)
        return ToolResult(ok=True, output=result)

    def get_tool_specs(self) -> list[dict]:
        specs = [
            {
                "name": "list_files",
                "description": "List files in a directory",
                "args_schema": {"path": "string"},
            },
            {
                "name": "create_dir",
                "description": "Create a directory",
                "args_schema": {"path": "string"},
            },
            {
                "name": "move_file",
                "description": "Move file from src to dst",
                "args_schema": {"src": "string", "dst": "string"},
            },
            {
                "name": "read_text",
                "description": "Read text file",
                "args_schema": {"path": "string"},
            },
            {
                "name": "write_text",
                "description": "Write text file",
                "args_schema": {"path": "string", "content": "string"},
            },
            {
                "name": "run_command",
                "description": "Run shell command. Use carefully.",
                "args_schema": {"command": "string"},
            },
            {
                "name": "open_app",
                "description": "Open a Windows application by name or path",
                "args_schema": {"path_or_name": "string"},
            },
            {
                "name": "list_windows",
                "description": "List top-level windows, optionally filter by title",
                "args_schema": {"title_filter": "string|null"},
            },
            {
                "name": "focus_window",
                "description": "Focus a window by partial title",
                "args_schema": {"title": "string", "timeout_sec": "int|null"},
            },
            {
                "name": "wait_for_window",
                "description": "Wait until a window appears",
                "args_schema": {"title": "string", "timeout_sec": "int|null"},
            },
            {
                "name": "type_text",
                "description": "Type text into the active focused window",
                "args_schema": {"text": "string", "interval": "float|null"},
            },
            {
                "name": "press_hotkey",
                "description": "Press a keyboard shortcut",
                "args_schema": {"keys": "list[string]"},
            },
            {
                "name": "click_element",
                "description": "Click a UI element in a target window by title/control_type/auto_id",
                "args_schema": {
                    "window_title": "string",
                    "control_type": "string|null",
                    "title": "string|null",
                    "auto_id": "string|null",
                    "timeout_sec": "int|null",
                },
            },
            {
                "name": "get_window_texts",
                "description": "Read visible texts from a target window for verification",
                "args_schema": {"window_title": "string", "timeout_sec": "int|null"},
            },
        ]

        if self.enable_computer_use_tools:
            specs.extend(
                [
                    {
                        "name": "capture_screen",
                        "description": "Capture a desktop screenshot and store it as an artifact",
                        "args_schema": {"prefix": "string|null"},
                    },
                    {
                        "name": "ground_screen",
                        "description": "Annotate screenshot with numbered boxes for visual grounding",
                        "args_schema": {"image_path": "string"},
                    },
                    {
                        "name": "click_box",
                        "description": "Click the center point of a grounded UI box",
                        "args_schema": {
                            "box_id": "int",
                            "elements": "list[object]",
                            "button": "string|null",
                            "clicks": "int|null",
                        },
                    },
                    {
                        "name": "move_to_box",
                        "description": "Move mouse to the center point of a grounded UI box",
                        "args_schema": {"box_id": "int", "elements": "list[object]"},
                    },
                    {
                        "name": "computer_type_text",
                        "description": "Type text using computer-use controller",
                        "args_schema": {"text": "string", "interval": "float|null"},
                    },
                    {
                        "name": "computer_press_keys",
                        "description": "Press keys using computer-use controller",
                        "args_schema": {"keys": "list[string]"},
                    },
                    {
                        "name": "computer_scroll",
                        "description": "Scroll using computer-use controller",
                        "args_schema": {"clicks": "int"},
                    },
                ]
            )

        return specs

    def call(self, tool_name: str, args: dict):
        if tool_name not in self.tools:
            raise ValueError(f"unknown tool: {tool_name}")
        return self.tools[tool_name](**args)
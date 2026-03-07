from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.computer_use.visual_verifier import VisualVerifier
from app.runtime.observer import Observer
from app.schemas.failure_codes import FailureCode
from app.schemas.verification import VerificationResult
from app.schemas.world_state import WorldState


class Verifier:
    def __init__(self, observer: Observer):
        self.observer = observer
        self.visual_verifier = VisualVerifier()

    def verify_step(self, tool: str, args: Dict[str, Any], output: Dict[str, Any] | None = None) -> Dict[str, Any]:
        output = output or {}
        result = self.verify(
            step={"tool": tool, "args": args},
            tool_result={"ok": True, "output": output, "error": None},
            world_state=self.observer.observe(last_tool=tool, last_tool_ok=True),
        )
        return {
            "ok": result.ok,
            "method": result.method,
            "details": result.model_dump(),
        }

    def verify(
        self,
        step: Dict[str, Any],
        tool_result: Dict[str, Any],
        world_state: WorldState,
    ) -> VerificationResult:
        tool = step.get("tool")
        args = step.get("args", {})
        output = tool_result.get("output", {}) or {}

        if not tool_result.get("ok", False):
            return VerificationResult(
                ok=False,
                reason=tool_result.get("error") or "tool execution failed",
                failure_code=FailureCode.TOOL_EXECUTION_FAILED.value,
                evidence=[f"tool={tool} failed"],
                suggestions=["check args", "consider replanning", "retry only if safe"],
            )

        if tool == "create_dir":
            path = args.get("path")
            if path and Path(path).exists() and Path(path).is_dir():
                return VerificationResult(
                    ok=True,
                    evidence=[f"directory exists: {path}"],
                )
            return VerificationResult(
                ok=False,
                reason=f"directory not found after create_dir: {path}",
                failure_code=FailureCode.DIRECTORY_NOT_FOUND_AFTER_CREATE.value,
                suggestions=["retry create_dir", "check allowed_roots"],
            )

        if tool == "write_text":
            path = args.get("path")
            if path and Path(path).exists() and Path(path).is_file():
                return VerificationResult(
                    ok=True,
                    evidence=[f"file exists: {path}"],
                )
            return VerificationResult(
                ok=False,
                reason=f"file not found after write_text: {path}",
                failure_code=FailureCode.FILE_NOT_FOUND_AFTER_WRITE.value,
                suggestions=["retry write_text", "check parent dir"],
            )

        if tool == "move_file":
            dst = args.get("dst")
            if dst and Path(dst).exists():
                return VerificationResult(
                    ok=True,
                    evidence=[f"moved file exists at dst: {dst}"],
                )
            return VerificationResult(
                ok=False,
                reason=f"destination file not found after move_file: {dst}",
                failure_code=FailureCode.DESTINATION_NOT_FOUND_AFTER_MOVE.value,
                suggestions=["retry move_file", "check source path", "check destination path"],
            )

        if tool in {"open_app", "wait_for_window", "focus_window"}:
            title = args.get("title") or args.get("path_or_name", "")
            matched = False
            for window in world_state.open_windows:
                window_title = str(window.get("title", ""))
                if title and title.lower().replace(".exe", "") in window_title.lower():
                    matched = True
                    break

            if tool == "open_app" and tool_result.get("ok"):
                return VerificationResult(
                    ok=True,
                    evidence=["process launch command returned ok"],
                    suggestions=["prefer wait_for_window as next verification step"],
                )

            if matched:
                return VerificationResult(
                    ok=True,
                    evidence=[f"matched window title: {title}"],
                )

            return VerificationResult(
                ok=False,
                reason=f"window not verified: {title}",
                failure_code=FailureCode.WINDOW_NOT_VERIFIED.value,
                suggestions=["call list_windows", "call wait_for_window", "use more specific title"],
            )

        if tool == "get_window_texts":
            title = args.get("window_title")
            if title:
                observed = self.observer.read_window_texts(title)
                if observed.get("ok"):
                    return VerificationResult(
                        ok=True,
                        evidence=[f"retrieved texts for window: {title}"],
                    )
                return VerificationResult(
                    ok=False,
                    reason=observed.get("error") or f"failed to read texts from window: {title}",
                    failure_code=FailureCode.WINDOW_TEXT_READ_FAILED.value,
                    suggestions=["check window title", "call list_windows first"],
                )

        if tool == "capture_screen":
            screenshot_path = output.get("path")
            if screenshot_path and Path(screenshot_path).exists():
                return VerificationResult(
                    ok=True,
                    method="artifact_check",
                    evidence=[f"screenshot captured: {screenshot_path}"],
                    artifacts=[{"type": "screenshot", "path": screenshot_path}],
                )
            return VerificationResult(
                ok=False,
                reason="screenshot file missing after capture_screen",
                failure_code=FailureCode.TOOL_EXECUTION_FAILED.value,
                method="artifact_check",
            )

        if tool == "ground_screen":
            annotated_path = output.get("annotated_screenshot_path")
            elements = output.get("elements", [])
            if annotated_path and Path(annotated_path).exists() and elements:
                return VerificationResult(
                    ok=True,
                    method="artifact_check",
                    evidence=[
                        f"annotated screenshot created: {annotated_path}",
                        f"grounded elements={len(elements)}",
                    ],
                    artifacts=[{"type": "annotated_screenshot", "path": annotated_path}],
                )
            return VerificationResult(
                ok=False,
                reason="grounding output incomplete",
                failure_code=FailureCode.TOOL_EXECUTION_FAILED.value,
                method="artifact_check",
                suggestions=["capture a fresh screenshot", "retry grounding"],
            )

        if tool in {
            "click_box",
            "move_to_box",
            "computer_type_text",
            "computer_press_keys",
            "computer_scroll",
        }:
            visual_result = self.visual_verifier.verify_transition(
                before_path=args.get("before_screenshot_path") or output.get("before_screenshot_path"),
                after_path=world_state.screenshot_path or output.get("after_screenshot_path"),
                expectation=step.get("expected"),
            )
            if tool == "move_to_box" and not visual_result.ok:
                return VerificationResult(
                    ok=True,
                    method="controller_ack",
                    evidence=["mouse move acknowledged; visual diff skipped as non-fatal"],
                    suggestions=["follow with click_box or capture_screen for stronger verification"],
                )
            return visual_result

        if tool in {"type_text", "press_hotkey", "click_element", "run_command", "read_text", "list_files"}:
            return VerificationResult(
                ok=True,
                evidence=[f"default pass for tool={tool}"],
                suggestions=["add an explicit follow-up verification step for stronger guarantees"],
            )

        return VerificationResult(ok=True, evidence=[f"default pass for tool={tool}"])
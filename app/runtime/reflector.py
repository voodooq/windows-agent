from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.reflection import Reflection


class Reflector:
    def reflect(self, goal: str, execution_result: Dict[str, Any]) -> Reflection:
        steps: List[Dict[str, Any]] = execution_result.get("steps", [])
        ok = bool(execution_result.get("ok"))

        if ok:
            lessons = self._success_lessons(steps)
            memory_writes = self._memory_writes(goal=goal, steps=steps, ok=True)
            return Reflection(
                outcome="success",
                failed_step=None,
                root_causes=["all planned steps executed and passed verification"],
                lessons=lessons,
                memory_writes=memory_writes,
                should_write_memory=True,
                skill_candidate=len(steps) >= 3,
            )

        failed_step = next((step for step in steps if not step.get("ok")), None)
        failed_step_id = failed_step.get("step_id") if failed_step else None
        root_causes: List[str] = []
        lessons: List[str] = []

        if failed_step:
            tool = failed_step.get("tool")
            error = failed_step.get("error")
            verification = failed_step.get("verification", {}) or {}

            if error:
                root_causes.append(f"step {failed_step_id} failed on tool {tool}: {error}")

            if error and "approval" in str(error).lower():
                lessons.append("high-risk actions should require explicit approval or a safer alternative")
            elif verification and not verification.get("ok"):
                root_causes.append(
                    f"step {failed_step_id} did not pass verification via {verification.get('method')}"
                )
                lessons.append("use act-then-verify loops and add more explicit expected outcomes per step")
            else:
                lessons.append("prefer smaller verified steps and validate tool arguments before execution")
        else:
            root_causes.append("execution ended without a clear failed step")
            lessons.append("capture more detailed execution telemetry for diagnosis")

        memory_writes = self._memory_writes(goal=goal, steps=steps, ok=False)
        return Reflection(
            outcome="failure",
            failed_step=failed_step_id,
            root_causes=root_causes,
            lessons=lessons,
            memory_writes=memory_writes,
            should_write_memory=True,
            skill_candidate=False,
        )

    def _success_lessons(self, steps: List[Dict[str, Any]]) -> List[str]:
        lessons: List[str] = []

        used_tools = {str(step.get("tool")) for step in steps}
        if "run_command" in used_tools:
            lessons.append("prefer direct tools over shell commands when an equivalent tool exists")
        if any(tool in used_tools for tool in {"open_app", "focus_window", "type_text", "click_element"}):
            lessons.append("GUI tasks should keep a strict open-focus-act-verify order")
        if any(step.get("verification", {}).get("method") != "no_verifier" for step in steps):
            lessons.append("verification-aware execution improves reliability")
        if not lessons:
            lessons.append("small structured plans improve reliability")

        return lessons

    def _memory_writes(self, goal: str, steps: List[Dict[str, Any]], ok: bool) -> List[str]:
        writes: List[str] = []
        if ok:
            writes.append(f"Completed goal successfully: {goal}")
        else:
            writes.append(f"Task ended with failure and should be reviewed: {goal}")

        used_tools = sorted({str(step.get("tool")) for step in steps if step.get("tool")})
        if used_tools:
            writes.append(f"Tools used in this task: {', '.join(used_tools)}")

        return writes
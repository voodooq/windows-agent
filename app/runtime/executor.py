from __future__ import annotations

from typing import Any, Dict, List

from app.runtime.verifier import Verifier
from app.schemas.plan import Plan
from app.state.approval_store import ApprovalStore
from app.tools.registry import ToolRegistry


class Executor:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        verifier: Verifier,
        approval_store: ApprovalStore | None = None,
        auto_approve_medium_risk: bool = True,
        approval_policy: Dict[str, Any] | None = None,
    ):
        self.tool_registry = tool_registry
        self.verifier = verifier
        self.approval_store = approval_store or ApprovalStore()
        self.auto_approve_medium_risk = auto_approve_medium_risk
        self.approval_policy = approval_policy or {}

    def execute_plan_step(
        self,
        step,
        goal_text: str = "",
        bad_state: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        bad_state = bad_state or {}
        approval = self._check_risk(
            step=step,
            goal_text=goal_text,
            bad_state=bad_state,
        )
        if not approval["allowed"]:
            result = {
                "step_id": step.id,
                "tool": step.tool,
                "args": step.args,
                "expected": step.expected,
                "risk_level": step.risk_level,
                "ok": False,
                "error": approval["reason"],
            }
            if approval.get("approval_id"):
                result["approval_id"] = approval["approval_id"]
                result["requires_approval"] = True
            return result

        try:
            result = self.tool_registry.call(step.tool, step.args)
            return {
                "step_id": step.id,
                "tool": step.tool,
                "args": step.args,
                "expected": step.expected,
                "risk_level": step.risk_level,
                "ok": bool(result.ok),
                "output": result.output,
                "error": result.error,
            }
        except Exception as e:
            return {
                "step_id": step.id,
                "tool": step.tool,
                "args": step.args,
                "expected": step.expected,
                "risk_level": step.risk_level,
                "ok": False,
                "error": str(e),
            }

    def execute_plan(self, plan: Plan) -> Dict[str, Any]:
        step_results: List[Dict[str, Any]] = []

        for step in plan.steps:
            step_result = self.execute_plan_step(step)
            verification = self.verifier.verify_step(
                tool=step.tool,
                args=step.args,
                output=step_result.get("output"),
            )

            step_ok = bool(step_result.get("ok")) and bool(verification.get("ok"))
            step_record = {
                **step_result,
                "verification": verification,
                "ok": step_ok,
            }
            step_results.append(step_record)

            if not step_ok:
                return {
                    "ok": False,
                    "goal": plan.goal,
                    "reasoning_summary": plan.reasoning_summary,
                    "steps": step_results,
                }

        return {
            "ok": True,
            "goal": plan.goal,
            "reasoning_summary": plan.reasoning_summary,
            "steps": step_results,
        }

    def _check_risk(
        self,
        step,
        goal_text: str,
        bad_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = (step.risk_level or "low").strip().lower()
        autonomy_mode = str(bad_state.get("autonomy_mode") or "normal").strip().lower()
        recommended_action = str(bad_state.get("recommended_action") or "continue").strip().lower()
        always_require = set(
            item.strip().lower()
            for item in self.approval_policy.get("always_require_for_tools", [])
            if str(item).strip()
        )

        if step.tool.strip().lower() in always_require:
            return self._request_approval(
                step=step,
                goal_text=goal_text,
                bad_state=bad_state,
                reason=f"tool '{step.tool}' requires approval by policy",
            )

        if normalized == "low":
            if autonomy_mode == "inspect_only":
                return self._request_approval(
                    step=step,
                    goal_text=goal_text,
                    bad_state=bad_state,
                    reason="inspect_only mode requires approval for all actions",
                )
            return {"allowed": True, "reason": "low risk auto-approved"}

        if normalized == "medium":
            if autonomy_mode in {"inspect_only", "conservative"}:
                return self._request_approval(
                    step=step,
                    goal_text=goal_text,
                    bad_state=bad_state,
                    reason=f"{autonomy_mode} mode requires approval for medium risk actions",
                )
            if recommended_action == "approval_only_for_medium_and_high_risk":
                return self._request_approval(
                    step=step,
                    goal_text=goal_text,
                    bad_state=bad_state,
                    reason="bad state policy requires approval for medium risk actions",
                )
            if self.auto_approve_medium_risk:
                return {"allowed": True, "reason": "medium risk auto-approved by policy"}
            return self._request_approval(
                step=step,
                goal_text=goal_text,
                bad_state=bad_state,
                reason="medium risk action requires approval",
            )

        return self._request_approval(
            step=step,
            goal_text=goal_text,
            bad_state=bad_state,
            reason=f"{normalized} risk action requires approval",
        )

    def _request_approval(
        self,
        step,
        goal_text: str,
        bad_state: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        approval = self.approval_store.create(
            goal_text=goal_text,
            step_id=step.id,
            tool=step.tool,
            args=step.args,
            expected=step.expected,
            risk_level=step.risk_level,
            reason=reason,
            bad_state=bad_state,
            metadata={
                "autonomy_mode": bad_state.get("autonomy_mode"),
                "recommended_action": bad_state.get("recommended_action"),
            },
        )
        if approval.status == "approved":
            return {"allowed": True, "reason": "approval already granted"}

        return {
            "allowed": False,
            "reason": reason,
            "approval_id": approval.id,
        }

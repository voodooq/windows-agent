from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.config import Config, env_value
from app.llm.openai_compatible import OpenAICompatibleClient
from app.memory.manager import MemoryManager
from app.runtime.executor import Executor
from app.runtime.goal_manager import GoalManager
from app.runtime.observer import Observer
from app.runtime.planner import Planner
from app.runtime.reflector import Reflector
from app.runtime.replanner import Replanner
from app.runtime.scorer import ActionScorer
from app.runtime.state_analyzer import StateAnalyzer
from app.runtime.verifier import Verifier
from app.state.approval_store import ApprovalStore
from app.state.world_state_store import WorldStateStore
from app.tools.files import configure_allowed_roots
from app.tools.registry import ToolRegistry


class AgentRuntime:
    def __init__(self, config: Config):
        self.config = config

        llm_conf = config.llm
        api_key = env_value(llm_conf.get("api_key_env", "OPENAI_API_KEY"), "")
        base_url = env_value(llm_conf.get("base_url_env", "OPENAI_BASE_URL"), "")
        model = env_value(llm_conf.get("model_env", "OPENAI_MODEL"), "")

        if not api_key:
            raise ValueError("missing API key env value")
        if not base_url:
            raise ValueError("missing base URL env value")
        if not model:
            raise ValueError("missing model env value")

        self.llm = OpenAICompatibleClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=int(llm_conf.get("timeout", 120)),
            responses_model=bool(llm_conf.get("use_responses_api", False)),
        )

        allowed_roots = config.security.get("allowed_roots", ["./data", "./workspace"])
        configure_allowed_roots(allowed_roots)

        computer_use_conf = config.runtime.get("computer_use", {})
        enable_visual_observation = bool(computer_use_conf.get("enable_visual_observation", False))
        enable_computer_use_tools = bool(computer_use_conf.get("enable_tools", False))

        self.tool_registry = ToolRegistry(
            command_timeout_sec=int(config.runtime.get("command_timeout_sec", 60)),
            blocked_commands=config.security.get("blocked_commands", []),
            allowed_apps=config.security.get("allowed_apps", []),
            enable_computer_use_tools=enable_computer_use_tools,
            grounding_columns=int(computer_use_conf.get("grounding_columns", 4)),
            grounding_rows=int(computer_use_conf.get("grounding_rows", 3)),
            computer_pause_sec=float(computer_use_conf.get("pause_sec", 0.1)),
        )
        self.memory = MemoryManager(path="data/memory.json")
        self.observer = Observer(
            watch_paths=config.runtime.get("watch_paths", ["./workspace", "./data"]),
            enable_visual_observation=enable_visual_observation,
            screen_capture=self.tool_registry.screen_capture,
            grounding_provider=self.tool_registry.grounding_provider,
        )
        self.world_state_store = WorldStateStore(
            path=str(config.runtime.get("world_state_path", "data/world_state.json")),
        )
        self.approval_store = ApprovalStore(
            path=str(config.runtime.get("approval_store_path", "data/approvals.json")),
        )
        self.state_analyzer = StateAnalyzer()
        self.verifier = Verifier(observer=self.observer, llm=self.llm)
        self.planner = Planner(llm=self.llm, tool_registry=self.tool_registry)
        self.executor = Executor(
            tool_registry=self.tool_registry,
            verifier=self.verifier,
            approval_store=self.approval_store,
            auto_approve_medium_risk=bool(
                config.runtime.get(
                    "auto_approve_medium_risk",
                    config.runtime.get("auto_approve_low_risk", True),
                )
            ),
            approval_policy=config.runtime.get("approval_policy", {}),
        )
        self.reflector = Reflector(llm=self.llm)
        self.replanner = Replanner()
        self.scorer = ActionScorer(llm=self.llm)
        self.goal_manager = GoalManager(
            path=str(config.runtime.get("goals_path", "data/goals.json")),
        )
        self.max_goal_retries = int(config.runtime.get("max_goal_retries", 2))

    def run(self, goal: str) -> Dict[str, Any]:
        memories = self.memory.recent_task_summaries(limit=5)
        world_state_summary = self.world_state_store.build_summary(
            event_limit=int(self.config.runtime.get("max_recent_events_for_context", 5)),
            goal_limit=int(self.config.runtime.get("max_recent_goals_for_context", 5)),
            failure_limit=int(self.config.runtime.get("max_recent_failures_for_context", 5)),
            tool_limit=int(self.config.runtime.get("max_recent_tools_for_context", 5)),
            new_file_limit=int(self.config.runtime.get("max_new_files_for_context", 10)),
        )
        current_state = self.world_state_store.load()
        analyzed_bad_state = self.state_analyzer.analyze(current_state)
        if analyzed_bad_state.get("is_bad_state"):
            self.world_state_store.set_bad_state(analyzed_bad_state)
        else:
            self.world_state_store.set_bad_state({})

        plan = self.planner.create_plan(
            user_goal=goal,
            memory_summaries=memories,
            world_state_summary=world_state_summary,
        )

        step_results = []
        overall_ok = True
        replanned: Dict[str, Any] | None = None
        active_bad_state = analyzed_bad_state if analyzed_bad_state.get("is_bad_state") else {}

        for step in plan.steps:
            # Phase 3: Best-of-N Candidate Selection
            active_step_data = step.model_dump()
            if step.candidates:
                # Merge main tool/args into candidates to evaluate all options
                all_options = [{"tool": step.tool, "args": step.args}] + step.candidates
                best_option = self.scorer.select_best(
                    goal=goal,
                    actions=all_options,
                    world_state_summary=world_state_summary
                )
                active_step_data["tool"] = best_option.get("tool", step.tool)
                active_step_data["args"] = best_option.get("args", step.args)

            exec_result = self.executor.execute_plan_step(
                step, # Note: executor usually expects the object, but we've updated it
                goal_text=goal,
                bad_state=active_bad_state,
            )
            # Ensure executor uses the best selected option
            if step.candidates:
                 # We need to ensure executor uses the refined args
                 # Overwriting step object for safety
                 step.tool = active_step_data["tool"]
                 step.args = active_step_data["args"]
                 exec_result = self.executor.execute_plan_step(
                     step,
                     goal_text=goal,
                     bad_state=active_bad_state,
                 )
            observed = self.observer.observe(
                last_tool=step.tool,
                last_tool_ok=exec_result.get("ok"),
                last_error=exec_result.get("error"),
            )
            self.world_state_store.update_from_observation(
                observed,
                watched_paths=self.observer.watch_paths,
            )
            verification = self.verifier.verify(
                step=step.model_dump(),
                tool_result=exec_result,
                world_state=observed,
            )
            self.world_state_store.append_tool(
                tool_name=step.tool,
                ok=exec_result.get("ok"),
                error=exec_result.get("error"),
                failure_code=verification.failure_code,
            )

            step_ok = bool(exec_result.get("ok")) and verification.ok
            step_record = {
                "step": step.model_dump(),
                "exec_result": exec_result,
                "observed_state": observed.model_dump(),
                "verification": verification.model_dump(),
                "ok": step_ok,
            }
            step_results.append(step_record)

            if not step_ok:
                overall_ok = False
                failure_message = (
                    exec_result.get("error")
                    or verification.reason
                    or "step execution or verification failed"
                )

                if exec_result.get("requires_approval"):
                    self.world_state_store.append_failure(
                        source="agent_runtime",
                        message=failure_message,
                        context={
                            "goal": goal,
                            "tool": step.tool,
                            "step": step.model_dump(),
                            "approval_id": exec_result.get("approval_id"),
                            "recovery_mode": "approval_wait",
                        },
                        failure_code=verification.failure_code,
                    )
                    break

                replan_world_state_summary = self.world_state_store.build_summary(
                    event_limit=int(self.config.runtime.get("max_recent_events_for_context", 5)),
                    goal_limit=int(self.config.runtime.get("max_recent_goals_for_context", 5)),
                    failure_limit=int(self.config.runtime.get("max_recent_failures_for_context", 5)),
                    tool_limit=int(self.config.runtime.get("max_recent_tools_for_context", 5)),
                    new_file_limit=int(self.config.runtime.get("max_new_files_for_context", 10)),
                )
                
                # Phase 1: Call Reflector to diagnose this specific step failure
                diagnosis = self.reflector.reflect(
                    goal=goal,
                    execution_result={"steps": [step_record], "ok": False},
                    world_state_summary=replan_world_state_summary
                )
                
                replanned = self.replanner.replan(
                    goal_text=goal,
                    failed_step=step.model_dump(),
                    tool_result=exec_result,
                    verification_result=verification,
                    world_state=observed,
                    world_state_summary=replan_world_state_summary,
                    reflection_result=diagnosis,
                )
                self.world_state_store.append_failure(
                    source="agent_runtime",
                    message=failure_message,
                    context={
                        "goal": goal,
                        "tool": step.tool,
                        "step": step.model_dump(),
                        "recovery_mode": replanned.get("recovery_mode"),
                        "recovery_code": replanned.get("recovery_code"),
                    },
                    failure_code=verification.failure_code,
                )
                break

        execution_result = {
            "ok": overall_ok,
            "goal": plan.goal,
            "reasoning_summary": plan.reasoning_summary,
            "steps": step_results,
        }
        if replanned is not None:
            execution_result["replanned"] = replanned

        reflection = self.reflector.reflect(goal=goal, execution_result=execution_result)

        record = {
            "timestamp": datetime.now().isoformat(),
            "goal": goal,
            "plan": plan.model_dump(),
            "result": execution_result,
            "reflection": self.memory.build_reflection_record(reflection),
        }
        self.memory.save_task(record)

        return {
            "goal": goal,
            "plan": plan.model_dump(),
            "result": execution_result,
            "reflection": reflection.model_dump(),
        }
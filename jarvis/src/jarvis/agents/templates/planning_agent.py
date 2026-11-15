"""
Planning & Execution Agent for J.A.R.V.I.S.
Designed for complex engineering tasks requiring structured multi-step planning,
systematic tool execution, and comprehensive synthesis.
"""

import json
import time
from typing import Any, Dict, List
from jarvis.agents.base_agent import BaseAgent
from jarvis.agents.schemas import AgentRequest, AgentResponse, ExecutionStep
from jarvis.config.provider_config import ModelRole
from jarvis.llm.schemas import LLMMessage, MessageRole
from jarvis.logger import get_logger

logger = get_logger("agents.planning")


class PlanningAgent(BaseAgent):
    """Strategic planning agent executing decomposed multi-step engineering plans."""

    def __init__(self, model_role: ModelRole = ModelRole.REASONING, **kwargs: Any):
        super().__init__(template_id="planning_agent", model_role=model_role, **kwargs)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()
        messages = self.composer.compose_messages(self.template_id, request.context)
        steps: List[ExecutionStep] = []
        tools_used: List[str] = []
        tool_results_list: List[Dict[str, Any]] = []
        pending_permission: Optional[Dict[str, Any]] = None
        fallback_occurred = False
        failover_history: List[str] = []
        has_step_error = False
        last_error = None

        # 1. Step 1: Strategic Planning / Goal Decomposition
        logger.info("PlanningAgent: Formulating execution roadmap...")
        plan_response = await self.gateway.complete(
            messages=messages,
            role=self.model_role,
            temperature=0.2,
            preferred_provider_id=request.preferred_provider,
            model_id=request.model_override,
        )

        plan_content = plan_response.content or "Formulating action steps..."
        if plan_response.fallback_occurred:
            fallback_occurred = True
            failover_history.extend(plan_response.failover_history)

        step_plan = ExecutionStep(
            step_number=1,
            thought="Strategic Decomposition & Planning",
            observation=plan_content,
        )
        steps.append(step_plan)
        messages.append(LLMMessage(role=MessageRole.ASSISTANT, content=plan_content))

        # 2. Step 2: Tool-Assisted Execution Loop
        for iteration in range(request.max_iterations):
            response = await self.gateway.complete(
                messages=messages,
                role=self.model_role,
                tools=self.tools_schemas,
                temperature=request.temperature or 0.2,
                preferred_provider_id=request.preferred_provider,
                model_id=request.model_override,
            )

            if response.fallback_occurred:
                fallback_occurred = True
                failover_history.extend(response.failover_history)

            content = response.content or ""

            if not response.tool_calls:
                # Execution complete
                duration_ms = (time.perf_counter() - start_time) * 1000
                return AgentResponse(
                    answer=content,
                    agent_template=self.template_id,
                    steps=steps,
                    tools_used=tools_used,
                    provider_used=response.provider_id,
                    model_used=response.model_id,
                    fallback_occurred=fallback_occurred,
                    failover_history=failover_history,
                    execution_time_ms=round(duration_ms, 2),
                    success=not has_step_error,
                    error=last_error if has_step_error else None,
                )

            # Process tool calls
            messages.append(LLMMessage(role=MessageRole.ASSISTANT, content=content, tool_calls=response.tool_calls))
            should_break_loop = False
            for tc in response.tool_calls:
                fn_name = tc.function.name
                raw_args = tc.function.arguments
                try:
                    parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    parsed_args = {}

                actual_tool_id = (
                    parsed_args.get("tool_id")
                    if (fn_name == "execute_tool" and isinstance(parsed_args, dict))
                    else fn_name
                )
                tools_used.append(fn_name)
                if actual_tool_id != fn_name and actual_tool_id not in tools_used:
                    tools_used.append(actual_tool_id)

                handler = self._meta_tools_by_id.get(fn_name)

                step_args = (
                    parsed_args.get("arguments")
                    if (fn_name == "execute_tool" and isinstance(parsed_args, dict))
                    else parsed_args
                )

                step = ExecutionStep(
                    step_number=len(steps) + 1,
                    thought=content,
                    action_tool=actual_tool_id,
                    action_args=parsed_args,
                )

                if handler:
                    try:
                        tool_res = await handler(**parsed_args)
                        obs_str = json.dumps(tool_res)

                        if isinstance(tool_res, dict):
                            tool_results_list.append({
                                "tool_id": tool_res.get("tool_id") or actual_tool_id,
                                "success": tool_res.get("success", True),
                                "data": tool_res.get("data"),
                                "error": tool_res.get("error"),
                                "permission_denied": tool_res.get("permission_denied", False),
                                "arguments": step_args,
                            })

                            if tool_res.get("permission_denied"):
                                pending_permission = {
                                    "tool_id": actual_tool_id,
                                    "tool_name": tool_res.get("data", {}).get("tool_name", actual_tool_id) if isinstance(tool_res.get("data"), dict) else actual_tool_id,
                                    "permission_tier": tool_res.get("data", {}).get("permission_tier", "dangerous") if isinstance(tool_res.get("data"), dict) else "dangerous",
                                    "arguments": step_args,
                                    "reason": tool_res.get("error") or f"Tool '{actual_tool_id}' requires authorization",
                                }
                                should_break_loop = True

                            if tool_res.get("success") is False:
                                has_step_error = True
                                last_error = tool_res.get("error", "Tool execution reported failure")
                    except Exception as e:
                        has_step_error = True
                        last_error = str(e)
                        obs_str = json.dumps({"error": str(e), "success": False})
                        tool_results_list.append({
                            "tool_id": actual_tool_id,
                            "success": False,
                            "error": str(e),
                            "arguments": step_args,
                        })
                else:
                    has_step_error = True
                    last_error = f"Meta-tool '{fn_name}' not found"
                    obs_str = json.dumps({"error": last_error, "success": False})
                    tool_results_list.append({
                        "tool_id": actual_tool_id,
                        "success": False,
                        "error": last_error,
                        "arguments": step_args,
                    })

                step.observation = obs_str
                steps.append(step)

                messages.append(
                    LLMMessage(
                        role=MessageRole.TOOL,
                        name=fn_name,
                        content=obs_str,
                        tool_call_id=tc.id,
                    )
                )

            if should_break_loop:
                break

        # Final Synthesis
        if pending_permission:
            final_answer = (
                f"⚠️ **Authorization Required**: Execution of `{pending_permission['tool_id']}` "
                f"requires your explicit permission. Please approve or deny using the controls below, "
                f"or reply 'yes' / 'no'."
            )
            final_provider = response.provider_id
            final_model = response.model_id
        else:
            final_call = await self.gateway.complete(
                messages=messages,
                role=self.model_role,
                temperature=0.2,
                preferred_provider_id=request.preferred_provider,
                model_id=request.model_override,
            )
            final_answer = final_call.content or "Completed strategic execution."
            final_provider = final_call.provider_id
            final_model = final_call.model_id

        duration_ms = (time.perf_counter() - start_time) * 1000
        return AgentResponse(
            answer=final_answer,
            agent_template=self.template_id,
            steps=steps,
            tools_used=tools_used,
            tool_results=tool_results_list,
            pending_permission=pending_permission,
            provider_used=final_provider,
            model_used=final_model,
            fallback_occurred=fallback_occurred,
            failover_history=failover_history,
            execution_time_ms=round(duration_ms, 2),
            success=not has_step_error,
            error=last_error if has_step_error else None,
        )

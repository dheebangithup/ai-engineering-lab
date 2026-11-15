"""
Direct Conversational Agent for J.A.R.V.I.S.
Provides fast stimulus-response with optional single-turn tool invocation.
"""

import json
import time
from typing import Any, Dict, List
from jarvis.agents.base_agent import BaseAgent
from jarvis.agents.schemas import AgentRequest, AgentResponse, ExecutionStep
from jarvis.config.provider_config import ModelRole
from jarvis.llm.schemas import LLMMessage, MessageRole
from jarvis.logger import get_logger

logger = get_logger("agents.direct")


class DirectAgent(BaseAgent):
    """Direct, single-turn conversational agent."""

    def __init__(self, model_role: ModelRole = ModelRole.FAST, **kwargs: Any):
        super().__init__(template_id="direct_agent", model_role=model_role, **kwargs)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()
        messages = self.composer.compose_messages(self.template_id, request.context)
        steps: List[ExecutionStep] = []
        tools_used: List[str] = []
        tool_results_list: List[Dict[str, Any]] = []
        pending_permission: Optional[Dict[str, Any]] = None

        # 1. Initial LLM Call
        response = await self.gateway.complete(
            messages=messages,
            role=self.model_role,
            tools=self.tools_schemas,
            temperature=request.temperature or 0.3,
            preferred_provider_id=request.preferred_provider,
            model_id=request.model_override,
        )

        final_content = response.content or ""
        has_step_error = False
        last_error = None

        # 2. Handle optional tool call
        if response.tool_calls:
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
                    thought=final_content,
                    action_tool=actual_tool_id,
                    action_args=parsed_args,
                )

                if handler:
                    try:
                        tool_res = await handler(**parsed_args)
                        obs_str = json.dumps(tool_res)

                        if isinstance(tool_res, dict):
                            # Record structured result for UI
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
                    last_error = f"Unknown meta-tool '{fn_name}'"
                    obs_str = json.dumps({"error": last_error, "success": False})
                    tool_results_list.append({
                        "tool_id": actual_tool_id,
                        "success": False,
                        "error": last_error,
                        "arguments": step_args,
                    })

                step.observation = obs_str
                steps.append(step)

                # Feed observation back for final synthesis
                messages.append(LLMMessage(role=MessageRole.ASSISTANT, content=final_content, tool_calls=[tc]))
                messages.append(
                    LLMMessage(
                        role=MessageRole.TOOL,
                        name=fn_name,
                        content=step.observation,
                        tool_call_id=tc.id,
                    )
                )

            # Final response generation after tool observation
            if pending_permission:
                final_content = (
                    f"⚠️ **Authorization Required**: Execution of `{pending_permission['tool_id']}` "
                    f"requires your explicit permission. Please approve or deny using the controls below, "
                    f"or reply 'yes' / 'no'."
                )
            else:
                final_resp = await self.gateway.complete(
                    messages=messages,
                    role=self.model_role,
                    temperature=request.temperature or 0.3,
                    preferred_provider_id=request.preferred_provider,
                    model_id=request.model_override,
                )
                final_content = final_resp.content or "Completed tool execution."

        duration_ms = (time.perf_counter() - start_time) * 1000

        return AgentResponse(
            answer=final_content,
            agent_template=self.template_id,
            steps=steps,
            tools_used=tools_used,
            tool_results=tool_results_list,
            pending_permission=pending_permission,
            provider_used=response.provider_id,
            model_used=response.model_id,
            fallback_occurred=response.fallback_occurred,
            failover_history=response.failover_history,
            execution_time_ms=round(duration_ms, 2),
            success=not has_step_error,
            error=last_error if has_step_error else None,
        )

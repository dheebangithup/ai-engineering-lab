import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from jarvis.agent.llm import chat_llm
from jarvis.agent.supervisor.state import (
    AgentStatus,
    SupervisorState,
    WorkerType,
)


class SupervisorDecision(BaseModel):
    is_ambiguous: bool = Field(
        description="True if the user's task is missing essential parameters, ambiguous, or needs clarification before executing."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Specific, concise question to ask the user if is_ambiguous is True."
    )
    pattern: str = Field(
        description="Selected pattern: 'direct' (conceptual/conversational, no tools), 'fast_react' (simple single-step tool read/list/command), or 'reflexion' (complex coding/multi-step/testing)."
    )
    reasoning: str = Field(
        description="Reasoning for selecting this pattern or requesting clarification."
    )


SUPERVISOR_SYSTEM_PROMPT = """You are the EXECUTIVE SUPERVISOR of the J.A.R.V.I.S. multi-agent system.
Your job is to manage sub-agents, interact with the user, and orchestrate task execution.

Decision Guidelines:
1. Clarification & Counter-Questions:
   - If the user request is ambiguous, vague, or missing critical details (e.g. "delete files", "process data", "run the script" without specifying what or where), mark is_ambiguous=True and formulate a polite counter-question.
   - If the task is sufficiently clear to begin, mark is_ambiguous=False.

2. Pattern Selection (when is_ambiguous=False):
   - 'direct': Pure conversational questions, greeting, or explanations of concepts where NO tools (files, bash, commands) are needed.
   - 'fast_react': Simple, deterministic tasks needing 1-2 tool calls without iterative verification (e.g., read a file, list files in a folder, check date, whoami, simple search).
   - 'reflexion': Complex multi-step tasks, code writing, script execution, file generation with verification, or tasks that benefit from planning, evaluation, and self-correction.
"""


def _classify_task(task: str, conversation_history: list) -> SupervisorDecision:
    """Classify task and decide pattern or clarification."""
    prompt = f"""Conversation history:
{json.dumps(conversation_history, indent=2)}

Current User Request:
{task}

Analyze the request and decide the appropriate next step.
"""
    try:
        structured_llm = chat_llm.with_structured_output(SupervisorDecision)
        decision = structured_llm.invoke([
            {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        if isinstance(decision, SupervisorDecision):
            return decision
    except Exception:
        pass

    # Fallback heuristic parser
    heuristic_prompt = f"""{SUPERVISOR_SYSTEM_PROMPT}

{prompt}

Respond ONLY with valid JSON in this exact structure:
{{
  "is_ambiguous": false,
  "clarification_question": null,
  "pattern": "fast_react",
  "reasoning": "brief explanation"
}}
"""
    try:
        raw = chat_llm.invoke([{"role": "user", "content": heuristic_prompt}])
        text = raw.content if hasattr(raw, "content") else str(raw)
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in clean:
            clean = clean.split("```", 1)[1].split("```", 1)[0].strip()
        data = json.loads(clean)
        return SupervisorDecision(**data)
    except Exception:
        # Safe default: if tools likely needed, use fast_react, else direct
        lower = task.lower()
        if any(w in lower for w in ("create", "write", "code", "script", "test", "verify", "fix", "debug")):
            return SupervisorDecision(
                is_ambiguous=False,
                clarification_question=None,
                pattern="reflexion",
                reasoning="Task contains multi-step creation/verification keywords.",
            )
        elif any(w in lower for w in ("read", "list", "search", "run", "check", "whoami")):
            return SupervisorDecision(
                is_ambiguous=False,
                clarification_question=None,
                pattern="fast_react",
                reasoning="Task appears to be a direct tool lookup.",
            )
        else:
            return SupervisorDecision(
                is_ambiguous=False,
                clarification_question=None,
                pattern="direct",
                reasoning="General question or conversation.",
            )


def supervisor_node(state: SupervisorState) -> dict:
    """
    Central brain of the supervisor agent.
    Evaluates state, handles human clarifications/approvals, and delegates to workers.
    """
    task = state["task"]
    iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", 5)
    worker_result = state.get("worker_result")
    history = state.get("conversation_history", [])
    human_response = state.get("human_input_response")

    # 1. User provided feedback/answer to a previous clarification or approval
    if human_response:
        updated_history = list(history) + [
            {"role": "assistant", "content": state.get("human_input_prompt", "")},
            {"role": "user", "content": human_response},
        ]
        clarified_task = f"{task}\nAdditional user context: {human_response}"
        decision = _classify_task(clarified_task, updated_history)

        if decision.is_ambiguous and decision.clarification_question:
            return {
                "iteration": iteration,
                "task": clarified_task,
                "conversation_history": [
                    {"role": "assistant", "content": state.get("human_input_prompt", "")},
                    {"role": "user", "content": human_response},
                ],
                "status": AgentStatus.NEED_HUMAN_INPUT,
                "human_input_prompt": decision.clarification_question,
                "human_input_response": None,
                "selected_worker": None,
                "worker_result": None,
            }

        return {
            "iteration": iteration,
            "task": clarified_task,
            "conversation_history": [
                {"role": "assistant", "content": state.get("human_input_prompt", "")},
                {"role": "user", "content": human_response},
            ],
            "status": AgentStatus.RUNNING,
            "selected_worker": decision.pattern,
            "routing_reason": decision.reasoning,
            "human_input_prompt": None,
            "human_input_response": None,
            "worker_result": None,
        }

    # 2. A sub-agent has executed and reported its WorkerResult
    if worker_result:
        status_val = worker_result.get("status")
        recorded_history = [worker_result]

        # Case 2a: Sub-agent requested human input or approval mid-execution
        if status_val == AgentStatus.NEED_HUMAN_INPUT.value or worker_result.get("needs_human_input"):
            return {
                "iteration": iteration,
                "status": AgentStatus.NEED_HUMAN_INPUT,
                "human_input_prompt": worker_result.get("human_prompt") or "Worker requested human confirmation.",
                "worker_history": recorded_history,
                "worker_result": None,
            }

        # Case 2b: Sub-agent completed successfully
        if status_val == AgentStatus.COMPLETED.value:
            outcome = worker_result.get("outcome", "")
            return {
                "iteration": iteration,
                "status": AgentStatus.COMPLETED,
                "final_response": outcome,
                "worker_history": recorded_history,
            }

        # Case 2c: Sub-agent encountered an error
        if status_val == AgentStatus.ERROR.value:
            current_worker = worker_result.get("worker")
            # If Fast ReAct failed, auto-escalate to Reflexion for self-correcting retry
            if current_worker == WorkerType.FAST_REACT.value and iteration < max_iterations:
                return {
                    "iteration": iteration,
                    "status": AgentStatus.RUNNING,
                    "selected_worker": WorkerType.REFLEXION.value,
                    "routing_reason": f"Escalated to reflexion worker following fast_react error: {worker_result.get('error')}",
                    "worker_history": recorded_history,
                    "worker_result": None,
                }
            # Otherwise ask human for guidance or terminate
            return {
                "iteration": iteration,
                "status": AgentStatus.ERROR,
                "final_response": f"Task failed during {current_worker} execution: {worker_result.get('error', 'Unknown error')}",
                "worker_history": recorded_history,
            }

    # 3. Fresh task arrival (Entry point)
    decision = _classify_task(task, history)

    if decision.is_ambiguous and decision.clarification_question:
        return {
            "iteration": iteration,
            "status": AgentStatus.NEED_HUMAN_INPUT,
            "human_input_prompt": decision.clarification_question,
            "selected_worker": None,
            "routing_reason": decision.reasoning,
        }

    return {
        "iteration": iteration,
        "status": AgentStatus.RUNNING,
        "selected_worker": decision.pattern,
        "routing_reason": decision.reasoning,
        "human_input_prompt": None,
    }

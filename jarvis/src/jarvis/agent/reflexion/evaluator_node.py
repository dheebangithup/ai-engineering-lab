from langchain_core.prompts import ChatPromptTemplate

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import EvaluationVerdict, EvaluatorState, ReflexionState
from jarvis.logger import get_logger

logger = get_logger("reflexion.evaluator")

FAILURE_INDICATOR_KEYWORDS = frozenset({"error", "failed", "failure", "exception", "traceback"})

SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are the objective evaluation component of a Reflexion agent.

Task: {task}
Original Plan: {plan}
Execution Outcome: {execution_outcome}
Execution Events: {execution_events}

Evaluate the task and learning opportunity independently.

1. Set verdict to SUCCESS only if the outcome satisfies the task.
2. Consider validation findings when assessing correctness.
3. Inspect execution events for meaningful, reusable lessons.
4. A recovered error does not automatically mean task failure.
5. Do not infer that a tool result is correct merely because the tool
   completed successfully.
6. Set has_reusable_lesson to true only when the evidence supports
   a lesson that could improve future tasks.
7. Do not treat every transient error as a reusable lesson.
8. Explain both decisions concisely.
"""
    )
])


def evaluator_node(state: ReflexionState) -> dict:
    logger.info("Reflexion evaluator assessing task outcome...")
    task = state.get("task", "")
    plan = state.get("plan", "")
    outcome = state.get("execution_outcome", "")
    events = state.get("execution_events", []) or []

    try:
        evaluator_llm = chat_llm.with_structured_output(EvaluatorState)

        prompt = SYSTEM_PROMPT.invoke({
            "task": task,
            "plan": plan,
            "execution_outcome": outcome,
            "execution_events": events,
        })

        response = evaluator_llm.invoke(prompt)
        if isinstance(response, EvaluatorState):
            eval_result = response
        elif isinstance(response, dict):
            eval_result = EvaluatorState(**response)
        else:
            raise ValueError(f"Unexpected evaluator response type: {type(response)}")

    except Exception as e:
        logger.warning(
            f"Reflexion evaluator structured call failed: {e}. Executing heuristic evaluation fallback.",
            exc_info=True,
        )
        outcome_lower = str(outcome).lower()
        is_failure = any(w in outcome_lower for w in FAILURE_INDICATOR_KEYWORDS) or not str(outcome).strip()
        eval_result = EvaluatorState(
            verdict=EvaluationVerdict.FAILURE.value if is_failure else EvaluationVerdict.SUCCESS.value,
            analysis=f"Heuristic fallback: outcome is {'failed' if is_failure else 'successful'}.",
            reason=f"Heuristic assessment following LLM evaluation failure: {str(e)}",
            has_reusable_lesson=is_failure,
            learning_reason="Investigate execution logs for errors." if is_failure else "No reusable lesson.",
        )

    verdict = eval_result.verdict
    logger.info(f"Reflexion evaluation verdict: {verdict}. Reason: {eval_result.reason}")

    return {
        "evaluation": eval_result,
    }
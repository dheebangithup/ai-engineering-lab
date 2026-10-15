from langchain_core.prompts import ChatPromptTemplate

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import EvaluationVerdict, ReflexionState
from jarvis.logger import get_logger

logger = get_logger("reflexion.reflection")

SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are the reflection component of a Reflexion agent.

Your responsibility is to analyze the evaluator's findings and produce
a concise, actionable lesson that improves future planning.

### Context

Task:
{task}

Plan:
{plan}

Execution Outcome:
{execution_outcome}

Evaluation Verdict:
{verdict}

Evaluation Analysis:
{analysis}

Evaluation Reason:
{reason}

Reusable Lesson:
{has_reusable_lesson}

Learning Reason:
{learning_reason}

### Instructions

1. Use the evaluator's findings as the primary evidence.
2. If the verdict is FAILURE:
   - Identify what went wrong and its root cause.
   - Explain what the planner should change in the next trial.
3. If the verdict is SUCCESS:
   - Do not invent a failure.
   - If a reusable lesson exists, identify the successful strategy
     or constraint that should be retained for future tasks.
   - If no reusable lesson exists, explain that no actionable,
     reusable lesson was established.
4. Respect has_reusable_lesson and learning_reason.
   Do not manufacture a reusable lesson when the evidence does not
   support one.
5. Do not repeat the entire execution outcome or rewrite the solution.
6. Keep the diagnostic analysis concise.
7. When a reusable lesson is justified, make it specific and actionable.

### Output Format

Return exactly these two sections:

<diagnostic_analysis>
What happened: ...
Why it happened or what the evidence establishes: ...
Recommended adjustment or retained strategy: ...
</diagnostic_analysis>

<reflection>
A concise, actionable lesson for future planning.
</reflection>
"""
    )
])


def reflection_node(state: ReflexionState) -> dict:
    evaluation = state.get("evaluation") if isinstance(state, dict) else None
    if evaluation:
        if isinstance(evaluation, dict):
            verdict = evaluation.get("verdict", EvaluationVerdict.FAILURE.value)
            analysis = evaluation.get("analysis", "")
            reason = evaluation.get("reason", "")
            has_reusable_lesson = evaluation.get("has_reusable_lesson", False)
            learning_reason = evaluation.get("learning_reason", "")
        else:
            verdict = getattr(evaluation, "verdict", EvaluationVerdict.FAILURE.value)
            analysis = getattr(evaluation, "analysis", "")
            reason = getattr(evaluation, "reason", "")
            has_reusable_lesson = getattr(evaluation, "has_reusable_lesson", False)
            learning_reason = getattr(evaluation, "learning_reason", "")
    else:
        verdict = EvaluationVerdict.FAILURE.value
        analysis = "No evaluation available."
        reason = "Missing evaluation state."
        has_reusable_lesson = False
        learning_reason = ""

    task = state.get("task", "") if isinstance(state, dict) else ""
    plan = state.get("plan", "") if isinstance(state, dict) else ""
    outcome = state.get("execution_outcome", "") if isinstance(state, dict) else ""

    logger.info(f"Reflexion reflection node generating feedback (verdict={verdict})...")

    try:
        response = chat_llm.invoke(
            SYSTEM_PROMPT.format(
                task=task,
                plan=plan,
                execution_outcome=outcome,
                verdict=verdict,
                analysis=analysis,
                reason=reason,
                has_reusable_lesson=has_reusable_lesson,
                learning_reason=learning_reason,
            )
        )
        reflection_text = response.content if hasattr(response, "content") else str(response)
        logger.info("Reflexion reflection feedback recorded to memory.")
    except Exception as e:
        logger.error(f"Reflexion reflection failed: {e}. Using fallback reflection feedback.", exc_info=True)
        reflection_text = (
            f"<diagnostic_analysis>\n"
            f"What happened: Prior trial evaluation verdict was {verdict}.\n"
            f"Why it happened: {reason or 'Execution encountered unexpected issues.'}\n"
            f"Recommended adjustment: Simplify actions and verify tool outputs step-by-step.\n"
            f"</diagnostic_analysis>\n"
            f"<reflection>\n"
            f"Avoid repeating previous errors. Prioritize direct, robust tool operations.\n"
            f"</reflection>"
        )

    return {
        "reflection": reflection_text,
        "reflexion_memeory": [reflection_text],
    }

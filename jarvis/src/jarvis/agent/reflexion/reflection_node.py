from langchain_core.prompts import ChatPromptTemplate

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import ReflexionState

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
    evaluation = state["evaluation"]

    response = chat_llm.invoke(
        SYSTEM_PROMPT.format(
            task=state["task"],
            plan=state["plan"],
            execution_outcome=state["execution_outcome"],
            verdict=evaluation.verdict,
            analysis=evaluation.analysis,
            reason=evaluation.reason,
            has_reusable_lesson=evaluation.has_reusable_lesson,
            learning_reason=evaluation.learning_reason,
        )
    )

    reflection_text = response.content

    return {
        "reflection": reflection_text,
        "reflexion_memeory": [reflection_text],
    }

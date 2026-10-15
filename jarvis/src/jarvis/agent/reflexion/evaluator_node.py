from langchain_core.prompts import ChatPromptTemplate

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import EvaluatorState, ReflexionState

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
    evaluator_llm = chat_llm.with_structured_output(EvaluatorState)

    prompt = SYSTEM_PROMPT.invoke({
        "task": state["task"],
        "plan": state["plan"],
        "execution_outcome": state["execution_outcome"],
        "execution_events": state.get("execution_events", []),
    })

    response = evaluator_llm.invoke(prompt)

    return {
        "evaluation": response,
    }
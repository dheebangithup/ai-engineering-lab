from langchain_core.prompts import ChatPromptTemplate

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import ReflexionState
from jarvis.logger import get_logger

logger = get_logger("reflexion.planner")

SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are the primary planning component of a Reflexion agent. Your job is to construct a step-by-step strategy to accomplish the user's task.

### Context
- **Task:** {task}

### Past Reflections Memory
{reflexion_memeory}

### Instructions
1. Review the task thoroughly.
2. If past reflections are present above, carefully inspect them to understand what strategies failed in prior trials and why. Make it a priority to adjust your strategy to avoid repeating those specific mistakes.
3. If no past reflections are present, design your optimal initial strategy from scratch.
4. Output your final strategy clearly inside the `<plan>` tags.

### Output Format
<plan>
1. [First sequential step]
2. [Second sequential step]
...
</plan>

""")
])


def planner_node(state: ReflexionState) -> dict:
    """
    Constructs an updated or initial plan based on task and prior reflections.
    Falls back gracefully to a robust default plan if LLM call encounters an error.
    """
    trial = state.get("trial_number", 0) + 1
    task = state.get("task", "")
    logger.info(f"Reflexion planner generating strategy for trial {trial}...")

    try:
        if not state.get("reflexion_memeory"):
            memory_context = "This is the first trial. There are no past failures or reflections to analyze."
        else:
            memory_context = "\n".join(
                f"Trial {i+1} Reflection:\n{ref}"
                for i, ref in enumerate(state.get("reflexion_memeory", []))
            )

        formatted_prompt = SYSTEM_PROMPT.format(
            task=task,
            reflexion_memeory=memory_context,
        )
        response = chat_llm.invoke(formatted_prompt)
        plan_content = response.content if hasattr(response, "content") else str(response)
        logger.info(f"Reflexion planner completed plan for trial {trial}")
    except Exception as e:
        logger.error(f"Reflexion planner encountered an error: {e}. Using fallback default plan.", exc_info=True)
        plan_content = (
            f"<plan>\n"
            f"1. Analyze requirements for: {task}\n"
            f"2. Execute necessary actions using available tools.\n"
            f"3. Verify and report outcome.\n"
            f"</plan>"
        )

    return {
        "plan": plan_content,
        "trial_number": trial,
    }
from langchain_core.prompts import ChatPromptTemplate

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import ReflexionState
from jarvis.logger import get_logger

logger = get_logger("reflexion.answer")

SYSTEM_PROMPT = ChatPromptTemplate.from_messages(
    ("system", """You are the final synthesis component of a Reflexion agent. The system has reached its maximum trial budget without achieving a flawless evaluation success metric. Your objective is to salvage the high-value components of past attempts, account for known limitations, and construct the absolute best possible final output.

### Context
- **Original Task:** {task}
- **Latest Execution Outcome:** {execution_outcome}
- **Historical Reflection Logs:** 
{reflexion_memeory}

### Instructions
1. Review the original task alongside the latest outcome and the chronological reflection logs.
2. Formulate your final response by building upon the elements that were proven successful across trials, while deliberately stripping out mechanisms known to cause failures.
3. If specific constraints could not be fully met due to system or environment limitations, be entirely transparent and explicit about these gaps.
4. Output your transparent analytical summary inside `<synthesis_meta>` tags.
5. Output the definitive final user-facing response inside `<final_answer>` tags.

### Output Format
Follow this structure exactly:

<synthesis_meta>
- Working Elements: [Briefly list what successfully works in this final version]
- Known Limitations/Uncertainties: [State clearly what parts of the task remain unfulfilled or unverified]
</synthesis_meta>

<final_answer>
[Provide the clean, completed, and optimized final response or code asset for the user.]
</final_answer>
""")
)


def answer_node(state: ReflexionState) -> dict:
    """
    Synthesize final response from execution history and past reflections.
    """
    logger.info("Reflexion answer node synthesizing final best response...")
    task = state.get("task", "") if isinstance(state, dict) else ""
    outcome = state.get("execution_outcome", "") if isinstance(state, dict) else ""
    mem = state.get("reflexion_memeory", []) if isinstance(state, dict) else []

    if not mem:
        memory_context = "This is the first trial. There are no past failures or reflections to analyze."
    else:
        memory_context = "\n".join(
            f"Trial {i+1} Reflection:\n{ref}"
            for i, ref in enumerate(mem)
        )

    try:
        response = chat_llm.invoke(
            SYSTEM_PROMPT.format(
                task=task,
                execution_outcome=outcome,
                reflexion_memeory=memory_context,
            )
        )
        answer_text = response.content if hasattr(response, "content") else str(response)
        logger.info("Reflexion answer node synthesis completed.")
    except Exception as e:
        logger.error(f"Reflexion answer synthesis failed: {e}. Returning latest outcome.", exc_info=True)
        answer_text = (
            f"<final_answer>\n"
            f"{outcome or 'Execution completed. Details recorded in execution events.'}\n"
            f"</final_answer>"
        )

    return {
        "reflection": answer_text,
        "trial_number": state.get("trial_number", 1) if isinstance(state, dict) else 1,
    }

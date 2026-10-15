from langchain_core.prompts import ChatPromptTemplate

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import ReflexionState

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
    if not state.get("reflexion_memeory"):
        memory_context = "This is the first trial. There are no past failures or reflections to analyze."
    else:
        memory_context = "\n".join(
            f"Trial {i+1} Reflection:\n{ref}"
            for i, ref in enumerate(state["reflexion_memeory"])
        )

    response = chat_llm.invoke(
        SYSTEM_PROMPT.format(
            task=state["task"],
            execution_outcome=state["execution_outcome"],
            reflexion_memeory=memory_context,
        )
    )

    return {
        "reflection": response.content,
        "trial_number": state.get("trial_number", 1),
    }

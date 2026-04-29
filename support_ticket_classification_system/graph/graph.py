"""
LangGraph entry point — Support Ticket Classification Pipeline.

Flow: START → llm_node → END

Middleware stack (applied via decorators):
  @pii_middleware     — redacts PII before LLM, restores after
  @security_guardrails — blocks prompt injection attempts
"""

from langgraph.graph import StateGraph, START, END

from support_ticket_classification_system.graph.state import TicketState
from support_ticket_classification_system.graph.middleware import pii_middleware
from support_ticket_classification_system.graph.guardrails import security_guardrails
from support_ticket_classification_system.services.llm_provider import classify_ticket
from support_ticket_classification_system.core.config import Settings


@pii_middleware
@security_guardrails
def llm_node(state: TicketState) -> TicketState:
    """
    Core classification node.
    Calls the real LLM provider with retry, validation, and cost tracking.
    """
    text = state.get("text", "")
    prompt_version = state.get("prompt_version") or Settings.DEFAULT_PROMPT_VERSION

    # ── Call the LLM classification engine ──
    result = classify_ticket(text, prompt_version)

    # ── Map result back into graph state ──
    state["llm_output"] = result["output"]
    state["validated"] = result["validated"]
    state["cost"] = result["cost"]
    state["retry_count"] = result["retry_count"]
    state["prompt_version"] = result["prompt_version"]

    return state


# ── Build the graph ──
graph = StateGraph(TicketState)
graph.add_node("llm_node", llm_node)
graph.add_edge(START, "llm_node")
graph.add_edge("llm_node", END)

app = graph.compile()

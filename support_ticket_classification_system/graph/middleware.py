import re
import uuid
from typing import Callable, Any
from support_ticket_classification_system.graph.state import TicketState

PII_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "PHONE": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "CREDIT_CARD": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "ACCOUNT_NUMBER": r"\b\d{9,16}\b",
    "PASSPORT": r"\b[A-Za-z]{1,2}\d{7}\b",
    "IP": r"\b\d{1,3}(?:\.\d{1,3}){3}\b"
}

def mask_pii(text: str):
    """
    Detects and masks PII.
    Returns:
        masked_text
        pii_map (for restoration)
    """
    pii_map = {}
    masked_text = text

    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)

        for match in matches:
            placeholder = f"[{pii_type}_{uuid.uuid4().hex[:6]}]"
            pii_map[placeholder] = match
            masked_text = masked_text.replace(match, placeholder, 1)

    return masked_text, pii_map


def restore_pii(text: str, pii_map: dict):
    """
    Restores masked PII back to its original values.
    """
    for placeholder, original in pii_map.items():
        text = text.replace(placeholder, original)
    return text


def pii_middleware(node_func: Callable[[TicketState], TicketState]) -> Callable[[TicketState], TicketState]:
    """
    Middleware decorator for LangGraph nodes.
    It redacts PII before the wrapped node executes and restores it after.
    """
    def wrapper(state: TicketState) -> TicketState:
        # --- BEFORE MODEL EXECUTION (Redaction) ---
        original_text = state.get("text", "")
        masked_text, local_pii_map = mask_pii(original_text)
        
        state["pii_detected"] = len(local_pii_map) > 0
        state["text"] = masked_text  # replace before passing to LLM
        
        # --- EXECUTE THE TARGET NODE ---
        new_state = node_func(state)
        
        # --- AFTER MODEL EXECUTION (Restoration) ---
        # Restore any PII in the generated LLM output using the local map
        if new_state.get("llm_output"):
            for key, value in new_state["llm_output"].items():
                if isinstance(value, str):
                    new_state["llm_output"][key] = restore_pii(value, local_pii_map)
                    
        return new_state
        
    return wrapper

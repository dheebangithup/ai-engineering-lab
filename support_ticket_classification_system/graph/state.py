from typing import TypedDict, Optional, Dict


class TicketState(TypedDict):
    text: str
    prompt_version: str
    pii_detected: bool
    injection_detected: bool
    llm_output: Optional[dict]
    validated: bool
    route: Optional[str]
    # Cost & usage tracking
    cost: Optional[dict]       # {prompt_tokens, completion_tokens, total_tokens, estimated_cost}
    retry_count: int           # number of LLM attempts needed
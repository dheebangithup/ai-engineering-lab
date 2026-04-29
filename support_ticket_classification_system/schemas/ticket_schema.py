from typing import TypedDict, Optional


class TicketResponse(TypedDict):
    """Full response schema for the ticket classification pipeline."""
    category: str
    priority: str
    assigned_team: str
    sentiment: str
    confidence_score: float
    prompt_version: str
    pii_detected: bool
    injection_detected: bool
    output: Optional[dict]
    validated: bool
    route: Optional[str]
    # Cost & usage tracking
    cost: Optional[dict]
    retry_count: int
"""
Pydantic-based validation layer for LLM classification output.
Ensures the LLM response conforms to the expected schema before
it is accepted into the pipeline state.
"""

import logging
from typing import Tuple, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ── Valid enum values (kept in sync with prompt_registry.py) ──
VALID_CATEGORIES = {
    "Billing", "Technical Support", "Account Access",
    "General Inquiry", "Bug Report", "Feature Request",
}
VALID_PRIORITIES = {"Low", "Medium", "High"}
VALID_SENTIMENTS = {"Positive", "Neutral", "Negative"}
VALID_TEAMS = {
    "Billing Team", "Technical Team", "Account Team",
    "General Support", "Engineering Team",
}


class TicketClassification(BaseModel):
    """Strict Pydantic model for validating LLM classification output."""

    category: str = Field(..., description="Ticket category")
    priority: str = Field(..., description="Priority level")
    assigned_team: str = Field(..., description="Team assignment")
    sentiment: str = Field(..., description="Customer sentiment")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0-1")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        # Accept case-insensitive matches and normalize
        for valid in VALID_CATEGORIES:
            if v.strip().lower() == valid.lower():
                return valid
        raise ValueError(f"Invalid category '{v}'. Must be one of: {VALID_CATEGORIES}")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        for valid in VALID_PRIORITIES:
            if v.strip().lower() == valid.lower():
                return valid
        raise ValueError(f"Invalid priority '{v}'. Must be one of: {VALID_PRIORITIES}")

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str) -> str:
        for valid in VALID_SENTIMENTS:
            if v.strip().lower() == valid.lower():
                return valid
        raise ValueError(f"Invalid sentiment '{v}'. Must be one of: {VALID_SENTIMENTS}")

    @field_validator("assigned_team")
    @classmethod
    def validate_team(cls, v: str) -> str:
        for valid in VALID_TEAMS:
            if v.strip().lower() == valid.lower():
                return valid
        raise ValueError(f"Invalid team '{v}'. Must be one of: {VALID_TEAMS}")


def validate_output(raw_dict: dict) -> Tuple[Optional[dict], bool, Optional[str]]:
    """
    Validate raw LLM output against the TicketClassification schema.

    Returns:
        (validated_dict, is_valid, error_message)
    """
    try:
        validated = TicketClassification(**raw_dict)
        return validated.model_dump(), True, None
    except Exception as e:
        error_msg = str(e)
        logger.warning("Validation failed: %s", error_msg)
        return None, False, error_msg

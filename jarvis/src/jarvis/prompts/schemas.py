"""
Schemas for the J.A.R.V.I.S. Prompt Hub.
Defines template structures and runtime prompt context injection.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Specification of an agent archetype prompt template."""
    template_id: str
    name: str
    description: str
    system_instructions: str
    response_guidelines: List[str] = Field(default_factory=list)
    default_role: str = "assistant"


class PromptContext(BaseModel):
    """Dynamic context injected into system and user prompts at runtime."""
    query: str
    memory_context: Optional[str] = None
    tools_summary: Optional[str] = None
    workspace_path: Optional[str] = None
    session_history: List[Dict[str, Any]] = Field(default_factory=list)
    custom_instructions: Optional[str] = None

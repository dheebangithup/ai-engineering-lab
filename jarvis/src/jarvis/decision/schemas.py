"""
Schemas for the Decision Engine and Complexity Router.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskComplexity(str, Enum):
    SIMPLE = "simple"           # Single-shot, conversational or direct tool call
    MODERATE = "moderate"       # Single agent with 2-3 step tool loop
    COMPLEX = "complex"         # Requires planning, multi-step reflection, decomposition


class TaskIntent(str, Enum):
    CONVERSATION = "conversation"
    WEB_SEARCH = "web_search"
    FILE_PROCESSING = "file_processing"
    CODE_DEV = "code_dev"
    SYSTEM_COMMAND = "system_command"
    MEMORY_QUERY = "memory_query"
    PLANNING = "planning"
    UNKNOWN = "unknown"


class TaskClassification(BaseModel):
    """Structured decision output produced by the Decision Engine."""
    complexity: TaskComplexity = TaskComplexity.SIMPLE
    intent: TaskIntent = TaskIntent.CONVERSATION
    requires_planning: bool = False
    requires_memory_recall: bool = True
    requires_memory_ingest: bool = Field(default=False, description="True if query contains durable facts, preferences, or profile info worth remembering")
    suggested_agent: str = Field(default="direct_agent", description="Agent template identifier to route to")
    suggested_tool_categories: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = ""
    extracted_entities: List[str] = Field(default_factory=list)
    fast_path: bool = Field(default=False, description="True if decided via zero-LLM heuristics")

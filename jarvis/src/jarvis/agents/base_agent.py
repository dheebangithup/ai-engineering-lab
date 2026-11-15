"""
Abstract Base Agent interface for J.A.R.V.I.S.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from jarvis.agents.schemas import AgentRequest, AgentResponse
from jarvis.config.provider_config import ModelRole
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.prompts.prompt_composer import PromptComposer
from jarvis.tools.tool_gateway import ToolsGateway


class BaseAgent(ABC):
    """Abstract interface implemented by all J.A.R.V.I.S. agent archetypes."""

    def __init__(
        self,
        template_id: str,
        provider_gateway: ProviderGateway,
        tools_gateway: ToolsGateway,
        prompt_composer: PromptComposer,
        meta_tools: List[Callable],
        model_role: ModelRole = ModelRole.FAST,
    ):
        self.template_id = template_id
        self.gateway = provider_gateway
        self.tools_gateway = tools_gateway
        self.composer = prompt_composer
        self.meta_tools = meta_tools
        self.model_role = model_role

        # Build OpenAI function schemas for the 3 meta-tools
        self.tools_schemas = [
            fn._jarvis_tool_def.to_openai_schema()
            for fn in self.meta_tools
            if hasattr(fn, "_jarvis_tool_def")
        ]
        self._meta_tools_by_id = {
            fn._jarvis_tool_def.tool_id: fn
            for fn in self.meta_tools
            if hasattr(fn, "_jarvis_tool_def")
        }

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute the agent loop and return the standardized response."""
        pass

    # =========================================================================
    # Default Mandatory Memory Substrate Operations (Recall, Ingest, Edit, Feedback)
    # =========================================================================

    async def recall_memory(self, query: str, top_k: int = 3) -> Optional[str]:
        """Recall relevant historical facts, preferences, and runbooks (<15ms)."""
        if not self.tools_gateway.registry.get_definition("memory_recall"):
            return None
        res = await self.tools_gateway.execute_tool("memory_recall", {"query": query, "top_k": top_k})
        if res.success and res.data:
            return res.data.get("output") if isinstance(res.data, dict) else str(res.data)
        return None

    async def ingest_memory(self, raw_text: str) -> bool:
        """Autonomously persist new user facts, identity, preferences, or tech stack."""
        if not self.tools_gateway.registry.get_definition("memory_ingest"):
            return False
        res = await self.tools_gateway.execute_tool("memory_ingest", {"raw_text": raw_text})
        return res.success

    async def edit_memory(self, target_id_or_name: str, instruction: str, pillar: str = "semantic") -> bool:
        """Update or correct existing memories or procedural runbooks when information changes."""
        if not self.tools_gateway.registry.get_definition("memory_edit"):
            return False
        res = await self.tools_gateway.execute_tool("memory_edit", {
            "target_id_or_name": target_id_or_name,
            "instruction": instruction,
            "pillar": pillar,
        })
        return res.success

    async def feedback_memory(self, procedure_name: str, success: bool, failure_reason: str = "") -> bool:
        """Provide feedback and reinforcement so procedural memories evolve and self-heal."""
        if not self.tools_gateway.registry.get_definition("memory_feedback"):
            return False
        res = await self.tools_gateway.execute_tool("memory_feedback", {
            "procedure_name": procedure_name,
            "success": success,
            "failure_reason": failure_reason,
        })
        return res.success

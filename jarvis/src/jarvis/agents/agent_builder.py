"""
Agent Builder (Runtime Composer) for J.A.R.V.I.S.
Wires decoupled Provider Gateway, Tools Gateway, Strata Memory, and Prompt Hub together at runtime.
"""

from typing import Any, Dict, List, Optional
from jarvis.agents.agent_hub import AgentHub
from jarvis.agents.base_agent import BaseAgent
from jarvis.agents.schemas import AgentRequest
from jarvis.config.provider_config import ModelRole
from jarvis.decision.schemas import TaskClassification, TaskComplexity
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.logger import get_logger
from jarvis.prompts.prompt_composer import PromptComposer
from jarvis.prompts.schemas import PromptContext
from jarvis.tools.meta_tools import create_gateway_meta_tools
from jarvis.tools.tool_gateway import ToolsGateway

logger = get_logger("agents.builder")


class AgentBuilder:
    """Dynamically composes and configures agents at runtime based on task classification."""

    def __init__(
        self,
        provider_gateway: ProviderGateway,
        tools_gateway: ToolsGateway,
        prompt_composer: Optional[PromptComposer] = None,
        agent_hub: Optional[AgentHub] = None,
    ):
        self.gateway = provider_gateway
        self.tools_gateway = tools_gateway
        self.composer = prompt_composer or PromptComposer()
        self.hub = agent_hub or AgentHub()

    async def recall_memory_context(self, query: str) -> Optional[str]:
        """Fetch memory context from Strata MCP if memory_recall tool is available."""
        if not self.tools_gateway.registry.get_definition("memory_recall"):
            return None

        try:
            logger.info(f"Recalling memory context for query: '{query}'")
            res = await self.tools_gateway.execute_tool(
                "memory_recall",
                {"query": query, "top_k": 3},
            )
            if res.success and res.data:
                output = res.data.get("output", "") if isinstance(res.data, dict) else str(res.data)
                return output if output.strip() else None
        except Exception as e:
            logger.warning(f"Memory recall encountered an error: {e}")

        return None

    async def build(
        self,
        query: str,
        classification: TaskClassification,
        session_history: Optional[List[Dict[str, Any]]] = None,
        preferred_provider: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> tuple[BaseAgent, AgentRequest]:
        """
        Compose a fully-wired agent for the given query and classification.
        Returns: (Wired Agent Instance, Prepared AgentRequest)
        """
        template_id = classification.suggested_agent
        agent_cls = self.hub.get_agent_class(template_id)

        # 1. Memory Context Recall
        memory_ctx = None
        if classification.requires_memory_recall:
            memory_ctx = await self.recall_memory_context(query)

        # 2. Bind the 3 Meta-Tools
        meta_tools = create_gateway_meta_tools(self.tools_gateway)

        # 3. Model Role Selection
        if classification.complexity == TaskComplexity.COMPLEX or classification.requires_planning:
            role = ModelRole.REASONING
        else:
            role = ModelRole.FAST

        # 4. Prepare Context
        prompt_context = PromptContext(
            query=query,
            memory_context=memory_ctx,
            session_history=session_history or [],
        )

        # 5. Instantiate Agent
        agent = agent_cls(
            provider_gateway=self.gateway,
            tools_gateway=self.tools_gateway,
            prompt_composer=self.composer,
            meta_tools=meta_tools,
            model_role=role,
        )

        request = AgentRequest(
            query=query,
            context=prompt_context,
            max_iterations=8 if classification.complexity == TaskComplexity.COMPLEX else 4,
            preferred_provider=preferred_provider,
            model_override=model_override,
        )

        logger.info(
            f"Built agent '{agent.template_id}' (class: {agent_cls.__name__}, role: {role.value}) "
            f"for query: '{query[:40]}...'"
        )

        return agent, request

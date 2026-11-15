"""
Agent Hub for J.A.R.V.I.S.
Maintains the registry of available agent archetypes and creates instances.
"""

from typing import Dict, List, Type
from jarvis.agents.base_agent import BaseAgent
from jarvis.agents.templates.direct_agent import DirectAgent
from jarvis.agents.templates.planning_agent import PlanningAgent
from jarvis.agents.templates.reflex_agent import ReflexAgent
from jarvis.logger import get_logger

logger = get_logger("agents.hub")


class AgentHub:
    """Registry of pre-built and custom agent archetypes."""

    def __init__(self):
        self._registry: Dict[str, Type[BaseAgent]] = {
            "direct_agent": DirectAgent,
            "reflex_agent": ReflexAgent,
            "planning_agent": PlanningAgent,
            "research_agent": ReflexAgent,  # Research uses the ReAct reflex loop
            "code_agent": PlanningAgent,    # Code dev uses structured planning & execution
        }

    def register_agent(self, template_id: str, agent_class: Type[BaseAgent]) -> None:
        """Register a new custom agent archetype. Validates BaseAgent inheritance for mandatory memory lifecycle."""
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"Agent class '{agent_class.__name__}' must inherit from BaseAgent to support default memory substrate")
        self._registry[template_id] = agent_class
        logger.info(f"Registered agent archetype '{template_id}' -> {agent_class.__name__}")

    def get_agent_class(self, template_id: str) -> Type[BaseAgent]:
        """Retrieve the class for a template ID, defaulting to DirectAgent."""
        return self._registry.get(template_id, DirectAgent)

    def list_templates(self) -> List[str]:
        """List all registered agent archetype IDs."""
        return list(self._registry.keys())

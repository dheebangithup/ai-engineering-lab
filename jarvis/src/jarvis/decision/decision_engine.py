"""
Decision Engine for J.A.R.V.I.S.
Routes tasks using fast-path heuristics and the dedicated Decision Model.
Decoupled from generative LLMs for instant (<5ms) zero-hallucination routing.
"""

from typing import Optional
from jarvis.decision.decision_model import DecisionModel
from jarvis.decision.heuristics import evaluate_heuristics
from jarvis.decision.schemas import TaskClassification
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.logger import get_logger

logger = get_logger("decision.decision_engine")


class DecisionEngine:
    """The central routing and complexity engine for J.A.R.V.I.S."""

    def __init__(self, provider_gateway: Optional[ProviderGateway] = None):
        self.gateway = provider_gateway
        self.decision_model = DecisionModel()

    async def classify(self, query: str, context: Optional[str] = None) -> TaskClassification:
        """
        Classify query complexity and intent:
        1. Fast-path heuristics check (<1ms) for trivial greetings/closings
        2. Dedicated Decision Model evaluation (<5ms) for deep complexity, intent, and tool routing
        """
        # Step 1: Fast-path zero-cost heuristics
        fast_result = evaluate_heuristics(query)
        if fast_result is not None:
            logger.debug(f"Fast-path matched for query '{query}': {fast_result.intent.value}")
            return fast_result

        # Step 2: Query configured Decision Model from Provider Gateway
        if self.gateway:
            try:
                gateway_decision = await self.gateway.classify_decision(query, context=context)
                if isinstance(gateway_decision, TaskClassification):
                    return gateway_decision
            except Exception as e:
                logger.warning(f"Gateway decision model execution warning ({e}). Falling back to local classifier.")

        # Step 3: Resilient fallback
        classification = self.decision_model.evaluate(query, context=context)
        return classification

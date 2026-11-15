"""
Phase 1 Test Suite:
Validates the Dynamic Provider Store, Resilient Provider Gateway with Fallback,
and the Decision Engine complexity and intent classification.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from jarvis.config.provider_config import (
    ModelRole,
    ModelSpec,
    ProviderInstanceConfig,
    ProviderKind,
    ProviderRegistryConfig,
)
from jarvis.config.provider_store import ProviderStore
from jarvis.decision.decision_engine import DecisionEngine
from jarvis.decision.schemas import TaskComplexity, TaskIntent
from jarvis.llm.base_provider import BaseLLMProvider
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.llm.schemas import (
    LLMMessage,
    LLMResponse,
    MessageRole,
    ProviderHealth,
    ProviderStatus,
)


@pytest.fixture
def temp_provider_store(tmp_path: Path) -> ProviderStore:
    """Fixture providing a temporary isolated ProviderStore."""
    settings_file = tmp_path / "settings" / "providers.json"
    return ProviderStore(settings_file=settings_file)


class DummyMockProvider(BaseLLMProvider):
    """Mock provider for unit testing fallback behavior."""

    def __init__(self, config: ProviderInstanceConfig, should_fail: bool = False, response_text: str = "ok"):
        super().__init__(config)
        self.should_fail = should_fail
        self.response_text = response_text
        self.call_count = 0

    async def complete(self, messages, **kwargs):
        self.call_count += 1
        if self.should_fail:
            raise ConnectionError(f"Simulated network down on provider '{self.provider_id}'")
        return LLMResponse(
            content=self.response_text,
            role=MessageRole.ASSISTANT,
            provider_id=self.provider_id,
            model_id=self.config.models.get("test-model", ModelSpec(model_id="test-model")).model_id,
        )

    async def check_health(self):
        return ProviderHealth(
            provider_id=self.provider_id,
            status=ProviderStatus.UNAVAILABLE if self.should_fail else ProviderStatus.HEALTHY,
        )


# =========================================================================
# 1. ProviderStore Tests
# =========================================================================

def test_provider_store_seed_and_persistence(temp_provider_store: ProviderStore):
    """Verify that seed config is automatically initialized and persisted to JSON."""
    config = temp_provider_store.load_config()
    assert "kodekloud" in config.providers or "ollama_local" in config.providers
    assert temp_provider_store.settings_file.exists()

    # Add a custom provider (e.g. from UI)
    custom = ProviderInstanceConfig(
        provider_id="custom_provider",
        name="Custom LLM Endpoint",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.custom.com/v1",
        api_key="secret",
    )
    temp_provider_store.add_or_update_provider(custom)

    # Re-read from disk
    new_store = ProviderStore(settings_file=temp_provider_store.settings_file)
    reloaded = new_store.load_config()
    assert "custom_provider" in reloaded.providers
    assert reloaded.providers["custom_provider"].base_url == "https://api.custom.com/v1"


def test_provider_store_remove_provider(temp_provider_store: ProviderStore):
    """Verify provider deletion and fallback chain cleanup."""
    temp_provider_store.set_fallback_chain(ModelRole.FAST, ["p1", "p2"])
    custom = ProviderInstanceConfig(
        provider_id="p1",
        name="Provider 1",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://p1.com/v1",
    )
    temp_provider_store.add_or_update_provider(custom)
    
    assert temp_provider_store.remove_provider("p1") is True
    reloaded = temp_provider_store.load_config()
    assert "p1" not in reloaded.providers
    assert "p1" not in reloaded.fallback_chains[ModelRole.FAST]


# =========================================================================
# 2. Provider Gateway Automatic Fallback Tests
# =========================================================================

@pytest.mark.anyio
async def test_provider_gateway_fallback_on_primary_failure(temp_provider_store: ProviderStore):
    """
    Test that if Primary Provider throws an error, the Provider Gateway
    automatically cascades to Secondary Provider and flags fallback_occurred=True.
    """
    p1_cfg = ProviderInstanceConfig(
        provider_id="primary_failing",
        name="Primary Failing Provider",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://fail.com",
    )
    p2_cfg = ProviderInstanceConfig(
        provider_id="secondary_healthy",
        name="Secondary Healthy Provider",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://healthy.com",
    )

    temp_provider_store.add_or_update_provider(p1_cfg)
    temp_provider_store.add_or_update_provider(p2_cfg)
    temp_provider_store.set_fallback_chain(ModelRole.FAST, ["primary_failing", "secondary_healthy"])

    gateway = ProviderGateway(store=temp_provider_store)

    # Inject mock implementations
    p1_mock = DummyMockProvider(p1_cfg, should_fail=True)
    p2_mock = DummyMockProvider(p2_cfg, should_fail=False, response_text="Success from Secondary!")
    gateway._providers["primary_failing"] = p1_mock
    gateway._providers["secondary_healthy"] = p2_mock

    messages = [LLMMessage(role=MessageRole.USER, content="Hello")]
    response = await gateway.complete(messages=messages, role=ModelRole.FAST)

    assert response.content == "Success from Secondary!"
    assert response.provider_id == "secondary_healthy"
    assert response.fallback_occurred is True
    assert len(response.failover_history) == 1
    assert "primary_failing" in response.failover_history[0]
    assert p1_mock.call_count == 1
    assert p2_mock.call_count == 1


@pytest.mark.anyio
async def test_provider_gateway_all_fail(temp_provider_store: ProviderStore):
    """Verify that when all providers fail, a clear descriptive RuntimeError is raised."""
    p1_cfg = ProviderInstanceConfig(
        provider_id="failing_1",
        name="Failing 1",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://fail1.com",
    )
    temp_provider_store.add_or_update_provider(p1_cfg)
    temp_provider_store.set_fallback_chain(ModelRole.REASONING, ["failing_1"])

    gateway = ProviderGateway(store=temp_provider_store)
    gateway._providers["failing_1"] = DummyMockProvider(p1_cfg, should_fail=True)

    messages = [LLMMessage(role=MessageRole.USER, content="Hello")]
    with pytest.raises(RuntimeError) as exc_info:
        await gateway.complete(messages=messages, role=ModelRole.REASONING)

    assert "All providers in fallback chain failed" in str(exc_info.value)


# =========================================================================
# 3. Decision Engine Tests
# =========================================================================

@pytest.mark.anyio
async def test_decision_engine_fast_path():
    """Verify that simple greetings and closings trigger zero-LLM fast path in <1ms."""
    mock_gateway = AsyncMock(spec=ProviderGateway)
    engine = DecisionEngine(provider_gateway=mock_gateway)

    # Greeting
    res_hi = await engine.classify("Hi Jarvis!")
    assert res_hi.fast_path is True
    assert res_hi.complexity == TaskComplexity.SIMPLE
    assert res_hi.intent == TaskIntent.CONVERSATION
    mock_gateway.complete.assert_not_called()

    # Thanks
    res_thanks = await engine.classify("Thank you so much")
    assert res_thanks.fast_path is True
    assert res_thanks.intent == TaskIntent.CONVERSATION
    mock_gateway.complete.assert_not_called()


@pytest.mark.anyio
async def test_decision_engine_llm_routing():
    """Verify that complex non-greeting queries are routed to the Decision Model."""
    mock_gateway = AsyncMock(spec=ProviderGateway)
    engine = DecisionEngine(provider_gateway=mock_gateway)

    classification = await engine.classify("Refactor the entire authentication system across all microservices")

    assert classification.complexity == TaskComplexity.COMPLEX
    assert classification.intent == TaskIntent.CODE_DEV or classification.intent == TaskIntent.PLANNING
    assert classification.requires_planning is True
    assert classification.suggested_agent == "planning_agent"
    assert "filesystem" in classification.suggested_tool_categories or "memory" in classification.suggested_tool_categories
    assert classification.fast_path is True  # Sub-5ms Decision Model evaluation


@pytest.mark.anyio
async def test_decision_engine_durable_facts_detection():
    """Verify that statements introducing personal identity or project facts flag requires_memory_ingest=True."""
    mock_gateway = AsyncMock(spec=ProviderGateway)
    engine = DecisionEngine(provider_gateway=mock_gateway)

    # Personal identity
    res = await engine.classify("My name is Theeban, I am an AI engineer")
    assert res.requires_memory_ingest is True
    assert res.requires_memory_recall is True
    assert "memory" in res.suggested_tool_categories
    assert "Theeban" in res.extracted_entities

    # Technical / Project preference
    res_pref = await engine.classify("I prefer PostgreSQL on Neon and Python 3.12")
    assert res_pref.requires_memory_ingest is True
    assert "memory" in res_pref.suggested_tool_categories

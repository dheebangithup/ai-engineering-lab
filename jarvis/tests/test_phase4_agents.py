"""
Phase 4 Test Suite: Prompt Hub, Agent Hub, Runtime Agent Composition,
and the Core J.A.R.V.I.S. Orchestrator Pipeline.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from jarvis.agents.agent_builder import AgentBuilder
from jarvis.agents.agent_hub import AgentHub
from jarvis.agents.schemas import AgentRequest
from jarvis.agents.templates.direct_agent import DirectAgent
from jarvis.agents.templates.planning_agent import PlanningAgent
from jarvis.agents.templates.reflex_agent import ReflexAgent
from jarvis.config.provider_config import ModelRole
from jarvis.core.jarvis import Jarvis
from jarvis.decision.schemas import TaskClassification, TaskComplexity, TaskIntent
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.llm.schemas import (
    LLMMessage,
    LLMResponse,
    MessageRole,
    ToolCallFunction,
    ToolCallRequest,
)
from jarvis.prompts.prompt_composer import PromptComposer
from jarvis.prompts.schemas import PromptContext
from jarvis.tools.meta_tools import create_gateway_meta_tools
from jarvis.tools.tool_gateway import ToolsGateway


# =========================================================================
# 1. Prompt Hub Tests
# =========================================================================

def test_prompt_composer_layered_composition():
    composer = PromptComposer()
    context = PromptContext(
        query="Refactor database",
        memory_context="<strata_memory_context>User uses Python 3.12</strata_memory_context>",
    )

    sys_prompt = composer.compose_system_prompt("planning_agent", context)
    assert "J.A.R.V.I.S." in sys_prompt
    assert "Planning & Execution Agent" in sys_prompt
    assert "<strata_memory_context>User uses Python 3.12</strata_memory_context>" in sys_prompt
    assert "Active Workspace Sandbox:" in sys_prompt

    messages = composer.compose_messages("planning_agent", context)
    assert len(messages) == 2
    assert messages[0].role == MessageRole.SYSTEM
    assert messages[1].role == MessageRole.USER
    assert messages[1].content == "Refactor database"


# =========================================================================
# 2. Agent Hub & Agent Builder Tests
# =========================================================================

@pytest.mark.anyio
async def test_agent_builder_wires_direct_agent():
    mock_gw = AsyncMock(spec=ProviderGateway)
    tools_gw = ToolsGateway()
    builder = AgentBuilder(provider_gateway=mock_gw, tools_gateway=tools_gw)

    classification = TaskClassification(
        complexity=TaskComplexity.SIMPLE,
        intent=TaskIntent.CONVERSATION,
        suggested_agent="direct_agent",
        requires_memory_recall=False,
    )

    agent, req = await builder.build("Hello Jarvis", classification)
    assert isinstance(agent, DirectAgent)
    assert agent.model_role == ModelRole.FAST
    assert len(agent.meta_tools) == 3


@pytest.mark.anyio
async def test_agent_builder_wires_planning_agent():
    mock_gw = AsyncMock(spec=ProviderGateway)
    tools_gw = ToolsGateway()
    builder = AgentBuilder(provider_gateway=mock_gw, tools_gateway=tools_gw)

    classification = TaskClassification(
        complexity=TaskComplexity.COMPLEX,
        intent=TaskIntent.PLANNING,
        suggested_agent="planning_agent",
        requires_planning=True,
        requires_memory_recall=False,
    )

    agent, req = await builder.build("Refactor authentication pipeline", classification)
    assert isinstance(agent, PlanningAgent)
    assert agent.model_role == ModelRole.REASONING
    assert req.max_iterations == 8


# =========================================================================
# 3. DirectAgent Execution Tests
# =========================================================================

@pytest.mark.anyio
async def test_direct_agent_execution():
    mock_gw = AsyncMock(spec=ProviderGateway)
    mock_gw.complete.return_value = LLMResponse(
        content="Good evening, sir. All systems are operational.",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
    )

    tools_gw = ToolsGateway()
    meta_tools = create_gateway_meta_tools(tools_gw)
    composer = PromptComposer()

    agent = DirectAgent(
        provider_gateway=mock_gw,
        tools_gateway=tools_gw,
        prompt_composer=composer,
        meta_tools=meta_tools,
    )

    req = AgentRequest(
        query="Status report",
        context=PromptContext(query="Status report"),
    )

    resp = await agent.execute(req)
    assert "Good evening, sir" in resp.answer
    assert resp.agent_template == "direct_agent"
    assert resp.provider_used == "ollama_local"


@pytest.mark.anyio
async def test_direct_agent_autonomous_memory_ingest():
    """Verify DirectAgent can execute memory_ingest via execute_tool in one turn."""
    mock_gw = AsyncMock(spec=ProviderGateway)

    # First completion: agent calls execute_tool(tool_id='memory_ingest', ...)
    step1_resp = LLMResponse(
        content="I will remember this.",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
        tool_calls=[
            ToolCallRequest(
                id="call_ingest",
                function=ToolCallFunction(
                    name="execute_tool",
                    arguments='{"tool_id": "memory_ingest", "arguments": {"raw_text": "The user is Theeban, an AI engineer."}}',
                ),
            )
        ],
    )

    # Second completion: agent acknowledges naturally without asking permission
    step2_resp = LLMResponse(
        content="Pleasure to meet you, Theeban! How can I assist you with your AI engineering work today?",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
    )

    mock_gw.complete.side_effect = [step1_resp, step2_resp]

    tools_gw = ToolsGateway()
    from jarvis.tools.decorators import jarvis_tool
    from jarvis.tools.schemas import PermissionTier, ToolParameter

    @jarvis_tool(
        tool_id="memory_ingest",
        name="Ingest Memory",
        description="Ingest memory into Strata",
        permission_tier=PermissionTier.SENSITIVE,
        parameters={"raw_text": ToolParameter(type="string", description="text", required=True)},
    )
    def mock_ingest(raw_text: str):
        return {"status": "stored", "raw_text": raw_text}

    tools_gw.register_tool(mock_ingest)
    meta_tools = create_gateway_meta_tools(tools_gw)
    composer = PromptComposer()

    agent = DirectAgent(
        provider_gateway=mock_gw,
        tools_gateway=tools_gw,
        prompt_composer=composer,
        meta_tools=meta_tools,
    )

    req = AgentRequest(
        query="My name is Theeban, I am an AI engineer",
        context=PromptContext(query="My name is Theeban, I am an AI engineer"),
    )

    resp = await agent.execute(req)
    assert "Theeban" in resp.answer
    assert "execute_tool" in resp.tools_used
    assert len(resp.steps) == 1
    assert resp.steps[0].action_args["tool_id"] == "memory_ingest"


# =========================================================================
# 4. ReflexAgent ReAct Loop Tests
# =========================================================================

@pytest.mark.anyio
async def test_reflex_agent_react_tool_loop():
    mock_gw = AsyncMock(spec=ProviderGateway)

    # First call: LLM decides to search tools
    step1_resp = LLMResponse(
        content="I need to search for tools to read the file.",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
        tool_calls=[
            ToolCallRequest(
                id="call_1",
                function=ToolCallFunction(
                    name="search_tools",
                    arguments='{"query": "read file"}',
                ),
            )
        ],
    )

    # Second call: LLM sees observation and returns final answer
    step2_resp = LLMResponse(
        content="I have identified the read_file tool. Task complete.",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
        tool_calls=None,
    )

    mock_gw.complete.side_effect = [step1_resp, step2_resp]

    tools_gw = ToolsGateway()
    meta_tools = create_gateway_meta_tools(tools_gw)
    composer = PromptComposer()

    agent = ReflexAgent(
        provider_gateway=mock_gw,
        tools_gateway=tools_gw,
        prompt_composer=composer,
        meta_tools=meta_tools,
    )

    req = AgentRequest(
        query="Find file reading tools",
        context=PromptContext(query="Find file reading tools"),
        max_iterations=3,
    )

    resp = await agent.execute(req)
    assert resp.answer == "I have identified the read_file tool. Task complete."
    assert len(resp.steps) == 1
    assert resp.steps[0].action_tool == "search_tools"
    assert "search_tools" in resp.tools_used


# =========================================================================
# 5. Full End-to-End Orchestrator Pipeline Tests
# =========================================================================

@pytest.mark.anyio
async def test_jarvis_orchestrator_pipeline():
    """Verify that Jarvis.process executes the full end-to-end pipeline cleanly."""
    mock_gw = AsyncMock(spec=ProviderGateway)
    mock_gw.complete.return_value = LLMResponse(
        content="Greetings. J.A.R.V.I.S. online.",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
    )

    jarvis = Jarvis(provider_gateway=mock_gw)
    # Mock mcp_manager.initialize_servers to avoid external subprocess in unit test
    jarvis.mcp_manager = AsyncMock()
    jarvis.mcp_manager.initialize_servers.return_value = {}
    jarvis.mcp_manager.shutdown = AsyncMock()

    await jarvis.initialize()

    response = await jarvis.process("Hi Jarvis!")
    assert response.query == "Hi Jarvis!"
    assert "Greetings" in response.answer
    assert response.agent_used == "direct_agent"
    assert response.classification.complexity == TaskComplexity.SIMPLE
    assert response.classification.intent == TaskIntent.CONVERSATION

    # Verify session history updated
    session = jarvis.get_or_create_session("default")
    assert len(session.history) == 2
    assert session.history[0]["content"] == "Hi Jarvis!"

    await jarvis.shutdown()


@pytest.mark.anyio
async def test_jarvis_orchestrator_autonomous_ingest_safety_net():
    """Verify that Jarvis.process automatically ingests durable facts even if the LLM didn't call the tool."""
    mock_gw = AsyncMock(spec=ProviderGateway)
    mock_gw.complete.return_value = LLMResponse(
        content="Pleasure to meet you, Theeban! All systems operational.",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
    )

    jarvis = Jarvis(provider_gateway=mock_gw)
    jarvis.mcp_manager = AsyncMock()
    jarvis.mcp_manager.initialize_servers.return_value = {}
    jarvis.mcp_manager.shutdown = AsyncMock()

    from jarvis.tools.decorators import jarvis_tool
    from jarvis.tools.schemas import PermissionTier, ToolParameter

    ingested_texts = []

    @jarvis_tool(
        tool_id="memory_ingest",
        name="Ingest Memory",
        description="Ingest memory into Strata",
        permission_tier=PermissionTier.SENSITIVE,
        parameters={"raw_text": ToolParameter(type="string", description="text", required=True)},
    )
    def mock_ingest(raw_text: str):
        ingested_texts.append(raw_text)
        return {"status": "stored", "raw_text": raw_text}

    jarvis.tools_gateway.register_tool(mock_ingest)
    await jarvis.initialize()

    resp = await jarvis.process("My name is Theeban, I am an AI engineer")
    assert resp.classification.requires_memory_ingest is True
    assert "memory_ingest" in resp.tools_used
    assert len(ingested_texts) == 1
    assert "Theeban" in ingested_texts[0]

    await jarvis.shutdown()


@pytest.mark.anyio
async def test_base_agent_default_memory_methods():
    """Verify that any agent inheriting from BaseAgent has the 4 default memory methods."""
    mock_gw = AsyncMock(spec=ProviderGateway)
    tools_gw = ToolsGateway()

    from jarvis.tools.decorators import jarvis_tool
    from jarvis.tools.schemas import PermissionTier, ToolParameter

    recalled_queries = []
    ingested_facts = []
    edited_memories = []
    feedback_reports = []

    @jarvis_tool(
        tool_id="memory_recall",
        name="Recall Memory",
        description="Recall memories",
        parameters={"query": ToolParameter(type="string", description="query"), "top_k": ToolParameter(type="integer", default=3)},
    )
    def mock_recall(query: str, top_k: int = 3):
        recalled_queries.append(query)
        return {"output": "Recalled facts"}

    @jarvis_tool(
        tool_id="memory_ingest",
        name="Ingest Memory",
        description="Ingest memories",
        parameters={"raw_text": ToolParameter(type="string", description="text")},
    )
    def mock_ingest(raw_text: str):
        ingested_facts.append(raw_text)
        return {"status": "stored"}

    @jarvis_tool(
        tool_id="memory_edit",
        name="Edit Memory",
        description="Edit memories",
        parameters={
            "target_id_or_name": ToolParameter(type="string", description="target"),
            "instruction": ToolParameter(type="string", description="instruction"),
            "pillar": ToolParameter(type="string", default="semantic"),
        },
    )
    def mock_edit(target_id_or_name: str, instruction: str, pillar: str = "semantic"):
        edited_memories.append((target_id_or_name, instruction, pillar))
        return {"status": "updated"}

    @jarvis_tool(
        tool_id="memory_feedback",
        name="Feedback Memory",
        description="Feedback memories",
        parameters={
            "procedure_name": ToolParameter(type="string", description="proc"),
            "success": ToolParameter(type="boolean", description="success"),
            "failure_reason": ToolParameter(type="string", default=""),
        },
    )
    def mock_feedback(procedure_name: str, success: bool, failure_reason: str = ""):
        feedback_reports.append((procedure_name, success, failure_reason))
        return {"status": "reinforced"}

    tools_gw.register_tool(mock_recall)
    tools_gw.register_tool(mock_ingest)
    tools_gw.register_tool(mock_edit)
    tools_gw.register_tool(mock_feedback)

    meta_tools = create_gateway_meta_tools(tools_gw)
    composer = PromptComposer()

    agent = DirectAgent(
        provider_gateway=mock_gw,
        tools_gateway=tools_gw,
        prompt_composer=composer,
        meta_tools=meta_tools,
    )

    # 1. Recall
    ctx = await agent.recall_memory("Find user preferences")
    assert ctx == "Recalled facts"
    assert len(recalled_queries) == 1

    # 2. Ingest
    ingest_ok = await agent.ingest_memory("User prefers uv and Python 3.12")
    assert ingest_ok is True
    assert len(ingested_facts) == 1

    # 3. Edit / Update
    edit_ok = await agent.edit_memory("deploy_service", "Add healthcheck step before restarting", "procedural")
    assert edit_ok is True
    assert len(edited_memories) == 1

    # 4. Feedback / Reinforcement
    fb_ok = await agent.feedback_memory("deploy_service", True)
    assert fb_ok is True
    assert len(feedback_reports) == 1
    assert feedback_reports[0] == ("deploy_service", True, "")


def test_agent_hub_enforces_base_agent():
    """Verify that AgentHub enforces BaseAgent inheritance for all registered agent archetypes."""
    hub = AgentHub()

    class ValidCustomAgent(DirectAgent):
        pass

    class InvalidAgent:
        pass

    hub.register_agent("valid_agent", ValidCustomAgent)
    assert hub.get_agent_class("valid_agent") is ValidCustomAgent

    with pytest.raises(TypeError) as exc:
        hub.register_agent("invalid_agent", InvalidAgent)  # type: ignore
    assert "must inherit from BaseAgent" in str(exc.value)


@pytest.mark.anyio
async def test_jarvis_orchestrator_evolutionary_feedback_on_failure():
    """Verify that on agent failure, memory_feedback is called with success=False and failure_reason so runbooks self-heal."""
    mock_gw = AsyncMock(spec=ProviderGateway)

    # First turn: tool call to a failing tool
    step1_resp = LLMResponse(
        content="Attempting step...",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
        tool_calls=[
            ToolCallRequest(
                id="call_failing",
                function=ToolCallFunction(
                    name="execute_tool",
                    arguments='{"tool_id": "failing_tool", "arguments": {}}',
                ),
            )
        ],
    )
    # Second turn: final response noting failure
    step2_resp = LLMResponse(
        content="Execution failed due to broken step.",
        role=MessageRole.ASSISTANT,
        provider_id="ollama_local",
        model_id="qwen3:8b",
    )
    mock_gw.complete.side_effect = [step1_resp, step2_resp]

    jarvis = Jarvis(provider_gateway=mock_gw)
    jarvis.mcp_manager = AsyncMock()
    jarvis.mcp_manager.initialize_servers.return_value = {}
    jarvis.mcp_manager.shutdown = AsyncMock()

    from jarvis.tools.decorators import jarvis_tool
    from jarvis.tools.schemas import PermissionTier, ToolParameter

    feedback_records = []

    @jarvis_tool(tool_id="failing_tool", name="Failing Tool", description="A tool that fails")
    def failing_tool():
        raise RuntimeError("Database connection timed out on port 5432")

    @jarvis_tool(
        tool_id="memory_feedback",
        name="Feedback Memory",
        description="Report feedback",
        parameters={
            "procedure_name": ToolParameter(type="string", description="proc"),
            "success": ToolParameter(type="boolean", description="success"),
            "failure_reason": ToolParameter(type="string", default=""),
        },
    )
    def mock_feedback(procedure_name: str, success: bool, failure_reason: str = ""):
        feedback_records.append((procedure_name, success, failure_reason))
        return {"status": "healed"}

    jarvis.tools_gateway.register_tool(failing_tool)
    jarvis.tools_gateway.register_tool(mock_feedback)
    await jarvis.initialize()

    resp = await jarvis.process("Run the database migration command")

    # Feedback should have recorded the failure with trace to trigger Strata self-healing
    assert len(feedback_records) == 1
    proc_name, success, reason = feedback_records[0]
    assert success is False
    assert "Database connection timed out" in reason or "failed" in reason

    await jarvis.shutdown()

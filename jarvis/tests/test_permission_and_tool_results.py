"""
Tests for Tool Results Display & Human-in-the-Loop Permission Resolution.
Verifies that:
1. Tool execution results (data, arguments, success status) are captured in AgentResponse and JarvisResponse.
2. When a tool requires approval, pending_permission is returned and tracked on JarvisSession.
3. Affirmative chat input ("yes", "approve") resolves and executes the pending tool with bypass_permission=True.
4. Negative chat input ("no", "deny") cancels the pending action cleanly.
5. REST API endpoint POST /v1/permissions/approve approves and executes or denies pending actions.
"""

import json
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from jarvis.agents.schemas import AgentRequest
from jarvis.agents.templates.direct_agent import DirectAgent
from jarvis.config.provider_config import ModelRole
from jarvis.core.jarvis import Jarvis
from jarvis.core.schemas import JarvisRequest, PendingAction
from jarvis.interfaces.api import app
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.llm.schemas import LLMResponse, MessageRole, ToolCallFunction, ToolCallRequest
from jarvis.prompts.prompt_composer import PromptComposer
from jarvis.prompts.schemas import PromptContext
from jarvis.tools.decorators import jarvis_tool
from jarvis.tools.meta_tools import create_gateway_meta_tools
from jarvis.tools.permissions import PermissionInterceptor
from jarvis.tools.schemas import PermissionTier, ToolParameter
from jarvis.tools.tool_gateway import ToolsGateway


@pytest.mark.anyio
async def test_tool_results_captured_in_direct_agent():
    """Verify tool_results list captures output data, parameters, and status."""
    mock_gw = AsyncMock(spec=ProviderGateway)

    # 1. Step 1: Agent calls execute_tool for memory_store_explicit
    step1_resp = LLMResponse(
        content="Storing user preference.",
        role=MessageRole.ASSISTANT,
        provider_id="mock_prov",
        model_id="mock_model",
        tool_calls=[
            ToolCallRequest(
                id="call_store",
                function=ToolCallFunction(
                    name="execute_tool",
                    arguments='{"tool_id": "memory_store_explicit", "arguments": {"fact": "User prefers dark mode", "category": "preferences"}}',
                ),
            )
        ],
    )
    # 2. Step 2: Agent synthesizes final answer
    step2_resp = LLMResponse(
        content="I have stored your preference for dark mode.",
        role=MessageRole.ASSISTANT,
        provider_id="mock_prov",
        model_id="mock_model",
    )
    mock_gw.complete.side_effect = [step1_resp, step2_resp]

    tools_gw = ToolsGateway()

    @jarvis_tool(
        tool_id="memory_store_explicit",
        name="Store Explicit Memory",
        description="Store memory explicitly",
        permission_tier=PermissionTier.SAFE,
        parameters={
            "fact": ToolParameter(type="string", description="fact", required=True),
            "category": ToolParameter(type="string", description="category", default="general"),
        },
    )
    def mock_store(fact: str, category: str = "general"):
        return {"status": "stored", "memory_id": "mem_12345", "fact": fact, "category": category}

    tools_gw.register_tool(mock_store)
    meta_tools = create_gateway_meta_tools(tools_gw)

    agent = DirectAgent(
        provider_gateway=mock_gw,
        tools_gateway=tools_gw,
        prompt_composer=PromptComposer(),
        meta_tools=meta_tools,
    )

    req = AgentRequest(
        query="Store preference: User prefers dark mode",
        context=PromptContext(query="Store preference: User prefers dark mode"),
    )

    resp = await agent.execute(req)
    assert resp.success is True
    assert "execute_tool" in resp.tools_used
    assert "memory_store_explicit" in resp.tools_used
    assert len(resp.tool_results) == 1

    tr = resp.tool_results[0]
    assert tr["tool_id"] == "memory_store_explicit"
    assert tr["success"] is True
    assert tr["data"]["memory_id"] == "mem_12345"
    assert tr["data"]["fact"] == "User prefers dark mode"
    assert tr["arguments"]["category"] == "preferences"


@pytest.mark.anyio
async def test_permission_pending_action_and_affirmative_resolution():
    """Verify tool requiring authorization sets pending_action and user typing 'yes' executes it."""
    jarvis = Jarvis()
    jarvis.mcp_manager = AsyncMock()
    jarvis.mcp_manager.initialize_servers.return_value = {}
    jarvis.mcp_manager.shutdown = AsyncMock()
    await jarvis.initialize()

    session_id = "test_perm_session"
    session = jarvis.get_or_create_session(session_id)

    # 1. Manually stage a pending action as if a tool call was intercepted
    session.pending_action = PendingAction(
        action_token="act_test123",
        tool_id="run_command",
        tool_name="Run System Command",
        permission_tier="dangerous",
        arguments={"command": "echo", "args": ["verified_execution"]},
        reason="Execution of shell command requires explicit human authorization",
    )

    # 2. User replies "yes" in chat
    resp = await jarvis.process(
        JarvisRequest(
            query="yes",
            session_id=session_id,
        )
    )

    # Assert pending action was consumed and executed
    assert session.pending_action is None
    assert "run_command" in resp.tools_used
    assert len(resp.tool_results) == 1
    assert resp.tool_results[0]["success"] is True
    assert "verified_execution" in resp.tool_results[0]["data"]["stdout"]
    assert "Permission Granted" in resp.answer


@pytest.mark.anyio
async def test_permission_pending_action_negative_cancellation():
    """Verify tool requiring authorization is canceled when user replies 'no'."""
    jarvis = Jarvis()
    jarvis.mcp_manager = AsyncMock()
    jarvis.mcp_manager.initialize_servers.return_value = {}
    jarvis.mcp_manager.shutdown = AsyncMock()
    await jarvis.initialize()

    session_id = "test_cancel_session"
    session = jarvis.get_or_create_session(session_id)

    session.pending_action = PendingAction(
        action_token="act_cancel123",
        tool_id="run_command",
        arguments={"command": "echo", "args": ["should_not_run"]},
    )

    # User replies "no"
    resp = await jarvis.process(
        JarvisRequest(
            query="no, cancel that",
            session_id=session_id,
        )
    )

    assert session.pending_action is None
    assert "canceled" in resp.answer.lower() or "denied" in resp.answer.lower()


@pytest.mark.anyio
async def test_api_permission_approval_endpoint():
    """Verify POST /v1/permissions/approve executes pending tool and returns tool_results."""
    from jarvis.interfaces import api
    jarvis = api.get_jarvis()
    orig_mcp = jarvis.mcp_manager
    mock_mcp = AsyncMock()
    mock_mcp.initialize_servers.return_value = {}
    mock_mcp.shutdown = AsyncMock()
    mock_mcp.list_configured_servers.return_value = []
    jarvis.mcp_manager = mock_mcp

    try:
        await jarvis.initialize()

        session_id = "api_test_session"
        session = jarvis.get_or_create_session(session_id)

        session.pending_action = PendingAction(
            action_token="act_api_token",
            tool_id="run_command",
            arguments={"command": "echo", "args": ["api_approved_test"]},
        )

        client = TestClient(app)
        resp = client.post(
            "/v1/permissions/approve",
            json={
                "session_id": session_id,
                "action_token": "act_api_token",
                "approved": True,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "run_command" in data["tools_used"]
        assert len(data["tool_results"]) == 1
        assert "api_approved_test" in data["tool_results"][0]["data"]["stdout"]
        assert session.pending_action is None
    finally:
        jarvis.mcp_manager = orig_mcp

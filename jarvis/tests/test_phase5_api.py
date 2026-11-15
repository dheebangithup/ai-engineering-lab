"""
Phase 5 Test Suite: FastAPI REST API Gateway & Control Center.
Tests chat endpoint, status check, and dynamic provider & MCP management endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pytest

from jarvis.core.jarvis import Jarvis
from jarvis.core.schemas import JarvisResponse
from jarvis.decision.schemas import TaskClassification, TaskComplexity, TaskIntent
from jarvis.interfaces.api import app, get_jarvis
from jarvis.llm.schemas import LLMResponse, MessageRole


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture with mocked background connections."""
    jarvis = get_jarvis()
    # Mock external MCP server subprocess to keep tests fast and isolated
    jarvis.mcp_manager.initialize_servers = AsyncMock(return_value={"strata-memory": ["memory_recall"]})
    jarvis.mcp_manager.shutdown = AsyncMock()

    # Mock provider gateway completion
    jarvis.provider_gateway.complete = AsyncMock(
        return_value=LLMResponse(
            content="J.A.R.V.I.S. REST API operational.",
            role=MessageRole.ASSISTANT,
            provider_id="ollama_local",
            model_id="qwen3:8b",
        )
    )

    with TestClient(app) as test_client:
        yield test_client


def test_api_status_endpoint(client: TestClient):
    resp = client.get("/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert "workspace_root" in data
    assert "active_providers" in data
    assert data["total_tools"] >= 5


def test_api_chat_endpoint(client: TestClient):
    payload = {"query": "Hello Jarvis", "session_id": "test_session"}
    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "Hello Jarvis"
    assert "operational" in data["answer"] or "J.A.R.V.I.S." in data["answer"]
    assert "classification" in data


def test_api_list_and_update_providers(client: TestClient):
    # 1. List providers
    resp = client.get("/v1/settings/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert "fallback_chains" in data

    # 2. Add custom provider via API (UI ready)
    custom_provider = {
        "provider_id": "test_custom_api",
        "name": "Custom Endpoint from UI",
        "kind": "openai_compatible",
        "base_url": "https://custom.api/v1",
        "api_key": "test_key",
        "models": {
            "model-1": {
                "model_id": "model-1",
                "roles": ["fast"],
            }
        },
        "enabled": True,
    }
    add_resp = client.post("/v1/settings/providers", json=custom_provider)
    assert add_resp.status_code == 200
    assert "successfully updated" in add_resp.json()["message"]

    # 3. Verify single provider get
    get_p = client.get("/v1/settings/providers/test_custom_api")
    assert get_p.status_code == 200
    assert get_p.json()["base_url"] == "https://custom.api/v1"

    # 4. Update fallback chains endpoint
    chain_payload = {
        "role": "fast",
        "provider_ids": ["test_custom_api", "ollama_local"]
    }
    chain_resp = client.post("/v1/settings/fallback_chains", json=chain_payload)
    assert chain_resp.status_code == 200
    assert chain_resp.json()["provider_ids"] == ["test_custom_api", "ollama_local"]

    # 5. Verify it is reflected in providers list
    verify_resp = client.get("/v1/settings/providers")
    assert "test_custom_api" in verify_resp.json()["providers"]
    assert verify_resp.json()["fallback_chains"]["fast"] == ["test_custom_api", "ollama_local"]


def test_api_chat_with_preferred_provider(client: TestClient):
    payload = {
        "query": "Run this with custom provider",
        "session_id": "custom_exec_session",
        "preferred_provider": "ollama_local"
    }
    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "Run this with custom provider"


def test_api_test_provider_connection(client: TestClient):
    # 1. Test successful token & connection
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
        mock_get.return_value = mock_resp

        payload = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-valid-key",
            "kind": "openai_compatible",
        }
        resp = client.post("/v1/settings/providers/test_connection", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["status"] == "connected"
        assert "gpt-4o" in data["available_models"]

    # 2. Test invalid API token (HTTP 401)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Incorrect API key provided"
        mock_get.return_value = mock_resp

        payload = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-invalid-key",
            "kind": "openai_compatible",
        }
        resp = client.post("/v1/settings/providers/test_connection", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["status"] == "auth_failed"
        assert "Authentication failed" in data["message"]


def test_api_list_tools(client: TestClient):
    resp = client.get("/v1/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert len(tools) >= 5
    assert any(t["tool_id"] == "read_file" for t in tools)
    assert any(t["tool_id"] == "run_command" for t in tools)


def test_api_serve_ui_dashboard(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "J.A.R.V.I.S." in resp.text
    assert "Arc Reactor" in resp.text or "Command Console" in resp.text

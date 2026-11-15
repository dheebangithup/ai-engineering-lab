"""
Connection and API Token Verification for LLM Providers.
Validates endpoint reachability, token authentication, and model availability.
"""

import time
from typing import Dict, List, Optional
import httpx
from jarvis.config.provider_config import ProviderKind
from jarvis.interfaces.schemas import (
    TestProviderConnectionRequest,
    TestProviderConnectionResponse,
)
from jarvis.logger import get_logger

logger = get_logger("llm.connection_tester")


async def test_llm_provider_connectivity(
    request: TestProviderConnectionRequest,
    timeout_seconds: float = 8.0,
) -> TestProviderConnectionResponse:
    """
    Test connectivity to an LLM provider endpoint and verify API token validity.
    Returns latency, authentication status, and discovered models.
    """
    raw_url = request.base_url.strip().rstrip("/")
    api_key = request.api_key.strip() if request.api_key else ""
    kind = request.kind
    headers = {"Content-Type": "application/json", **request.custom_headers}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    start_time = time.perf_counter()

    # 1. Ollama Provider
    if kind == ProviderKind.OLLAMA:
        native_url = raw_url[:-3] if raw_url.endswith("/v1") else raw_url
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.get(f"{native_url}/api/tags")
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", []) if "name" in m]
                    capabilities_map: Dict[str, List[str]] = {}
                    for m in data.get("models", []):
                        m_name = m.get("name", "")
                        caps = m.get("capabilities", [])
                        if m_name and caps:
                            capabilities_map[m_name] = caps
                    return TestProviderConnectionResponse(
                        success=True,
                        status="connected",
                        latency_ms=latency,
                        message=f"Connected to Ollama daemon. {len(models)} local models detected.",
                        available_models=models,
                        model_capabilities=capabilities_map,
                        http_status_code=200,
                    )
                else:
                    return TestProviderConnectionResponse(
                        success=False,
                        status="error",
                        latency_ms=latency,
                        message=f"Ollama returned HTTP {resp.status_code}: {resp.text[:150]}",
                        http_status_code=resp.status_code,
                    )
        except httpx.ConnectError:
            return TestProviderConnectionResponse(
                success=False,
                status="unreachable",
                message=f"Could not connect to Ollama daemon at '{native_url}'. Ensure Ollama is running (`ollama serve`).",
            )
        except Exception as e:
            return TestProviderConnectionResponse(
                success=False,
                status="error",
                message=f"Ollama connectivity error: {str(e)}",
            )

    # 2. OpenAI-Compatible & Groq Providers
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, headers=headers) as client:
            # First attempt: standard GET /models
            models_url = f"{raw_url}/models"
            try:
                resp = await client.get(models_url)
                latency = round((time.perf_counter() - start_time) * 1000, 2)

                if resp.status_code == 200:
                    data = resp.json()
                    raw_models = data.get("data", [])
                    models = [m.get("id", "") for m in raw_models if isinstance(m, dict) and "id" in m]
                    return TestProviderConnectionResponse(
                        success=True,
                        status="connected",
                        latency_ms=latency,
                        message=f"API token verified! Discovered {len(models)} available models.",
                        available_models=models,
                        http_status_code=200,
                    )
                elif resp.status_code in (401, 403):
                    return TestProviderConnectionResponse(
                        success=False,
                        status="auth_failed",
                        latency_ms=latency,
                        message=f"Authentication failed (HTTP {resp.status_code}): Invalid or unauthorized API key/token.",
                        http_status_code=resp.status_code,
                    )
            except (httpx.ConnectError, httpx.ConnectTimeout):
                raise
            except Exception as e:
                logger.debug(f"/models request exception, trying chat completions ping: {e}")

            # Second attempt: fallback to 1-token /chat/completions ping if /models returned 404 or failed
            target_model = request.model_id or "gpt-4o"
            chat_url = f"{raw_url}/chat/completions"
            chat_payload = {
                "model": target_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }
            chat_resp = await client.post(chat_url, json=chat_payload)
            latency = round((time.perf_counter() - start_time) * 1000, 2)

            if chat_resp.status_code == 200:
                return TestProviderConnectionResponse(
                    success=True,
                    status="connected",
                    latency_ms=latency,
                    message="API token and endpoint verified via test completion.",
                    available_models=[target_model] if target_model else [],
                    http_status_code=200,
                )
            elif chat_resp.status_code in (401, 403):
                return TestProviderConnectionResponse(
                    success=False,
                    status="auth_failed",
                    latency_ms=latency,
                    message=f"Authentication failed (HTTP {chat_resp.status_code}): Invalid or unauthorized API key.",
                    http_status_code=chat_resp.status_code,
                )
            elif chat_resp.status_code == 404:
                return TestProviderConnectionResponse(
                    success=False,
                    status="model_not_found",
                    latency_ms=latency,
                    message=f"Endpoint reached, but model '{target_model}' was not found. Please verify model name.",
                    http_status_code=404,
                )
            else:
                return TestProviderConnectionResponse(
                    success=False,
                    status="error",
                    latency_ms=latency,
                    message=f"Provider endpoint returned HTTP {chat_resp.status_code}: {chat_resp.text[:200]}",
                    http_status_code=chat_resp.status_code,
                )

    except (httpx.ConnectError, httpx.ConnectTimeout):
        return TestProviderConnectionResponse(
            success=False,
            status="unreachable",
            message=f"Endpoint unreachable at '{raw_url}'. Verify URL hostname, protocol (http/https), and port.",
        )
    except Exception as e:
        return TestProviderConnectionResponse(
            success=False,
            status="error",
            message=f"Connection test error: {str(e)}",
        )

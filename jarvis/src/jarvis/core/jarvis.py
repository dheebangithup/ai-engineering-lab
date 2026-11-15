"""
Core J.A.R.V.I.S. Orchestrator.
The unified entry point integrating Provider Gateway, Decision Engine,
Tools Gateway, MCP Multi-Server Engine, and the Runtime Agent Hub.
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional
from jarvis.agents.agent_builder import AgentBuilder
from jarvis.agents.agent_hub import AgentHub
from jarvis.agents.schemas import ExecutionStep
from jarvis.core.schemas import JarvisRequest, JarvisResponse, JarvisSession, PendingAction
from jarvis.decision.decision_engine import DecisionEngine
from jarvis.decision.schemas import TaskClassification, TaskComplexity, TaskIntent
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.logger import get_logger
from jarvis.mcp.mcp_manager import MCPManager
from jarvis.prompts.prompt_composer import PromptComposer
from jarvis.tools.implementations.filesystem import (
    list_files,
    read_file,
    search_files,
    write_file,
)
from jarvis.tools.implementations.shell import run_command
from jarvis.tools.permissions import PermissionInterceptor
from jarvis.tools.tool_gateway import ToolsGateway
from jarvis.workspace import Workspace, get_workspace

logger = get_logger("core.jarvis")

AFFIRMATIVE_KEYWORDS = {
    "yes", "y", "approve", "approved", "confirm", "confirmed",
    "proceed", "sure", "ok", "okay", "go ahead", "do it", "allow",
    "grant", "run it", "execute", "accept", "i approve", "yes please",
}
NEGATIVE_KEYWORDS = {
    "no", "n", "deny", "denied", "cancel", "canceled", "cancelled",
    "stop", "abort", "reject", "don't", "dont", "never mind", "nevermind",
}


class Jarvis:
    """The central J.A.R.V.I.S. Personal AI Agent."""

    def __init__(
        self,
        workspace: Optional[Workspace] = None,
        provider_gateway: Optional[ProviderGateway] = None,
        tools_gateway: Optional[ToolsGateway] = None,
        permission_interceptor: Optional[PermissionInterceptor] = None,
    ):
        self.workspace = workspace or get_workspace()
        self.workspace.initialize()

        # 1. Foundation Gateways
        self.provider_gateway = provider_gateway or ProviderGateway()
        self.permissions = permission_interceptor or PermissionInterceptor()
        self.tools_gateway = tools_gateway or ToolsGateway(permission_interceptor=self.permissions)

        # 2. Decision Engine (Sub-5ms Decision Model)
        self.decision_engine = DecisionEngine(provider_gateway=self.provider_gateway)

        # 3. Multi-Server MCP Manager
        self.mcp_manager = MCPManager(tools_gateway=self.tools_gateway)

        # 4. Prompt & Agent Hub
        self.prompt_composer = PromptComposer()
        self.agent_hub = AgentHub()
        self.agent_builder = AgentBuilder(
            provider_gateway=self.provider_gateway,
            tools_gateway=self.tools_gateway,
            prompt_composer=self.prompt_composer,
            agent_hub=self.agent_hub,
        )

        # 5. Session State
        self._sessions: Dict[str, JarvisSession] = {}
        self._is_initialized = False

    async def initialize(self) -> "Jarvis":
        """Bootstrap built-in tools and connect enabled MCP servers."""
        if self._is_initialized:
            return self

        logger.info("Initializing J.A.R.V.I.S. Core Systems...")

        # Register built-in filesystem and shell tools
        self.tools_gateway.register_tool(list_files)
        self.tools_gateway.register_tool(read_file)
        self.tools_gateway.register_tool(write_file)
        self.tools_gateway.register_tool(search_files)
        self.tools_gateway.register_tool(run_command)

        # Initialize external MCP servers (Strata Memory, etc.)
        try:
            bridged = await self.mcp_manager.initialize_servers()
            logger.info(f"Connected MCP servers: {list(bridged.keys())}")
        except Exception as e:
            logger.warning(f"MCP server initialization warning: {e}")

        self._is_initialized = True
        logger.info("J.A.R.V.I.S. initialization complete.")
        return self

    def get_or_create_session(self, session_id: str) -> JarvisSession:
        """Retrieve active session or create a new session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = JarvisSession(session_id=session_id)
        return self._sessions[session_id]

    async def approve_pending_permission(
        self,
        session_id: str,
        approved: bool,
        action_token: Optional[str] = None,
    ) -> JarvisResponse:
        """
        Explicitly approve or deny an action waiting for human authorization.
        Can be invoked via interactive UI buttons or chat message resolution.
        """
        session = self.get_or_create_session(session_id)
        pending = session.pending_action
        if not pending:
            return JarvisResponse(
                query="permission_approval",
                answer="No action is currently pending authorization in this session.",
                classification=TaskClassification(
                    complexity=TaskComplexity.SIMPLE,
                    intent=TaskIntent.CONVERSATION,
                    suggested_agent="direct_agent",
                    requires_planning=False,
                ),
                agent_used="permission_orchestrator",
                provider_used="system",
                model_used="interactive_permission_manager",
            )

        if action_token and pending.action_token != action_token:
            return JarvisResponse(
                query="permission_approval",
                answer="Action token mismatch or expired. Action was not executed.",
                classification=TaskClassification(
                    complexity=TaskComplexity.SIMPLE,
                    intent=TaskIntent.CONVERSATION,
                    suggested_agent="direct_agent",
                    requires_planning=False,
                ),
                agent_used="permission_orchestrator",
                provider_used="system",
                model_used="interactive_permission_manager",
            )

        # Clear pending action from session
        session.pending_action = None

        if not approved:
            answer = f"Authorization denied. The pending execution of `{pending.tool_id}` was canceled."
            session.history.append({"role": "user", "content": "Deny permission"})
            session.history.append({"role": "assistant", "content": answer})
            return JarvisResponse(
                query="deny",
                answer=answer,
                classification=TaskClassification(
                    complexity=TaskComplexity.SIMPLE,
                    intent=TaskIntent.CONVERSATION,
                    suggested_agent="direct_agent",
                    requires_planning=False,
                ),
                agent_used="permission_orchestrator",
                provider_used="system",
                model_used="interactive_permission_manager",
            )

        # Execute pending action with bypass_permission=True
        start_time = time.perf_counter()
        res = await self.tools_gateway.execute_tool(
            tool_id=pending.tool_id,
            arguments=pending.arguments,
            bypass_permission=True,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        status_str = "successfully" if res.success else "with an error"
        answer_lines = [
            f"✅ **Permission Granted**: Executed `{pending.tool_id}` {status_str}."
        ]
        if res.error:
            answer_lines.append(f"\n⚠️ **Error**: {res.error}")
        if res.data is not None:
            if isinstance(res.data, (dict, list)):
                answer_lines.append(f"\n**Execution Result**:\n```json\n{json.dumps(res.data, indent=2)}\n```")
            else:
                answer_lines.append(f"\n**Execution Result**:\n{res.data}")

        answer = "\n".join(answer_lines)
        session.history.append({"role": "user", "content": "Approve permission"})
        session.history.append({"role": "assistant", "content": answer})

        tool_result_dict = res.model_dump()
        tool_result_dict["arguments"] = pending.arguments

        return JarvisResponse(
            query="approve",
            answer=answer,
            classification=TaskClassification(
                complexity=TaskComplexity.SIMPLE,
                intent=TaskIntent.SYSTEM_COMMAND,
                suggested_agent="direct_agent",
                requires_planning=False,
            ),
            agent_used="permission_orchestrator",
            tools_used=[pending.tool_id],
            tool_results=[tool_result_dict],
            steps=[
                ExecutionStep(
                    step_number=1,
                    thought=f"Executing authorized pending tool '{pending.tool_id}'",
                    action_tool=pending.tool_id,
                    action_args=pending.arguments,
                    observation=json.dumps(tool_result_dict),
                )
            ],
            provider_used="system",
            model_used="interactive_permission_manager",
            execution_time_ms=round(duration_ms, 2),
        )

    async def process(self, request_or_query: str | JarvisRequest) -> JarvisResponse:
        """
        Main execution pipeline:
        1. Classify Query (Decision Engine)
        2. Runtime Agent Composition (Agent Builder + Memory Recall + Meta-Tools)
        3. Agent Execution Loop
        4. Session History Update
        5. Autonomous Post-Task Feedback
        """
        if not self._is_initialized:
            await self.initialize()

        start_time = time.perf_counter()

        # Normalize request
        if isinstance(request_or_query, str):
            request = JarvisRequest(query=request_or_query)
        else:
            request = request_or_query

        session = self.get_or_create_session(request.session_id)
        logger.info(f"Processing query: '{request.query}' in session '{session.session_id}'")

        # Step 0: Check if session has a pending permission action waiting for response
        if session.pending_action:
            q_clean = request.query.strip().lower()
            if q_clean in AFFIRMATIVE_KEYWORDS or any(q_clean.startswith(kw) for kw in ["yes", "approve", "confirm", "proceed", "sure", "allow", "grant", "ok"]):
                return await self.approve_pending_permission(session.session_id, approved=True)
            elif q_clean in NEGATIVE_KEYWORDS or any(q_clean.startswith(kw) for kw in ["no", "deny", "cancel", "stop", "abort", "reject", "don't"]):
                return await self.approve_pending_permission(session.session_id, approved=False)

        # Step 1: Decision Engine Routing
        classification: TaskClassification = await self.decision_engine.classify(
            query=request.query,
            context=request.context_override,
        )

        # Step 2: Runtime Agent Composition
        agent, agent_request = await self.agent_builder.build(
            query=request.query,
            classification=classification,
            session_history=session.history,
            preferred_provider=request.preferred_provider,
            model_override=request.model_override,
        )

        # Step 3: Execute Agent
        agent_resp = await agent.execute(agent_request)

        # Step 4: Handle Pending Authorization if action requires human confirmation
        pending_dict = None
        if agent_resp.pending_permission:
            action_token = f"act_{uuid.uuid4().hex[:8]}"
            pending = PendingAction(
                action_token=action_token,
                tool_id=agent_resp.pending_permission.get("tool_id", ""),
                tool_name=agent_resp.pending_permission.get("tool_name", ""),
                permission_tier=agent_resp.pending_permission.get("permission_tier", "dangerous"),
                arguments=agent_resp.pending_permission.get("arguments", {}),
                reason=agent_resp.pending_permission.get("reason", "Action requires human approval"),
                created_at=time.time(),
            )
            session.pending_action = pending
            pending_dict = pending.model_dump()

        # Step 5: Update Session Conversation History
        session.history.append({"role": "user", "content": request.query})
        session.history.append({"role": "assistant", "content": agent_resp.answer})

        # Step 6: Autonomous Post-Task Memory Learning & Ingestion
        # 6a. Autonomous Ingestion Safety Net: Persist durable profile, identity, or project facts
        if classification.requires_memory_ingest and "memory_ingest" not in agent_resp.tools_used:
            try:
                if self.tools_gateway.registry.get_definition("memory_ingest"):
                    logger.info(f"Autonomous background ingest for query: '{request.query[:50]}...'")
                    ingest_res = await self.tools_gateway.execute_tool(
                        "memory_ingest",
                        {"raw_text": request.query},
                    )
                    if ingest_res.success:
                        agent_resp.tools_used.append("memory_ingest")
                        agent_resp.tool_results.append(ingest_res.model_dump())
            except Exception as e:
                logger.warning(f"Autonomous memory ingest encountered an error: {e}")

        # 6b. Mandatory Evolutionary Feedback & Reinforcement
        # If the agent hasn't already called memory_feedback, reinforce or self-heal based on outcome
        if "memory_feedback" not in agent_resp.tools_used and (agent_resp.tools_used or classification.intent.value not in ("conversation", "unknown")):
            try:
                if self.tools_gateway.registry.get_definition("memory_feedback"):
                    procedure = classification.intent.value
                    if agent_resp.success:
                        logger.info(f"Reinforcing procedural memory for '{procedure}' (success=True)")
                        await self.tools_gateway.execute_tool(
                            "memory_feedback",
                            {
                                "procedure_name": procedure,
                                "success": True,
                            },
                        )
                    else:
                        logger.info(f"Reporting failure feedback for '{procedure}' self-healing runbook evolution")
                        await self.tools_gateway.execute_tool(
                            "memory_feedback",
                            {
                                "procedure_name": procedure,
                                "success": False,
                                "failure_reason": agent_resp.error or "Agent task execution encountered an error",
                            },
                        )
            except Exception as e:
                logger.warning(f"Memory feedback reinforcement encountered an error: {e}")

        total_time_ms = (time.perf_counter() - start_time) * 1000

        return JarvisResponse(
            query=request.query,
            answer=agent_resp.answer,
            classification=classification,
            agent_used=agent_resp.agent_template,
            tools_used=agent_resp.tools_used,
            tool_results=agent_resp.tool_results,
            steps=agent_resp.steps,
            pending_permission=pending_dict,
            provider_used=agent_resp.provider_used,
            model_used=agent_resp.model_used,
            fallback_occurred=agent_resp.fallback_occurred,
            failover_history=agent_resp.failover_history,
            execution_time_ms=round(total_time_ms, 2),
        )

    async def shutdown(self) -> None:
        """Clean up active MCP server connections and HTTP client pools."""
        logger.info("Shutting down J.A.R.V.I.S...")
        await self.mcp_manager.shutdown()
        await self.provider_gateway.close()
        self._is_initialized = False
        logger.info("J.A.R.V.I.S. shutdown complete.")

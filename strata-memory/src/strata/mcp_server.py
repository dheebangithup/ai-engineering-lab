import argparse
import json
import logging
import sys
from typing import Annotated, Any, Dict, List, Literal, Optional
from pydantic import Field
from fastmcp import FastMCP
from strata.config import settings
from strata.neon_control import maybe_suspend_neon_compute
from strata.service import (
    svc_memory_delete,
    svc_memory_edit,
    svc_memory_feedback,
    svc_memory_ingest,
    svc_memory_prune,
    svc_memory_purge_namespace,
    svc_memory_recall,
    svc_memory_store_explicit,
)

# Direct all logs to stderr to keep stdout pure for JSON-RPC stdio transport
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

mcp = FastMCP(
    name="Strata Memory Engine",
    instructions="""
Strata is a 4-pillar cognitive memory engine backed by Neon Serverless PostgreSQL.
It provides long-term persistence across 4 distinct cognitive layers:
1. Semantic Layer: Atomic facts, user configurations, preferences, and domain truths with bi-temporal validity.
2. Episodic Layer: Timestamped execution traces, situations, actions, outcomes, and utility scores.
3. Procedural Layer: Versioned workflows, runbooks, and skills with Bayesian ranking and self-healing.
4. Entity Graph Layer: Bi-temporal property graph of connected people, projects, servers, and services.

RECOMMENDED AGENT WORKFLOW:
- CALL `memory_recall` BEFORE answering complex questions to retrieve active context and runbooks.
- CALL `memory_ingest` WHEN learning new project facts, preferences, or decisions to persist them.
- CALL `memory_feedback` AFTER executing runbooks to reinforce successful memories or trigger auto-repair on failure.
""",
)


# ============================================================================
# TOOL 1: memory_recall
# ============================================================================
@mcp.tool()
async def memory_recall(
    query: Annotated[
        str,
        Field(
            description=(
                "Natural language search query expressing what information, facts, runbooks, "
                "or entity relationships you need to retrieve (e.g., 'What database and region are used?')."
            )
        ),
    ],
    namespace: Annotated[
        str,
        Field(
            default="default",
            description=(
                "Multi-tenancy isolation namespace. Defaults to 'default'. Use the same namespace "
                "used when storing memories to retrieve matching records."
            ),
        ),
    ] = "default",
    pillars: Annotated[
        Optional[List[Literal["semantic", "episodic", "procedural", "entity"]]],
        Field(
            default=None,
            description=(
                "List of memory pillars to search. Defaults to all 4 pillars: "
                "['semantic', 'episodic', 'procedural', 'entity']. Specify a subset to narrow results."
            ),
        ),
    ] = None,
    top_k: Annotated[
        int,
        Field(
            default=5,
            ge=1,
            le=25,
            description="Maximum number of candidate memories to return per pillar (default: 5).",
        ),
    ] = 5,
    token_budget: Annotated[
        int,
        Field(
            default=1500,
            ge=100,
            le=8000,
            description=(
                "Maximum token budget for the returned XML context block (default: 1500). "
                "The engine dynamically packs the highest-scoring memories and safely closes XML tags."
            ),
        ),
    ] = 1500,
) -> str:
    """Retrieve relevant memories across the 4 Cognitive Memory Pillars (<15ms, Zero-LLM).

    WHEN TO USE:
    - At the start of a user session or conversation to load context and preferences.
    - Before answering technical questions, designing architecture, or modifying code.
    - Before executing a multi-step task to look up existing procedural skills and runbooks.

    HOW TO USE:
    - Pass a natural language `query` describing what you need.
    - The tool computes an Ollama embedding (nomic-embed-text, 768d), performs Reciprocal Rank
      Fusion (HNSW vector + BM25 text) on Neon, ranks procedures via Bayesian formula, and
      traverses the active entity graph.
    - Only ACTIVE facts (valid_until IS NULL) are returned; superseded facts are omitted.

    RETURNS:
    - A well-formed XML context block (`<strata_memory_context>`) ready to inject into your prompt,
      guaranteed to fit within your specified `token_budget`.
    """
    try:
        res = await svc_memory_recall(
            query=query,
            namespace=namespace,
            pillars=pillars,
            top_k=top_k,
            token_budget=token_budget,
        )
        return res.formatted_context
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 2: memory_ingest
# ============================================================================
@mcp.tool()
async def memory_ingest(
    raw_text: Annotated[
        str,
        Field(
            description=(
                "Unstructured text containing facts, user preferences, events, skills, or entity relations. "
                "Pass natural language directly without manual JSON formatting."
            )
        ),
    ],
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Target namespace partition for multi-tenancy isolation (default: 'default').",
        ),
    ] = "default",
    fast_mode: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "If True, bypasses Small LLM extraction and performs immediate deterministic insertion "
                "into the semantic pillar (<15ms latency). If False (default), uses Ollama (qwen3:8b) "
                "to autonomously route facts, extract graph triples, and supersede contradictions."
            ),
        ),
    ] = False,
    source_id: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Optional external audit reference ID (e.g. git commit hash, session ID, ticket number).",
        ),
    ] = None,
    ttl_seconds: Annotated[
        Optional[int],
        Field(
            default=None,
            description="Optional time-to-live in seconds. After this duration, the memory soft-expires.",
        ),
    ] = None,
) -> str:
    """Autonomously ingest and route unstructured information across the 4 Memory Pillars.

    WHEN TO USE:
    - When the user shares new project decisions, architecture choices, credentials, or preferences.
    - When an event occurs that updates or contradicts previous project knowledge.
    - When you want Strata to automatically figure out whether the input is a fact, an event,
      a reusable procedure, or a relationship between entities.

    HOW TO USE:
    - Pass the raw conversation snippet or statement in `raw_text`.
    - Strata's internal Small LLM (qwen3:8b) pre-fetches similar existing memories, checks for
      contradictions, marks outdated records as superseded (valid_until = NOW()), and inserts
      new structured records across the 4 pillars.

    RETURNS:
    - JSON summary containing created IDs, superseded IDs, and counts per pillar.
    """
    try:
        res = await svc_memory_ingest(
            raw_text=raw_text,
            namespace=namespace,
            fast_mode=fast_mode,
            source_id=source_id,
            ttl_seconds=ttl_seconds,
        )
        return res.model_dump_json(indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 3: memory_store_explicit
# ============================================================================
@mcp.tool()
async def memory_store_explicit(
    pillar: Annotated[
        Literal["semantic", "episodic", "procedural", "entity"],
        Field(
            description=(
                "Target pillar to write to: "
                "'semantic' (atomic facts), 'episodic' (event traces), "
                "'procedural' (versioned runbooks), or 'entity' (graph nodes & edges)."
            )
        ),
    ],
    payload: Annotated[
        Dict[str, Any],
        Field(
            description=(
                "Structured dictionary matching the target pillar schema: "
                "• semantic: {'summary': str, 'tags': list[str], 'confidence': float} "
                "• episodic: {'summary': str, 'situation': str, 'action_taken': str, 'outcome': str, 'success': bool} "
                "• procedural: {'name': str, 'description': str, 'trigger_condition': str, 'steps': list[str]} "
                "• entity: {'source_name': str, 'source_type': str, 'relation_type': str, 'target_name': str, 'target_type': str, 'fact_summary': str}"
            )
        ),
    ],
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
    ttl_seconds: Annotated[
        Optional[int],
        Field(
            default=None,
            description="Optional time-to-live in seconds. After this duration, the memory soft-expires.",
        ),
    ] = None,
) -> str:
    """Direct, Zero-LLM structured insertion into a specific Memory Pillar (<10ms).

    WHEN TO USE:
    - When you already know the exact pillar and have structured the memory data.
    - When logging an explicit task outcome (episodic) or registering a formal runbook (procedural).
    - When you want guaranteed zero-LLM latency without extraction overhead.

    HOW TO USE:
    - Specify the target `pillar` and supply the required schema in `payload`.
    """
    try:
        res = await svc_memory_store_explicit(
            pillar=pillar,
            payload=payload,
            namespace=namespace,
            ttl_seconds=ttl_seconds,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 4: memory_edit
# ============================================================================
@mcp.tool()
async def memory_edit(
    target_id_or_name: Annotated[
        str,
        Field(
            description="UUID of the memory item (for semantic/episodic) or name of the procedure/entity."
        ),
    ],
    instruction: Annotated[
        str,
        Field(
            description="Natural language instruction describing the exact modification (e.g., 'Update region to ap-southeast-1')."
        ),
    ],
    pillar: Annotated[
        Literal["semantic", "procedural", "entity"],
        Field(
            default="semantic",
            description="Pillar of the target memory: 'semantic' (default), 'procedural', or 'entity'.",
        ),
    ] = "semantic",
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
) -> str:
    """Modify or supersede an existing memory item using natural language instructions.

    WHEN TO USE:
    - When you need to correct, update, or revise an existing fact, procedure, or entity property.
    - For semantic memories, this preserves bi-temporal history: marks the old record as superseded
      (valid_until = NOW()) and inserts the newly edited fact.
    - For procedures, this modifies steps and increments version (v1 -> v2) with an audit entry.
    """
    try:
        res = await svc_memory_edit(
            target_id_or_name=target_id_or_name,
            instruction=instruction,
            pillar=pillar,
            namespace=namespace,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 5: memory_feedback
# ============================================================================
@mcp.tool()
async def memory_feedback(
    memory_ids_used: Annotated[
        Optional[List[str]],
        Field(
            default=None,
            description="List of memory UUIDs that assisted the agent during task execution.",
        ),
    ] = None,
    procedure_name: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Name of the procedural skill or runbook executed by the agent.",
        ),
    ] = None,
    success: Annotated[
        bool,
        Field(
            default=True,
            description="Whether the task execution was successful (True) or failed (False).",
        ),
    ] = True,
    failure_reason: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "If success=False, provide the error trace or explanation of failure. "
                "Strata's Small LLM will analyze this error and automatically patch the procedure steps."
            ),
        ),
    ] = None,
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
) -> str:
    """Report task execution feedback to adjust utility scores and auto-heal failed runbooks.

    WHEN TO USE:
    - Immediately after completing a task that utilized memories from `memory_recall`.
    - When a procedural workflow or runbook failed in production due to an error.

    HOW IT WORKS:
    - Reinforcement Loop: Successful tasks bump utility_score (+1) on memories used. Failed tasks
      penalize utility_score (-2). High-utility memories rank higher in future recall queries.
    - Self-Healing Runbooks: If `success=False` and `failure_reason` is provided, Strata analyzes
      why the procedure failed, automatically patches `steps[]`, increments the procedure `version`,
      and logs the repair explanation to `changelog`.
    """
    try:
        res = await svc_memory_feedback(
            memory_ids_used=memory_ids_used,
            procedure_name=procedure_name,
            success=success,
            failure_reason=failure_reason,
            namespace=namespace,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 6: memory_delete
# ============================================================================
@mcp.tool()
async def memory_delete(
    target_id: Annotated[
        str,
        Field(
            description="UUID of the memory item to delete, or name of the procedure/entity."
        ),
    ],
    pillar: Annotated[
        Literal["semantic", "episodic", "procedural", "entity"],
        Field(
            default="semantic",
            description="Pillar of the target memory: 'semantic' (default), 'episodic', 'procedural', or 'entity'.",
        ),
    ] = "semantic",
    hard_delete: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "If False (default), performs a soft delete (valid_until = NOW() or is_active = FALSE), "
                "retaining an audit trail while removing from recall. If True, permanently purges the row."
            ),
        ),
    ] = False,
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
) -> str:
    """Soft-inactivate or permanently delete a memory record.

    WHEN TO USE:
    - To prune obsolete or incorrect memories.
    - By default (hard_delete=False), marks valid_until = NOW() to preserve historical audit trails
      while ensuring the record is never returned in future recall operations.
    """
    try:
        res = await svc_memory_delete(
            target_id=target_id,
            pillar=pillar,
            hard_delete=hard_delete,
            namespace=namespace,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 7: memory_prune
# ============================================================================
@mcp.tool()
async def memory_prune(
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace to prune.",
        ),
    ] = "default",
    distill_episodes: Annotated[
        bool,
        Field(
            default=True,
            description="If True, uses Small LLM to distill reusable runbooks and permanent facts before purging raw episodes.",
        ),
    ] = True,
    episodic_older_than_days: Annotated[
        Optional[int],
        Field(
            default=30,
            description="Prune episodic memories older than X days (or those whose TTL has expired). Set None to only prune TTL-expired.",
        ),
    ] = 30,
    superseded_older_than_days: Annotated[
        int,
        Field(
            default=90,
            description="Permanently delete historical superseded/soft-deleted rows older than X days.",
        ),
    ] = 90,
    retire_toxic_threshold: Annotated[
        Optional[int],
        Field(
            default=-5,
            description="Automatically soft-retire memories with utility_score <= threshold (default: -5).",
        ),
    ] = -5,
    batch_size: Annotated[
        int,
        Field(
            default=20,
            description="Maximum number of expired episodes to distill and prune per invocation.",
        ),
    ] = 20,
) -> str:
    """Consolidates and prunes expired or stale memories using Cognitive Distillation.

    WHEN TO USE:
    - Periodically to reclaim storage and keep retrieval fast.
    - To safely retire old episodic logs without losing hard-won lessons (synthesizes them into runbooks & semantic facts).
    - To purge dead superseded facts and auto-retire toxic memories that repeatedly cause failures.
    """
    try:
        res = await svc_memory_prune(
            namespace=namespace,
            distill_episodes=distill_episodes,
            episodic_older_than_days=episodic_older_than_days,
            superseded_older_than_days=superseded_older_than_days,
            retire_toxic_threshold=retire_toxic_threshold,
            batch_size=batch_size,
        )
        return res.model_dump_json(indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 8: memory_purge_namespace
# ============================================================================
@mcp.tool()
async def memory_purge_namespace(
    namespace: Annotated[
        str,
        Field(
            description="Name of the namespace to completely erase.",
        ),
    ],
    confirm: Annotated[
        bool,
        Field(
            default=False,
            description="Explicit confirmation flag (must be True to execute destructive wipe).",
        ),
    ] = False,
) -> str:
    """Permanently purges all memories, procedures, and entity nodes/edges in a namespace.

    WHEN TO USE:
    - User privacy / GDPR Right to be Forgotten requests.
    - Resetting temporary test or staging namespaces.
    """
    try:
        res = await svc_memory_purge_namespace(
            namespace=namespace,
            confirm=confirm,
        )
        return res.model_dump_json(indent=2)
    finally:
        await maybe_suspend_neon_compute()


def main() -> None:
    """Entry point for FastMCP server."""
    parser = argparse.ArgumentParser(description="Strata FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="FastMCP transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE transport (default: 8000)",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

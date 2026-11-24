"""Strata Working Memory Buffer (Short-Term Memory Layer).

Implements the Short-Term Working Context and Protected Eviction Policy
defined in Agent Memory Architect:
  1. Manages active trajectory messages, tool calls, and tool outputs.
  2. Flags active tool results as `protected=True` until dependent steps finish.
  3. Enforces context token budgets by evicting oldest non-protected items first,
     permanently preventing the Eviction Policy Bug (repeated tool retries).
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class WorkingMemoryItem:
    item_id: str
    session_id: str
    turn_id: int
    role: str  # "user" | "assistant" | "tool" | "system"
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    is_tool_output: bool = False
    protected: bool = False  # Pinned against budget eviction
    token_count: int = 0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkingMemoryManager:
    """In-memory active working context buffer partitioned by (namespace, session_id)."""

    def __init__(self, default_max_tokens: int = 2000):
        self.default_max_tokens = default_max_tokens
        # Key: (namespace, session_id) -> List[WorkingMemoryItem]
        self._buffers: Dict[str, List[WorkingMemoryItem]] = {}

    def _get_key(self, namespace: str, session_id: str) -> str:
        return f"{namespace}:{session_id}"

    def add_message(
        self,
        namespace: str,
        session_id: str,
        role: str,
        content: str,
        turn_id: Optional[int] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        is_tool_output: bool = False,
        protected: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkingMemoryItem:
        key = self._get_key(namespace, session_id)
        if key not in self._buffers:
            self._buffers[key] = []

        # Simple ~4 chars per token approximation
        approx_tokens = max(1, len(content) // 4)
        current_turn = turn_id if turn_id is not None else len(self._buffers[key]) + 1

        item = WorkingMemoryItem(
            item_id=str(uuid4()),
            session_id=session_id,
            turn_id=current_turn,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            is_tool_output=is_tool_output,
            protected=protected,
            token_count=approx_tokens,
            metadata=metadata or {},
        )
        self._buffers[key].append(item)
        return item

    def add_tool_output(
        self,
        namespace: str,
        session_id: str,
        tool_call_id: str,
        tool_name: str,
        content: str,
        protected: bool = True,  # Protected by default until downstream steps finish
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkingMemoryItem:
        """Adds a tool execution result, pinned as protected=True by default."""
        return self.add_message(
            namespace=namespace,
            session_id=session_id,
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            is_tool_output=True,
            protected=protected,
            metadata=metadata or {},
        )

    def unprotect_tool(self, namespace: str, session_id: str, tool_call_id: str) -> bool:
        """Unprotects a tool result once dependent reasoning finishes, allowing eviction if needed."""
        key = self._get_key(namespace, session_id)
        items = self._buffers.get(key, [])
        unprotected = False
        for item in items:
            if item.tool_call_id == tool_call_id and item.protected:
                item.protected = False
                unprotected = True
        return unprotected

    def enforce_budget(
        self,
        namespace: str,
        session_id: str,
        max_tokens: Optional[int] = None,
    ) -> List[WorkingMemoryItem]:
        """Evicts oldest non-protected items until buffer fits under max_tokens budget.
        
        Items with protected=True are NEVER evicted.
        """
        key = self._get_key(namespace, session_id)
        items = self._buffers.get(key, [])
        limit = max_tokens or self.default_max_tokens

        total_tokens = sum(it.token_count for it in items)
        if total_tokens <= limit:
            return items

        # Evict oldest non-protected items
        evicted = []
        kept = []
        for it in items:
            if total_tokens > limit and not it.protected:
                total_tokens -= it.token_count
                evicted.append(it)
            else:
                kept.append(it)

        self._buffers[key] = kept
        return kept

    def get_items(self, namespace: str, session_id: str) -> List[WorkingMemoryItem]:
        key = self._get_key(namespace, session_id)
        return list(self._buffers.get(key, []))

    def clear(self, namespace: str, session_id: str) -> int:
        key = self._get_key(namespace, session_id)
        count = len(self._buffers.get(key, []))
        if key in self._buffers:
            del self._buffers[key]
        return count


# Singleton working memory manager
working_memory = WorkingMemoryManager()

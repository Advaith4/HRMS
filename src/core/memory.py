"""
src/core/memory.py
Dual-Tier Memory Architecture for Agentic Workflows.
Tier 1: Ephemeral Short-Term Working Memory (Session cache)
Tier 2: Persistent Long-Term Memory (Database & Vector Store bridge)
"""
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ShortTermWorkingMemory:
    """
    In-memory LRU context buffer for active agentic tasks.
    Preserves intermediate thoughts, tool execution steps, and task scratchpads.
    """
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self._store: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def set_context(self, session_id: str, key: str, value: Any) -> None:
        if session_id not in self._store:
            if len(self._store) >= self.capacity:
                self._store.popitem(last=False)
            self._store[session_id] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "data": {},
                "history": [],
            }
        self._store[session_id]["data"][key] = value
        self._store[session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._store.move_to_end(session_id)

    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        if session_id in self._store:
            self._store.move_to_end(session_id)
            return self._store[session_id]["data"].get(key, default)
        return default

    def append_step(self, session_id: str, agent: str, action: str, output: Any) -> None:
        if session_id not in self._store:
            self.set_context(session_id, "initialized", True)
        self._store[session_id]["history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "action": action,
            "output": output,
        })

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        if session_id in self._store:
            return list(self._store[session_id]["history"])
        return []

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)


# Global singleton instance for short-term working memory
working_memory = ShortTermWorkingMemory(capacity=200)


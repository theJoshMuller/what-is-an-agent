# app/llm/base.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCall:
    """Represents a single tool call returned by the LLM."""
    id: str
    name: str
    arguments: dict  # Already parsed from JSON


@dataclass
class StreamChunk:
    """Yielded by streaming LLM clients."""
    text: str = ""
    tool_calls: list = field(default_factory=list)  # list[ToolCall]
    done: bool = False
    error: Optional[str] = None


# Type alias for a chat message dict
Message = dict  # {"role": "user"|"assistant"|"tool", "content": str}

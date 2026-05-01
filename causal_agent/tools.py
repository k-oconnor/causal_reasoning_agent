"""
causal_agent/tools.py

Tool-calling primitives shared across all LLM backends.

These types form the standard interface between the agent's planning loop
and any external capability (web search, code execution, kRPC, etc.).
No backend-specific logic lives here.

Design
------
ToolDefinition  – schema for one tool (name + description + JSON Schema params).
ToolCall        – a single call request emitted by the model.
ToolResult      – the result of executing a ToolCall, returned to the model.
LLMResponse     – union return type from complete_with_tools(): either a final
                  text response or a list of ToolCalls to execute.
ToolRegistry    – maps tool names to Python callables + their schemas.
                  Pass a registry to complete_with_tools(); it handles schema
                  serialisation and call dispatch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

@dataclass
class ToolDefinition:
    """
    Schema for a single tool the agent may call.

    Parameters
    ----------
    name        : identifier the model uses in tool_calls.
    description : plain-English explanation of what the tool does and when
                  to use it. Quality here directly affects call accuracy.
    parameters  : JSON Schema object describing the arguments. Example:
                  {
                    "type": "object",
                    "properties": {
                      "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                  }
    """

    name: str
    description: str
    parameters: dict[str, Any]

    # -- Serialisation helpers ------------------------------------------------

    def to_openai_schema(self) -> dict:
        """OpenAI / DeepSeek function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_schema(self) -> dict:
        """Anthropic tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def to_gemini_schema(self) -> dict:
        """
        Gemini function declaration dict.

        Gemini uses uppercase type names ("STRING", "OBJECT") instead of the
        JSON Schema lowercase convention ("string", "object"). We convert
        recursively.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": _jsonschema_to_gemini(self.parameters),
        }


@dataclass
class ToolCall:
    """A tool invocation requested by the model in one completion turn."""

    id: str                     # opaque call ID (echoed back in ToolResult)
    name: str                   # must match a registered ToolDefinition.name
    arguments: dict[str, Any]   # parsed from model JSON output


@dataclass
class ToolResult:
    """The result of executing a ToolCall, to be returned to the model."""

    tool_call_id: str   # matches ToolCall.id
    name: str
    content: str        # always a string; serialise complex objects before here

    def to_openai_message(self) -> dict:
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": self.content,
        }

    def to_anthropic_message(self) -> dict:
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_call_id,
            "content": self.content,
        }


@dataclass
class LLMResponse:
    """
    Return type from BaseLLM.complete_with_tools().

    Exactly one of content or tool_calls will be populated per turn:
    - tool_calls non-empty  → model wants to call tools; execute and loop.
    - content non-None      → model is done; this is the final answer.
    """

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_message: dict[str, Any] | None = None

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @property
    def is_final(self) -> bool:
        return self.content is not None and not self.tool_calls


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """
    Maps tool names to callables and their ToolDefinitions.

    Usage
    -----
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="web_search",
            description="Search the web for current information.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        fn=my_search_function,
    )

    # Pass to complete_with_tools:
    response = llm.complete_with_tools(messages, registry)

    # Dispatch a ToolCall from the model:
    result = registry.dispatch(tool_call)
    """

    def __init__(self) -> None:
        self._entries: dict[str, tuple[ToolDefinition, Callable]] = {}
        self.use_kripke_tools = False

    def register(self, definition: ToolDefinition, fn: Callable) -> "ToolRegistry":
        """Register a tool. Returns self for chaining."""
        self._entries[definition.name] = (definition, fn)
        return self

    def enable_kripke_tools(self) -> "ToolRegistry":
        """Request live Kripke tools be attached by the planner at decision time."""
        self.use_kripke_tools = True
        return self

    # -- Schema access --------------------------------------------------------

    def definitions(self) -> list[ToolDefinition]:
        return [defn for defn, _ in self._entries.values()]

    def openai_schemas(self) -> list[dict]:
        return [defn.to_openai_schema() for defn, _ in self._entries.values()]

    def anthropic_schemas(self) -> list[dict]:
        return [defn.to_anthropic_schema() for defn, _ in self._entries.values()]

    def gemini_schemas(self) -> list[dict]:
        return [defn.to_gemini_schema() for defn, _ in self._entries.values()]

    # -- Dispatch -------------------------------------------------------------

    def dispatch(self, tool_call: ToolCall) -> ToolResult:
        """Execute tool_call and return a ToolResult ready to send back to the model."""
        if tool_call.name not in self._entries:
            content = f"Error: unknown tool '{tool_call.name}'"
        else:
            _, fn = self._entries[tool_call.name]
            try:
                raw = fn(**tool_call.arguments)
                content = raw if isinstance(raw, str) else json.dumps(raw, default=str)
            except Exception as exc:
                content = f"Error executing '{tool_call.name}': {exc}"

        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            content=content,
        )

    def __bool__(self) -> bool:
        return bool(self._entries)

    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_GEMINI_TYPE_MAP = {
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}


def _jsonschema_to_gemini(schema: dict) -> dict:
    """
    Recursively convert a JSON Schema dict to Gemini's parameter format.

    Gemini expects uppercase type names and uses "properties" the same way,
    but wraps the whole thing differently from JSON Schema.
    """
    result: dict[str, Any] = {}

    if "type" in schema:
        result["type"] = _GEMINI_TYPE_MAP.get(schema["type"], schema["type"].upper())

    if "description" in schema:
        result["description"] = schema["description"]

    if "properties" in schema:
        result["properties"] = {
            k: _jsonschema_to_gemini(v) for k, v in schema["properties"].items()
        }

    if "required" in schema:
        result["required"] = schema["required"]

    if "items" in schema:
        result["items"] = _jsonschema_to_gemini(schema["items"])

    if "enum" in schema:
        result["enum"] = schema["enum"]

    return result

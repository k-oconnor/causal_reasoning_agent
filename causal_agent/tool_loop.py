"""
Shared ReAct-style tool loop utilities.

The loop is intentionally backend-agnostic: callers supply OpenAI-style
messages, a ToolRegistry, and optional callbacks for logging or early
termination. Backends translate the messages internally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from causal_agent.llm import BaseLLM
from causal_agent.tools import ToolCall, ToolRegistry, ToolResult


ToolCallCallback = Callable[[int, ToolCall], None]
ToolResultCallback = Callable[[int, ToolCall, ToolResult], Optional[str]]


@dataclass
class ToolLoopResult:
    """Final output and trace from a bounded tool-calling loop."""

    content: str
    iterations: int
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    truncated: bool = False


def run_tool_loop(
    *,
    llm: BaseLLM,
    registry: ToolRegistry,
    messages: list[dict[str, Any]],
    system: str = "",
    max_iterations: int = 8,
    max_tokens: int | None = None,
    on_tool_call: ToolCallCallback | None = None,
    on_tool_result: ToolResultCallback | None = None,
) -> ToolLoopResult:
    """
    Run a bounded Reason -> Act -> Observe loop until the model returns final text.

    `on_tool_result` may return a final content string to terminate early after a
    specific tool call, which is how ResearchPlanner handles plan_complete.
    """
    loop_messages = list(messages)
    tool_call_log: list[dict[str, Any]] = []
    iterations = 0
    kwargs = {"max_tokens": max_tokens} if max_tokens is not None else {}

    for iterations in range(1, max_iterations + 1):
        response = llm.complete_with_tools(
            messages=loop_messages,
            registry=registry,
            system=system,
            **kwargs,
        )

        if response.is_final:
            return ToolLoopResult(
                content=response.content or "",
                iterations=iterations,
                tool_calls=tool_call_log,
                messages=loop_messages,
            )

        if not response.tool_calls:
            return ToolLoopResult(
                content=response.content or "",
                iterations=iterations,
                tool_calls=tool_call_log,
                messages=loop_messages,
            )

        loop_messages.append(
            response.assistant_message or assistant_tool_message(response.tool_calls)
        )

        for tc in response.tool_calls:
            if on_tool_call is not None:
                on_tool_call(iterations, tc)

            result = registry.dispatch(tc)
            entry = {
                "call": {"name": tc.name, "arguments": tc.arguments},
                "result": result.content,
            }
            tool_call_log.append(entry)
            loop_messages.append(result.to_openai_message())

            if on_tool_result is not None:
                final_content = on_tool_result(iterations, tc, result)
                if final_content is not None:
                    return ToolLoopResult(
                        content=final_content,
                        iterations=iterations,
                        tool_calls=tool_call_log,
                        messages=loop_messages,
                    )

    last_content = ""
    if loop_messages:
        last_content = str(loop_messages[-1].get("content") or "")

    return ToolLoopResult(
        content=last_content,
        iterations=iterations,
        tool_calls=tool_call_log,
        messages=loop_messages,
        truncated=True,
    )


def assistant_tool_message(tool_calls: list[ToolCall]) -> dict[str, Any]:
    """Build an OpenAI-format assistant message containing tool calls."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": __import__("json").dumps(tc.arguments),
                },
            }
            for tc in tool_calls
        ],
    }

from __future__ import annotations

import unittest
from typing import Any

from causal_agent.llm import BaseLLM
from causal_agent.tool_loop import run_tool_loop
from causal_agent.tools import LLMResponse, ToolCall, ToolDefinition, ToolRegistry


class ToolLoopTests(unittest.TestCase):
    def test_preserves_assistant_message_for_followup_tool_call(self) -> None:
        llm = _ReasoningToolLLM()
        registry = ToolRegistry().register(
            ToolDefinition(
                name="inspect_board",
                description="Inspect the board.",
                parameters={
                    "type": "object",
                    "properties": {"focus": {"type": "string"}},
                    "required": ["focus"],
                },
            ),
            lambda focus: f"inspected {focus}",
        )

        result = run_tool_loop(
            llm=llm,
            registry=registry,
            messages=[{"role": "user", "content": "Choose a move."}],
        )

        self.assertEqual(result.content, '{"action_type": "slide"}')
        self.assertEqual(
            llm.second_messages[1]["reasoning_content"],
            "thinking through options",
        )
        self.assertEqual(llm.second_messages[2]["role"], "tool")


class _ReasoningToolLLM(BaseLLM):
    def __init__(self) -> None:
        self.calls = 0
        self.second_messages: list[dict[str, Any]] = []

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        raise NotImplementedError

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_call = ToolCall(
                id="call_1",
                name="inspect_board",
                arguments={"focus": "legal moves"},
            )
            return LLMResponse(
                tool_calls=[tool_call],
                assistant_message={
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": "thinking through options",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": '{"focus": "legal moves"}',
                            },
                        }
                    ],
                },
            )
        self.second_messages = list(messages)
        return LLMResponse(content='{"action_type": "slide"}')


if __name__ == "__main__":
    unittest.main()

"""
causal_agent/research_planner.py

Recursive, tool-augmented planning phase.

ResearchPlanner runs a ReAct loop (Reason → Act → Observe → repeat) using
native function calling until the LLM emits a final text response.  It has
no knowledge of any specific eval domain — all domain context comes through
the system prompt, skill library, and ToolRegistry injected at construction.

The output is a plain string: the LLM's final answer after it has finished
calling tools.  For the KSP eval this will be a rocket manifest + flight
plan.  For any other eval it will be whatever the mission instructions ask
the agent to produce.

Loop mechanics
--------------
1. Build the initial messages list from the goal (and optionally skills).
2. Call llm.complete_with_tools(messages, registry).
3. If the response has tool_calls:
     a. Append the assistant turn (with tool_calls) to messages.
     b. Dispatch each call via registry.dispatch().
     c. Append tool results to messages.
     d. Go to 2.
4. If the response is final (content set), return the content.
5. If max_iterations is reached, return whatever partial content exists
   with a warning prefix.

Message format
--------------
Uses the OpenAI/DeepSeek wire format throughout:
  {"role": "user",      "content": "..."}
  {"role": "assistant", "content": null, "tool_calls": [...]}
  {"role": "tool",      "tool_call_id": "...", "content": "..."}

Anthropic and Gemini backends translate internally inside their
complete_with_tools() implementations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from causal_agent.llm import BaseLLM
from causal_agent.memory import MemoryStore, MemoryEntry
from causal_agent.tools import ToolRegistry, ToolCall, ToolResult

log = logging.getLogger("causal_agent.research_planner")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class PlanningResult:
    """
    Everything produced by a ResearchPlanner.run() call.

    Attributes
    ----------
    plan        : The LLM's final output — a natural language plan, manifest,
                  script, or whatever the eval instructions requested.
    iterations  : Number of ReAct loop iterations taken.
    tool_calls  : Ordered log of every tool call made and its result.
    truncated   : True if the loop hit max_iterations before the LLM finished.
    """
    plan: str
    iterations: int
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    truncated: bool = False

    def summary(self) -> str:
        status = "TRUNCATED" if self.truncated else "complete"
        return (
            f"PlanningResult [{status}] "
            f"iterations={self.iterations} "
            f"tool_calls={len(self.tool_calls)}"
        )


# ---------------------------------------------------------------------------
# ResearchPlanner
# ---------------------------------------------------------------------------

class ResearchPlanner:
    """
    Runs the planning phase for one goal.

    Parameters
    ----------
    llm            : Any BaseLLM backend that implements complete_with_tools().
    registry       : ToolRegistry populated with whatever tools are available
                     for this eval (web_search, fetch_page, kripke_*, etc.).
    system_prompt  : System-level instructions for the planning phase.
                     Should describe the agent's role, the eval context,
                     and any constraints on the output format.
    skill_docs     : Optional list of skill document strings to prepend to the
                     first user message as reference material.
    max_iterations : Hard cap on ReAct loop iterations (default 20).
    verbose        : Print each tool call and result to stdout.
    """

    def __init__(
        self,
        llm: BaseLLM,
        registry: ToolRegistry,
        system_prompt: str = "",
        skill_docs: list[str] | None = None,
        memory: MemoryStore | None = None,
        max_iterations: int = 20,
        verbose: bool = True,
    ) -> None:
        self._llm = llm
        self._registry = registry
        from causal_agent.prompts import PLANNING_SYSTEM
        self._system = system_prompt or PLANNING_SYSTEM
        self._skills = skill_docs or []
        self._memory = memory
        self._max_iter = max_iterations
        self._verbose = verbose

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, goal: str) -> PlanningResult:
        """
        Execute the ReAct loop for `goal` and return a PlanningResult.
        """
        messages = self._build_initial_messages(goal)
        tool_call_log: list[dict[str, Any]] = []
        iterations = 0

        # Seed the first user message into memory so the execution phase
        # knows what goal the planning phase was working toward.
        self._mem_write(turn=0, kind="goal", source="planner", content=goal)

        # If prior memory exists, prepend a context summary to the first message
        # so the planner benefits from earlier attempts without re-researching.
        if self._memory:
            prior = self._memory.short_term_context(k=30)
            if prior and prior != "(no short-term memory)":
                messages[0]["content"] = (
                    "## Prior Session Context\n"
                    + prior
                    + "\n\n"
                    + messages[0]["content"]
                )

        for iterations in range(1, self._max_iter + 1):
            log.info("-- planning iteration %d / %d --", iterations, self._max_iter)

            response = self._llm.complete_with_tools(
                messages=messages,
                registry=self._registry,
                system=self._system,
            )

            if response.is_final:
                plan_text = response.content or ""
                log.info(
                    "planning complete — %d iterations, %d tool calls, %d chars",
                    iterations, len(tool_call_log), len(plan_text),
                )
                log.debug("final plan:\n%s", plan_text)
                self._mem_write(
                    turn=iterations,
                    kind="plan",
                    source="planner",
                    content=plan_text,
                    metadata={"iterations": iterations, "tool_calls": len(tool_call_log)},
                )
                return PlanningResult(
                    plan=plan_text,
                    iterations=iterations,
                    tool_calls=tool_call_log,
                )

            # -- Tool calls: append assistant turn, dispatch, append results --
            assistant_msg = self._assistant_message(response.tool_calls)
            messages.append(assistant_msg)

            for tc in response.tool_calls:
                self._log_call(tc)
                result: ToolResult = self._registry.dispatch(tc)
                self._log_result(result)

                entry = {"call": {"name": tc.name, "arguments": tc.arguments},
                         "result": result.content}
                tool_call_log.append(entry)

                self._mem_write(
                    turn=iterations,
                    kind="tool_call",
                    source=tc.name,
                    content=result.content,
                    metadata={"arguments": tc.arguments},
                )

                messages.append(result.to_openai_message())

        # Hit max_iterations — return whatever we have.
        last_content = messages[-1].get("content", "") if messages else ""
        log.warning(
            "ResearchPlanner hit max_iterations (%d) without a final response.",
            self._max_iter,
        )
        truncated_plan = (
            f"[WARNING: planning truncated at {self._max_iter} iterations]\n\n"
            + (last_content or "(no content)")
        )
        self._mem_write(
            turn=iterations,
            kind="plan",
            source="planner",
            content=truncated_plan,
            metadata={"truncated": True, "iterations": iterations},
        )
        return PlanningResult(
            plan=truncated_plan,
            iterations=iterations,
            tool_calls=tool_call_log,
            truncated=True,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_initial_messages(self, goal: str) -> list[dict]:
        parts: list[str] = []

        if self._skills:
            parts.append("## Reference Material\n")
            for doc in self._skills:
                parts.append(doc.strip())
                parts.append("")   # blank line between docs

        parts.append("## Goal\n")
        parts.append(goal.strip())

        return [{"role": "user", "content": "\n".join(parts)}]

    def _assistant_message(self, tool_calls: list[ToolCall]) -> dict:
        """Build an OpenAI-format assistant message containing tool_calls."""
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

    def _log_call(self, tc: ToolCall) -> None:
        log.info("tool call >> %s(%s)", tc.name, tc.arguments)

    def _log_result(self, result: ToolResult) -> None:
        preview = result.content[:300].replace("\n", " ")
        suffix = "..." if len(result.content) > 300 else ""
        log.info("tool result << %s: %s%s", result.name, preview, suffix)
        log.debug("tool result full << %s", result.content)

    def _mem_write(
        self,
        turn: int,
        kind: str,
        source: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Write an entry to the shared MemoryStore if one is attached."""
        if self._memory is None:
            return
        self._memory.add(MemoryEntry(
            turn=turn,
            kind=kind,
            source=source,
            content=content,
            metadata=metadata or {},
        ))

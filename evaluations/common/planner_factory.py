"""Planner construction helpers shared by game evaluation runners."""

from __future__ import annotations

from collections.abc import Sequence

from causal_agent.actions import ActionSpec
from causal_agent.acting import ActionError, Actor, GameAction
from causal_agent.feedback import FeedbackKind
from causal_agent.kripke import KripkeModel
from causal_agent.llm import BaseLLM
from causal_agent.memory import MemoryEntry, MemoryStore
from causal_agent.planning import Plan
from causal_agent.planning import Planner

from games.base import GameEnvironment


def build_planner(
    env: GameEnvironment,
    llm: BaseLLM,
    *,
    agent_id: str = "Agent",
    simulate_before_plan: bool = False,
    max_parse_retries: int = 1,
    max_tool_calls: int = 8,
) -> Planner:
    """Build a Planner using the environment's prompt, tools, and preview hook."""
    return Planner(
        llm,
        simulate_before_plan=simulate_before_plan,
        max_parse_retries=max_parse_retries,
        system=env.system_prompt(),
        tools=env.tools(agent_id),
        preview=env.preview,
        max_tool_calls=max_tool_calls,
    )


def plan_action_with_retry(
    *,
    planner: Planner,
    actor: Actor,
    kripke: KripkeModel,
    memory: MemoryStore,
    goal: str,
    agent_id: str,
    action_specs: Sequence[ActionSpec],
    turn: int,
    error_context: str | None = None,
) -> tuple[Plan, GameAction, int]:
    """
    Plan and validate one action, retrying once after invalid planner output.

    Returns `(plan, action, invalid_count)`, where `invalid_count` reflects
    planner outputs rejected before a valid action was produced.
    """
    if error_context:
        _remember_invalid(memory, turn, "env", error_context)

    plan = planner.plan(
        kripke=kripke,
        memory=memory,
        goal=goal,
        agent_id=agent_id,
        action_specs=action_specs,
    )
    try:
        return plan, actor.act(plan, action_specs, agent_id), 0
    except ActionError as exc:
        _remember_invalid(memory, turn, "actor", str(exc))

    replan = planner.plan(
        kripke=kripke,
        memory=memory,
        goal=goal,
        agent_id=agent_id,
        action_specs=action_specs,
    )
    try:
        return replan, actor.act(replan, action_specs, agent_id), 1
    except ActionError as exc:
        _remember_invalid(memory, turn, "actor", str(exc))

    fallback_spec = action_specs[0]
    fallback = Plan(
        intent="fallback after invalid replanning",
        action_type=fallback_spec.action_type,
        parameters=fallback_spec.fallback_payload(),
        reasoning="Planner output remained invalid after one retry; using the first legal example.",
    )
    return fallback, actor.act(fallback, action_specs, agent_id), 2


def _remember_invalid(
    memory: MemoryStore,
    turn: int,
    source: str,
    content: str,
) -> None:
    memory.add(MemoryEntry(
        turn=turn,
        kind=FeedbackKind.ILLEGAL_MOVE.value,
        source=source,
        content=content,
    ))

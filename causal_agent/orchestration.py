"""
causal_agent/orchestration.py

Session control loop.

Orchestration is the only module that imports from all four pillars.
It wires them together but delegates all substantive logic to them:

    observe (env)
        ↓
    FeedbackProcessor  → FeedbackEvent
        ↓
    MemoryStore        ← add event + snapshot KripkeModel
        ↓
    KripkeModel        ← update_with_facts(event.facts)
        ↓
    Planner            → Plan   (reads KripkeModel + MemoryStore)
        ↓
    Actor              → GameAction   (validates + packages Plan)
        ↓
    env.step(action)   → raw feedback (loops back to observe)

SessionResult carries the full outcome for logging, evaluation, and
long-term memory seeding for the next episode.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from causal_agent.actions import ActionSpec
from causal_agent.acting import Actor, ActionError, GameAction
from causal_agent.feedback import FeedbackEvent, FeedbackKind, FeedbackProcessor
from causal_agent.kripke import KripkeModel
from causal_agent.memory import MemoryEntry, MemoryStore
from causal_agent.planning import Plan, Planner

if TYPE_CHECKING:
    from games.base import GameEnvironment

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Per-agent settings injected at Orchestrator construction time."""
    agent_id: str
    goal: str
    max_turns: int = 100
    replan_on_illegal: bool = True   # replan automatically if acting raises ActionError
    verbose: bool = True             # print turn summaries to stdout


# ---------------------------------------------------------------------------
# Session result
# ---------------------------------------------------------------------------

@dataclass
class SessionResult:
    """Everything that happened during one game session."""
    agent_id: str
    total_turns: int
    terminal: bool
    final_reward: float
    actions: list[GameAction] = field(default_factory=list)
    events: list[FeedbackEvent] = field(default_factory=list)
    memory_snapshot: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Session [{self.agent_id}] "
            f"turns={self.total_turns} "
            f"terminal={self.terminal} "
            f"reward={self.final_reward:.2f}"
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Runs one game session for one agent.

    Parameters
    ----------
    env                : the game environment.
    planner            : Planning module.
    actor              : Acting module.
    feedback_processor : Feedback module.
    memory             : Memory module.
    kripke             : initial KripkeModel (constructed by the env or caller).
    config             : per-agent settings.
    """

    def __init__(
        self,
        env: "GameEnvironment",
        planner: Planner,
        actor: Actor,
        feedback_processor: FeedbackProcessor,
        memory: MemoryStore,
        kripke: KripkeModel,
        config: AgentConfig,
    ) -> None:
        self._env = env
        self._planner = planner
        self._actor = actor
        self._fp = feedback_processor
        self._memory = memory
        self._kripke = kripke
        self._cfg = config

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run_session(self) -> SessionResult:
        """
        Execute the full observe → plan → act loop until terminal or max_turns.
        """
        result = SessionResult(
            agent_id=self._cfg.agent_id,
            total_turns=0,
            terminal=False,
            final_reward=0.0,
        )

        for turn in range(self._cfg.max_turns):
            result.total_turns = turn

            # ── 1. Observe ───────────────────────────────────────────
            raw_obs = self._env.observe(self._cfg.agent_id)

            # ── 2. Feedback ──────────────────────────────────────────
            event = self._fp.process(raw_obs, turn)
            result.events.append(event)
            result.final_reward += event.reward

            self._log_event(event)

            # ── 3. Memory ────────────────────────────────────────────
            self._memory.add(MemoryEntry(
                turn=turn,
                kind=event.kind.value,
                source=event.source,
                content=event.content,
                metadata={"facts": event.facts, "reward": event.reward},
            ))

            # ── 4. Update Kripke ─────────────────────────────────────
            if event.facts:
                self._kripke = self._kripke.update_with_facts(event.facts)
            self._memory.snapshot_kripke(turn, self._kripke)

            # ── Terminal check ───────────────────────────────────────
            if event.terminal or self._env.is_terminal:
                result.terminal = True
                break

            # ── 5. Plan ──────────────────────────────────────────────
            action_specs = self._env.action_specs(self._cfg.agent_id)
            if not action_specs:
                log.debug("Turn %d: no valid actions, skipping.", turn)
                continue

            plan = self._planner.plan(
                kripke=self._kripke,
                memory=self._memory,
                goal=self._cfg.goal,
                agent_id=self._cfg.agent_id,
                action_specs=action_specs,
            )
            self._memory.add(MemoryEntry(
                turn=turn,
                kind="plan",
                source=self._cfg.agent_id,
                content=str(plan),
                metadata={"reasoning": plan.reasoning},
            ))

            # ── 6. Act ───────────────────────────────────────────────
            action = self._safe_act(plan, action_specs, turn, result)
            if action is None:
                continue

            result.actions.append(action)
            self._memory.add(MemoryEntry(
                turn=turn,
                kind="action",
                source=self._cfg.agent_id,
                content=str(action),
            ))

            self._log_action(turn, plan, action)

            # ── 7. Step env ──────────────────────────────────────────
            _ = self._env.step(self._cfg.agent_id, action)

        result.memory_snapshot = self._memory.to_dict()
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _safe_act(
        self,
        plan: Plan,
        action_specs: list[ActionSpec],
        turn: int,
        result: SessionResult,
    ) -> GameAction | None:
        """
        Attempt to produce a GameAction.  On ActionError, either replan
        (if configured) or log the illegal move and skip this turn.
        """
        try:
            return self._actor.act(plan, action_specs, self._cfg.agent_id)
        except ActionError as exc:
            log.warning("Turn %d: illegal action — %s", turn, exc)

            illegal_event = FeedbackEvent(
                kind=FeedbackKind.ILLEGAL_MOVE,
                turn=turn,
                source="orchestrator",
                content=str(exc),
            )
            result.events.append(illegal_event)
            self._memory.add(MemoryEntry(
                turn=turn,
                kind=FeedbackKind.ILLEGAL_MOVE.value,
                source="orchestrator",
                content=str(exc),
            ))

            if self._cfg.replan_on_illegal:
                try:
                    replan = self._planner.plan(
                        kripke=self._kripke,
                        memory=self._memory,
                        goal=self._cfg.goal,
                        agent_id=self._cfg.agent_id,
                        action_specs=action_specs,
                    )
                    return self._actor.act(replan, action_specs, self._cfg.agent_id)
                except ActionError:
                    log.error("Turn %d: replan also failed; skipping turn.", turn)

        return None

    def _log_event(self, event: FeedbackEvent) -> None:
        if self._cfg.verbose:
            print(f"  [feedback] {event}")

    def _log_action(self, turn: int, plan: Plan, action: GameAction) -> None:
        if self._cfg.verbose:
            print(f"  [turn {turn}] {action}")
            print(f"           intent: {plan.intent}")

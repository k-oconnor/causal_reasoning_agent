"""
causal_agent/acting.py

Translates a Plan into a validated GameAction ready for the environment.

Responsibility split
--------------------
Planning decides *what to do* (intent + action_type + parameters).
Acting decides *how to package it* for the specific environment format,
validates that the action is currently legal, and raises early if not.

GameAction is the canonical data object passed to GameEnvironment.step().
It is the only thing the environment needs to know about; it does not
import anything from planning or memory.

Validation
----------
Actor.act() checks that plan.action_type is legal and validates the payload
against the matching ActionSpec before emitting the action. If invalid, it
raises ActionError so Orchestration can catch it, log it as an ILLEGAL_MOVE
feedback event, and request a replan rather than submitting a bad move.

Post-processing hooks
---------------------
Override Actor and add entries to _post_processors to apply game-specific
transforms after validation (e.g. truncate message length, normalise
player name casing, redact private information from public speech).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from causal_agent.actions import ActionSpec, action_spec_by_type, coerce_action_specs
from causal_agent.planning import Plan


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ActionError(ValueError):
    """Raised when the planner proposes an action that is not currently legal."""


# ---------------------------------------------------------------------------
# GameAction
# ---------------------------------------------------------------------------

@dataclass
class GameAction:
    """
    The canonical action object submitted to the environment.

    Attributes
    ----------
    action_type : the action category string (e.g. "speak", "vote", "kill").
    payload     : action-specific data (e.g. {"message": "..."} for speak).
    agent_id    : who is performing the action.
    """
    action_type: str
    payload: dict[str, Any]
    agent_id: str

    def __str__(self) -> str:
        return f"GameAction({self.agent_id} → {self.action_type}: {self.payload})"


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------

PostProcessor = Callable[[GameAction], GameAction]


class Actor:
    """
    Converts a Plan into a validated GameAction.

    Parameters
    ----------
    post_processors : optional list of callables that transform a GameAction
                      after validation (e.g. message truncation).
    """

    def __init__(
        self, post_processors: list[PostProcessor] | None = None
    ) -> None:
        self._post_processors: list[PostProcessor] = post_processors or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def act(
        self,
        plan: Plan,
        valid_actions: Sequence[ActionSpec | str],
        agent_id: str,
    ) -> GameAction:
        """
        Parameters
        ----------
        plan         : Plan produced by the Planner.
        valid_actions: legal action specs or legacy action names for this turn.
        agent_id     : identifier of the acting agent.

        Returns
        -------
        GameAction ready for env.step().

        Raises
        ------
        ActionError if action type or payload validation fails.
        """
        payload = self._validate(plan, valid_actions)

        action = GameAction(
            action_type=plan.action_type,
            payload=payload,
            agent_id=agent_id,
        )

        for processor in self._post_processors:
            action = processor(action)

        return action

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate(
        self,
        plan: Plan,
        valid_actions: Sequence[ActionSpec | str],
    ) -> dict[str, Any]:
        specs = coerce_action_specs(valid_actions)
        if not specs:
            raise ActionError(
                f"No valid actions available this turn; "
                f"plan proposed {plan.action_type!r}."
            )
        by_type = action_spec_by_type(specs)
        if plan.action_type not in by_type:
            raise ActionError(
                f"Planned action {plan.action_type!r} is not in "
                f"valid actions {list(by_type)}.  Replan required."
            )
        try:
            return by_type[plan.action_type].validate_payload(plan.parameters)
        except ValueError as exc:
            raise ActionError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Built-in post-processors (attach as needed)
    # ------------------------------------------------------------------

    @staticmethod
    def truncate_message(max_chars: int = 300) -> PostProcessor:
        """
        Factory: return a post-processor that caps message length.
        Usage: Actor(post_processors=[Actor.truncate_message(200)])
        """
        def _truncate(action: GameAction) -> GameAction:
            if "message" in action.payload:
                msg = action.payload["message"]
                if len(msg) > max_chars:
                    action.payload["message"] = msg[:max_chars].rstrip() + "…"
            return action
        return _truncate

    @staticmethod
    def normalise_target_case() -> PostProcessor:
        """Factory: title-case the 'target' key so player names match env expectations."""
        def _norm(action: GameAction) -> GameAction:
            if "target" in action.payload:
                action.payload["target"] = str(action.payload["target"]).title()
            return action
        return _norm

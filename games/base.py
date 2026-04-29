"""
games/base.py

Abstract base class for all game environments.

Every game the framework supports must implement GameEnvironment.
The only causal_agent type it needs to know about is GameAction —
that is the sole coupling between the games layer and the agent layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from causal_agent.actions import ActionSpec

if TYPE_CHECKING:
    from causal_agent.acting import GameAction
    from causal_agent.kripke import KripkeModel


class GameEnvironment(ABC):
    """
    Minimal interface a game environment must satisfy.

    Methods
    -------
    observe(agent_id)
        Return a raw dict describing what `agent_id` can perceive this turn.
        The dict is passed to FeedbackProcessor.process(); its schema is
        game-specific but should include at minimum "kind", "source", "content".

    step(agent_id, action)
        Apply `action` for `agent_id` and advance the game state.
        Return a raw feedback dict (same schema as observe).

    action_specs(agent_id)
        Return the legal ActionSpec objects for `agent_id` right now. This is
        the canonical contract used by planning and acting.

    valid_actions(agent_id)
        Compatibility helper returning the legal action_type strings.

    is_terminal
        True when the game has reached an end condition.

    initial_kripke(agent_id)
        Construct the KripkeModel for `agent_id` at game start, encoding
        what that agent initially knows and doesn't know.
    """

    @abstractmethod
    def observe(self, agent_id: str) -> dict:
        """Current percept for agent_id."""
        ...

    @abstractmethod
    def step(self, agent_id: str, action: "GameAction") -> dict:
        """Apply action and return raw feedback dict."""
        ...

    @abstractmethod
    def action_specs(self, agent_id: str) -> list[ActionSpec]:
        """Legal structured actions for agent_id this turn."""
        ...

    def valid_actions(self, agent_id: str) -> list[str]:
        """Legal action type names for legacy callers."""
        return [spec.action_type for spec in self.action_specs(agent_id)]

    @property
    @abstractmethod
    def is_terminal(self) -> bool:
        """True when the game is over."""
        ...

    def initial_kripke(self, agent_id: str) -> "KripkeModel":
        """
        Build the agent's initial epistemic model.

        Games with hidden information can override this. Fully observable
        games get a trivial one-world model by default, making the Kripke
        module optional for puzzles such as 2048.
        """
        from causal_agent.kripke import KripkeModel, World

        return KripkeModel(worlds=[World.from_dict("actual", {})])

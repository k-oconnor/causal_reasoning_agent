"""
games/mastermind/env.py

Mastermind environment for exercising structured parameterized actions.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any, Sequence

from pydantic import BaseModel, Field, create_model

from causal_agent.actions import ActionSpec, _ForbidExtraConfig, string_enum
from causal_agent.acting import GameAction
from games.base import GameEnvironment


class MastermindEnv(GameEnvironment):
    """
    Minimal Mastermind environment.

    The agent repeatedly submits ``guess`` actions. Each guess is an exact
    length list of symbols from the configured palette.
    """

    def __init__(
        self,
        colors: Sequence[str] = ("red", "green", "blue", "yellow", "purple", "orange"),
        code_length: int = 4,
        max_attempts: int = 10,
        seed: int | None = None,
        secret: Sequence[str] | None = None,
        agent_id: str = "Agent",
    ) -> None:
        if not colors:
            raise ValueError("Mastermind requires at least one color.")
        if code_length < 1:
            raise ValueError("Mastermind code_length must be positive.")
        if max_attempts < 1:
            raise ValueError("Mastermind max_attempts must be positive.")

        self._colors = tuple(str(color) for color in colors)
        self._code_length = code_length
        self._max_attempts = max_attempts
        self._rng = random.Random(seed)
        self._agent_id = agent_id
        self._history: list[dict[str, Any]] = []
        self._solved = False
        self._terminal = False

        if secret is None:
            self._secret = [self._rng.choice(self._colors) for _ in range(code_length)]
        else:
            self._secret = [str(color) for color in secret]
            self._validate_code(self._secret)

    def observe(self, agent_id: str) -> dict:
        attempts_remaining = self._max_attempts - len(self._history)
        return {
            "kind": "terminal" if self._terminal else "observation",
            "source": "env",
            "content": (
                f"Mastermind attempts_remaining={attempts_remaining} "
                f"history={self._history}"
            ),
            "colors": list(self._colors),
            "code_length": self._code_length,
            "attempts_remaining": attempts_remaining,
            "history": list(self._history),
            "facts": {
                "attempts_remaining": attempts_remaining,
                "solved": self._solved,
            },
            "reward": self._terminal_reward() if self._terminal else 0.0,
            "terminal": self._terminal,
        }

    def step(self, agent_id: str, action: GameAction) -> dict:
        if self._terminal:
            return {
                "kind": "terminal",
                "source": "env",
                "content": "Game is already over.",
                "facts": {},
                "terminal": True,
                "reward": self._terminal_reward(),
            }
        if action.action_type != "guess":
            return self._illegal(f"Unknown action: {action.action_type}")

        code = action.payload.get("code", [])
        try:
            guess = [str(symbol) for symbol in code]
            self._validate_code(guess)
        except ValueError as exc:
            return self._illegal(str(exc))

        exact, partial = self._score_guess(guess)
        self._solved = exact == self._code_length
        record = {
            "guess": guess,
            "exact": exact,
            "partial": partial,
        }
        self._history.append(record)
        self._terminal = self._solved or len(self._history) >= self._max_attempts
        attempts_remaining = self._max_attempts - len(self._history)

        return {
            "kind": "terminal" if self._terminal else "observation",
            "source": "env",
            "content": (
                f"Guess {guess}: exact={exact}, partial={partial}, "
                f"attempts_remaining={attempts_remaining}."
            ),
            "history": list(self._history),
            "attempts_remaining": attempts_remaining,
            "facts": {
                "last_guess": guess,
                "last_exact": exact,
                "last_partial": partial,
                "attempts_remaining": attempts_remaining,
                "solved": self._solved,
            },
            "reward": self._terminal_reward() if self._terminal else 0.0,
            "terminal": self._terminal,
        }

    def action_specs(self, agent_id: str) -> list[ActionSpec]:
        if self._terminal:
            return []
        example = list(self._colors[: self._code_length])
        if len(example) < self._code_length:
            example.extend([self._colors[0]] * (self._code_length - len(example)))
        return [
            ActionSpec(
                action_type="guess",
                description=(
                    f"Guess the hidden code as exactly {self._code_length} symbols "
                    f"from the allowed color list."
                ),
                payload_model=_guess_payload_model(self._colors, self._code_length),
                examples=[{"code": example}],
            )
        ]

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def secret(self) -> list[str]:
        return list(self._secret)

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def _illegal(self, content: str) -> dict:
        return {
            "kind": "illegal_move",
            "source": "env",
            "content": content,
            "facts": {},
            "terminal": self._terminal,
            "reward": 0.0,
        }

    def _validate_code(self, code: Sequence[str]) -> None:
        if len(code) != self._code_length:
            raise ValueError(f"Code must contain exactly {self._code_length} symbols.")
        invalid = [symbol for symbol in code if symbol not in self._colors]
        if invalid:
            raise ValueError(f"Invalid Mastermind symbol(s): {invalid}.")

    def _score_guess(self, guess: list[str]) -> tuple[int, int]:
        exact = sum(g == s for g, s in zip(guess, self._secret))
        remaining_guess = [
            g for g, s in zip(guess, self._secret) if g != s
        ]
        remaining_secret = [
            s for g, s in zip(guess, self._secret) if g != s
        ]
        guess_counts = Counter(remaining_guess)
        secret_counts = Counter(remaining_secret)
        partial = sum(
            min(count, secret_counts.get(symbol, 0))
            for symbol, count in guess_counts.items()
        )
        return exact, partial

    def _terminal_reward(self) -> float:
        if self._solved:
            return 1.0
        if self._terminal:
            return -1.0
        return 0.0

    def __repr__(self) -> str:
        return (
            f"MastermindEnv(colors={list(self._colors)}, "
            f"code_length={self._code_length}, attempts={len(self._history)})"
        )


def _guess_payload_model(colors: Sequence[str], code_length: int) -> type[BaseModel]:
    symbol_type = string_enum("MastermindSymbol", colors)
    return create_model(
        "MastermindGuessPayload",
        __config__=_ForbidExtraConfig,
        code=(
            list[symbol_type],
            Field(
                ...,
                min_items=code_length,
                max_items=code_length,
                description=(
                    f"Exactly {code_length} symbols, each one of: {', '.join(colors)}."
                ),
            ),
        ),
    )

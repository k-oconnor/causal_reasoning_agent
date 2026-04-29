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
from causal_agent.prompts import MASTERMIND_SYSTEM
from causal_agent.tools import ToolRegistry
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
        duplicates_allowed: bool = True,
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
        self._duplicates_allowed = duplicates_allowed
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
        facts = {
            "attempts_remaining": attempts_remaining,
            "solved": self._solved,
        }
        facts.update(self._candidate_constraint_fact())
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
            "facts": facts,
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

        facts = {
            "last_guess": guess,
            "last_exact": exact,
            "last_partial": partial,
            "attempts_remaining": attempts_remaining,
            "solved": self._solved,
        }
        facts.update(self._candidate_constraint_fact())

        return {
            "kind": "terminal" if self._terminal else "observation",
            "source": "env",
            "content": (
                f"Guess {guess}: exact={exact}, partial={partial}, "
                f"attempts_remaining={attempts_remaining}."
            ),
            "history": list(self._history),
            "attempts_remaining": attempts_remaining,
            "facts": facts,
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
                    f"from the allowed color list. "
                    + (
                        "Repeated symbols are allowed."
                        if self._duplicates_allowed
                        else "Do not repeat symbols."
                    )
                ),
                payload_model=_guess_payload_model(self._colors, self._code_length),
                examples=[{"code": example}],
            )
        ]

    def system_prompt(self) -> str:
        return MASTERMIND_SYSTEM

    def tools(self, agent_id: str) -> ToolRegistry:
        from causal_agent.mastermind_tools import MastermindToolset

        registry = ToolRegistry().enable_kripke_tools()
        MastermindToolset(self).register_all(registry)
        return registry

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def colors(self) -> list[str]:
        return list(self._colors)

    @property
    def code_length(self) -> int:
        return self._code_length

    @property
    def duplicates_allowed(self) -> bool:
        return self._duplicates_allowed

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
        if not self._duplicates_allowed and len(set(code)) != len(code):
            raise ValueError("Duplicate Mastermind symbols are not allowed in this game.")

    def _score_guess(self, guess: list[str]) -> tuple[int, int]:
        return _score_guess_against(guess, self._secret)

    def _candidate_constraint_fact(self) -> dict[str, dict[str, list[list[str]]]]:
        if not self._history:
            return {}
        return {
            "secret_code": {
                "$in": [list(code) for code in self._remaining_candidates()]
            }
        }

    def _remaining_candidates(self) -> list[tuple[str, ...]]:
        from causal_agent.mastermind_tools import generate_all_codes

        candidates = generate_all_codes(
            self._colors,
            self._code_length,
            self._duplicates_allowed,
        )
        for record in self._history:
            guess = tuple(record["guess"])
            feedback = (int(record["exact"]), int(record["partial"]))
            candidates = [
                code for code in candidates
                if _score_guess_against(guess, code) == feedback
            ]
        return candidates

    def initial_kripke(self, agent_id: str):
        from causal_agent.kripke import KripkeModel, World
        from causal_agent.mastermind_tools import generate_all_codes

        worlds = []
        for index, code in enumerate(
            generate_all_codes(self._colors, self._code_length, self._duplicates_allowed)
        ):
            facts: dict[str, Any] = {"secret_code": tuple(code)}
            for pos, symbol in enumerate(code):
                facts[f"code_{pos}"] = symbol
            worlds.append(World.from_dict(f"code_{index}", facts))
        return KripkeModel(worlds=worlds)

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


def _score_guess_against(
    guess: Sequence[str],
    code: Sequence[str],
) -> tuple[int, int]:
    exact = sum(g == s for g, s in zip(guess, code))
    remaining_guess = [
        g for g, s in zip(guess, code) if g != s
    ]
    remaining_secret = [
        s for g, s in zip(guess, code) if g != s
    ]
    guess_counts = Counter(remaining_guess)
    secret_counts = Counter(remaining_secret)
    partial = sum(
        min(count, secret_counts.get(symbol, 0))
        for symbol, count in guess_counts.items()
    )
    return exact, partial


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

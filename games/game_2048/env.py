"""
games/game_2048/env.py

Small deterministic 2048 environment for exercising enum-only actions.
"""

from __future__ import annotations

import random

from pydantic import BaseModel, Field, create_model

from causal_agent.actions import ActionSpec, _ForbidExtraConfig, string_enum
from causal_agent.acting import GameAction
from games.base import GameEnvironment


Direction = str
_DIRECTIONS: tuple[Direction, ...] = ("up", "down", "left", "right")


class Game2048Env(GameEnvironment):
    """
    Minimal 2048 environment.

    The legal action surface is one action, ``slide``, whose payload contains
    a currently legal direction.
    """

    def __init__(
        self,
        size: int = 4,
        seed: int | None = None,
        agent_id: str = "Agent",
    ) -> None:
        if size < 2:
            raise ValueError("2048 board size must be at least 2.")
        self._size = size
        self._rng = random.Random(seed)
        self._agent_id = agent_id
        self._board: list[list[int]] = [[0 for _ in range(size)] for _ in range(size)]
        self._score = 0
        self._turn = 0
        self._terminal = False
        self._add_tile()
        self._add_tile()

    def observe(self, agent_id: str) -> dict:
        legal = self._legal_directions()
        return {
            "kind": "observation" if not self._terminal else "terminal",
            "source": "env",
            "content": (
                f"2048 turn={self._turn} score={self._score} "
                f"legal_directions={legal}"
            ),
            "board": self.board,
            "score": self._score,
            "legal_directions": legal,
            "facts": {
                "score": self._score,
                "max_tile": max(max(row) for row in self._board),
            },
            "terminal": self._terminal,
            "reward": 0.0,
        }

    def step(self, agent_id: str, action: GameAction) -> dict:
        if self._terminal:
            return {
                "kind": "terminal",
                "source": "env",
                "content": "Game is already over.",
                "facts": {},
                "terminal": True,
            }
        if action.action_type != "slide":
            return self._illegal(f"Unknown action: {action.action_type}")

        direction = str(action.payload.get("direction", ""))
        legal = self._legal_directions()
        if direction not in legal:
            return self._illegal(f"Direction {direction!r} is not currently legal.")

        new_board, gained = self._move(self._board, direction)
        self._board = new_board
        self._score += gained
        self._turn += 1
        self._add_tile()
        self._terminal = not self._legal_directions()

        return {
            "kind": "observation" if not self._terminal else "terminal",
            "source": "env",
            "content": f"Slid {direction}; gained {gained}; score={self._score}.",
            "board": self.board,
            "score": self._score,
            "legal_directions": self._legal_directions(),
            "facts": {
                "last_direction": direction,
                "score": self._score,
                "max_tile": max(max(row) for row in self._board),
            },
            "reward": float(gained),
            "terminal": self._terminal,
        }

    def action_specs(self, agent_id: str) -> list[ActionSpec]:
        legal = self._legal_directions()
        if self._terminal or not legal:
            return []
        return [
            ActionSpec(
                action_type="slide",
                description="Slide all tiles in one legal direction.",
                payload_model=_direction_payload_model(legal),
                examples=[{"direction": legal[0]}],
            )
        ]

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def board(self) -> list[list[int]]:
        return [row[:] for row in self._board]

    @property
    def score(self) -> int:
        return self._score

    def _illegal(self, content: str) -> dict:
        return {
            "kind": "illegal_move",
            "source": "env",
            "content": content,
            "facts": {},
            "terminal": self._terminal,
            "reward": 0.0,
        }

    def _add_tile(self) -> None:
        empties = [
            (r, c)
            for r, row in enumerate(self._board)
            for c, value in enumerate(row)
            if value == 0
        ]
        if not empties:
            return
        r, c = self._rng.choice(empties)
        self._board[r][c] = 4 if self._rng.random() < 0.1 else 2

    def _legal_directions(self) -> list[Direction]:
        legal: list[Direction] = []
        for direction in _DIRECTIONS:
            moved, _ = self._move(self._board, direction)
            if moved != self._board:
                legal.append(direction)
        return legal

    def _move(
        self,
        board: list[list[int]],
        direction: Direction,
    ) -> tuple[list[list[int]], int]:
        if direction == "left":
            return self._move_left(board)
        if direction == "right":
            reversed_board = [list(reversed(row)) for row in board]
            moved, gained = self._move_left(reversed_board)
            return [list(reversed(row)) for row in moved], gained
        if direction == "up":
            transposed = self._transpose(board)
            moved, gained = self._move_left(transposed)
            return self._transpose(moved), gained
        if direction == "down":
            transposed = self._transpose(board)
            reversed_board = [list(reversed(row)) for row in transposed]
            moved, gained = self._move_left(reversed_board)
            restored = [list(reversed(row)) for row in moved]
            return self._transpose(restored), gained
        raise ValueError(f"Unknown direction: {direction}")

    def _move_left(self, board: list[list[int]]) -> tuple[list[list[int]], int]:
        moved: list[list[int]] = []
        gained = 0
        for row in board:
            merged, row_gain = self._merge_row(row)
            moved.append(merged)
            gained += row_gain
        return moved, gained

    def _merge_row(self, row: list[int]) -> tuple[list[int], int]:
        values = [value for value in row if value]
        merged: list[int] = []
        gained = 0
        i = 0
        while i < len(values):
            if i + 1 < len(values) and values[i] == values[i + 1]:
                new_value = values[i] * 2
                merged.append(new_value)
                gained += new_value
                i += 2
            else:
                merged.append(values[i])
                i += 1
        merged.extend([0] * (self._size - len(merged)))
        return merged, gained

    def _transpose(self, board: list[list[int]]) -> list[list[int]]:
        return [list(row) for row in zip(*board)]

    def __repr__(self) -> str:
        return f"Game2048Env(size={self._size}, score={self._score}, terminal={self._terminal})"


def _direction_payload_model(directions: list[Direction]) -> type[BaseModel]:
    direction_type = string_enum("SlideDirection", directions)
    return create_model(
        "SlidePayload",
        __config__=_ForbidExtraConfig,
        direction=(
            direction_type,
            Field(..., description=f"One of: {', '.join(directions)}."),
        ),
    )

"""Toolset for evaluating 2048 moves during planning."""

from __future__ import annotations

import math
from typing import Any, Callable, TYPE_CHECKING

from causal_agent.tools import ToolDefinition, ToolRegistry

if TYPE_CHECKING:
    from games.game_2048.env import Game2048Env


_DIRECTIONS = ("up", "down", "left", "right")


class Game2048Toolset:
    """Register 2048 simulation, scoring, and shallow expectimax tools."""

    def __init__(self, env: "Game2048Env") -> None:
        self._env = env

    def register_all(self, registry: ToolRegistry) -> None:
        for defn, fn in self._all_tools():
            registry.register(defn, fn)

    def _all_tools(self) -> list[tuple[ToolDefinition, Callable]]:
        return [
            (self._defn_simulate_move(), self._simulate_move),
            (self._defn_score_board(), self._score_board_tool),
            (self._defn_count_empty_cells(), self._count_empty_cells),
            (self._defn_expectimax(), self._expectimax_tool),
        ]

    def _defn_simulate_move(self) -> ToolDefinition:
        return ToolDefinition(
            name="game2048_simulate_move",
            description=(
                "Simulate sliding the current 2048 board in one direction without "
                "adding the random next tile. Use this to compare immediate merges, "
                "empty cells, and max tile after candidate moves."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": list(_DIRECTIONS),
                        "description": "Direction to slide: up, down, left, or right.",
                    }
                },
                "required": ["direction"],
            },
        )

    def _simulate_move(self, direction: str) -> dict[str, Any]:
        board = self._env.board
        legal = self._legal_directions(board)
        if direction not in legal:
            return {
                "legal": False,
                "direction": direction,
                "legal_directions": legal,
                "reason": "Direction does not move any tile on the current board.",
            }

        moved, gained = self._env._move(board, direction)
        return {
            "legal": True,
            "direction": direction,
            "board": moved,
            "gained": gained,
            "empty_after": _count_empty(moved),
            "max_tile_after": _max_tile(moved),
            "merges": _merge_count(board, moved),
            "heuristic": self._score_board(moved)["score"],
        }

    def _defn_score_board(self) -> ToolDefinition:
        return ToolDefinition(
            name="game2048_score_board",
            description=(
                "Score a 2048 board using empty cells, monotonicity, smoothness, "
                "corner anchoring, and merge potential. Higher is better. If no "
                "board is provided, scores the current board."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "board": {
                        "type": "array",
                        "description": "Optional square 2048 board to score.",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    }
                },
            },
        )

    def _score_board_tool(self, board: list[list[int]] | None = None) -> dict[str, Any]:
        return self._score_board(board or self._env.board)

    def _score_board(self, board: list[list[int]]) -> dict[str, Any]:
        board = _normalise_board(board)
        empty = _count_empty(board)
        highest = _max_tile(board)
        corner_bonus = highest if _max_in_corner(board) else 0
        monotonicity = _monotonicity(board)
        smoothness = _smoothness(board)
        merge_potential = _merge_potential(board)

        score = (
            empty * 270.0
            + corner_bonus * 3.0
            + monotonicity * 80.0
            + smoothness * 18.0
            + merge_potential * 1.2
        )
        return {
            "score": round(score, 3),
            "empty_cells": empty,
            "max_tile": highest,
            "max_tile_in_corner": bool(corner_bonus),
            "monotonicity": round(monotonicity, 3),
            "smoothness": round(smoothness, 3),
            "merge_potential": merge_potential,
        }

    def _defn_count_empty_cells(self) -> ToolDefinition:
        return ToolDefinition(
            name="game2048_count_empty_cells",
            description="Count empty cells on the current 2048 board.",
            parameters={"type": "object", "properties": {}},
        )

    def _count_empty_cells(self) -> int:
        return _count_empty(self._env.board)

    def _defn_expectimax(self) -> ToolDefinition:
        return ToolDefinition(
            name="game2048_expectimax",
            description=(
                "Run a shallow expectimax search over legal 2048 moves and random "
                "tile spawns. Returns the best direction and per-direction scores."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "depth": {
                        "type": "integer",
                        "description": "Search depth from 1 to 4. Defaults to 3.",
                    }
                },
            },
        )

    def _expectimax_tool(self, depth: int = 3) -> dict[str, Any]:
        depth = max(1, min(int(depth), 4))
        board = self._env.board
        legal = self._legal_directions(board)
        if not legal:
            return {"direction": None, "scores": {}, "reason": "No legal moves."}

        scores = {
            direction: round(
                self._expectimax_after_move(board, direction, depth),
                3,
            )
            for direction in legal
        }
        best = max(scores, key=scores.get)
        return {"direction": best, "scores": scores, "depth": depth}

    def _expectimax_after_move(
        self,
        board: list[list[int]],
        direction: str,
        depth: int,
    ) -> float:
        moved, gained = self._env._move(board, direction)
        if moved == board:
            return float("-inf")
        return gained + self._chance_value(moved, depth - 1)

    def _chance_value(self, board: list[list[int]], depth: int) -> float:
        if depth <= 0:
            return float(self._score_board(board)["score"])

        empties = [
            (r, c)
            for r, row in enumerate(board)
            for c, value in enumerate(row)
            if value == 0
        ]
        if not empties:
            return self._max_move_value(board, depth)

        total = 0.0
        for r, c in empties:
            for tile, probability in ((2, 0.9), (4, 0.1)):
                spawned = [row[:] for row in board]
                spawned[r][c] = tile
                total += probability * self._max_move_value(spawned, depth)
        return total / len(empties)

    def _max_move_value(self, board: list[list[int]], depth: int) -> float:
        legal = self._legal_directions(board)
        if not legal:
            return float(self._score_board(board)["score"])
        return max(
            self._expectimax_after_move(board, direction, depth)
            for direction in legal
        )

    def _legal_directions(self, board: list[list[int]]) -> list[str]:
        return [
            direction
            for direction in _DIRECTIONS
            if self._env._move(board, direction)[0] != board
        ]


def _normalise_board(board: list[list[int]]) -> list[list[int]]:
    if not board or not all(isinstance(row, list) and row for row in board):
        raise ValueError("board must be a non-empty rectangular list of rows")
    width = len(board[0])
    normalised = [[int(value) for value in row] for row in board]
    if any(len(row) != width for row in normalised):
        raise ValueError("board rows must all have the same length")
    return normalised


def _count_empty(board: list[list[int]]) -> int:
    return sum(1 for row in board for value in row if value == 0)


def _max_tile(board: list[list[int]]) -> int:
    return max((value for row in board for value in row), default=0)


def _max_in_corner(board: list[list[int]]) -> bool:
    highest = _max_tile(board)
    if highest == 0:
        return False
    corners = {
        board[0][0],
        board[0][-1],
        board[-1][0],
        board[-1][-1],
    }
    return highest in corners


def _merge_count(before: list[list[int]], after: list[list[int]]) -> int:
    before_tiles = sum(1 for row in before for value in row if value)
    after_tiles = sum(1 for row in after for value in row if value)
    return max(0, before_tiles - after_tiles)


def _merge_potential(board: list[list[int]]) -> int:
    total = 0
    for row in board:
        total += sum(value for value, nxt in zip(row, row[1:]) if value and value == nxt)
    for col in zip(*board):
        total += sum(value for value, nxt in zip(col, col[1:]) if value and value == nxt)
    return total


def _smoothness(board: list[list[int]]) -> float:
    penalty = 0.0
    for row in board:
        penalty += _line_smoothness(row)
    for col in zip(*board):
        penalty += _line_smoothness(list(col))
    return -penalty


def _line_smoothness(line: list[int]) -> float:
    penalty = 0.0
    for left, right in zip(line, line[1:]):
        if left and right:
            penalty += abs(math.log2(left) - math.log2(right))
    return penalty


def _monotonicity(board: list[list[int]]) -> float:
    rows = sum(_line_monotonicity(row) for row in board)
    cols = sum(_line_monotonicity(list(col)) for col in zip(*board))
    return rows + cols


def _line_monotonicity(line: list[int]) -> float:
    values = [math.log2(value) if value else 0.0 for value in line]
    increasing_penalty = 0.0
    decreasing_penalty = 0.0
    for left, right in zip(values, values[1:]):
        if left > right:
            increasing_penalty += left - right
        else:
            decreasing_penalty += right - left
    return -min(increasing_penalty, decreasing_penalty)

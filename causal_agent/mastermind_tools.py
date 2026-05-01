"""Toolset for Mastermind candidate filtering and information scoring."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from itertools import permutations, product
from typing import Any, Callable, Sequence, TYPE_CHECKING

from causal_agent.tools import ToolDefinition, ToolRegistry

if TYPE_CHECKING:
    from games.mastermind.env import MastermindEnv


class MastermindToolset:
    """Register Mastermind candidate-set and information tools."""

    def __init__(self, env: "MastermindEnv") -> None:
        self._env = env

    def register_all(self, registry: ToolRegistry) -> None:
        for defn, fn in self._all_tools():
            registry.register(defn, fn)

    def _all_tools(self) -> list[tuple[ToolDefinition, Callable]]:
        return [
            (self._defn_candidate_count(), self._candidate_count),
            (self._defn_enumerate_candidates(), self._enumerate_candidates),
            (self._defn_filter_candidates(), self._filter_candidates),
            (self._defn_expected_information(), self._expected_information),
        ]

    def _defn_candidate_count(self) -> ToolDefinition:
        return ToolDefinition(
            name="mastermind_candidate_count",
            description="Count codes still consistent with all Mastermind feedback so far.",
            parameters={"type": "object", "properties": {}},
        )

    def _candidate_count(self) -> int:
        return len(self._candidates())

    def _defn_enumerate_candidates(self) -> ToolDefinition:
        return ToolDefinition(
            name="mastermind_enumerate_candidates",
            description=(
                "List remaining candidate codes consistent with all feedback. "
                "Use this once the candidate set is small enough to inspect."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum candidates to return. Defaults to 20.",
                    }
                },
            },
        )

    def _enumerate_candidates(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, int(limit))
        candidates = self._candidates()
        shown = candidates[:limit]
        return {
            "count": len(candidates),
            "candidates": [list(code) for code in shown],
            "truncated": len(candidates) > limit,
        }

    def _defn_filter_candidates(self) -> ToolDefinition:
        return ToolDefinition(
            name="mastermind_filter_candidates",
            description=(
                "Counterfactually apply feedback for a proposed guess and return "
                "how many current candidates would remain."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "guess": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Candidate guess code.",
                    },
                    "exact": {
                        "type": "integer",
                        "description": "Hypothetical exact-position matches.",
                    },
                    "partial": {
                        "type": "integer",
                        "description": "Hypothetical color-only matches.",
                    },
                },
                "required": ["guess", "exact", "partial"],
            },
        )

    def _filter_candidates(
        self,
        guess: Sequence[str],
        exact: int,
        partial: int,
    ) -> dict[str, Any]:
        guess_tuple = self._normalise_guess(guess)
        feedback = (int(exact), int(partial))
        candidates = self._candidates()
        survivors = [
            code for code in candidates
            if score_guess(guess_tuple, code) == feedback
        ]
        return {
            "guess": list(guess_tuple),
            "feedback": {"exact": feedback[0], "partial": feedback[1]},
            "remaining": len(survivors),
            "current_candidates": len(candidates),
            "examples": [list(code) for code in survivors[:20]],
        }

    def _defn_expected_information(self) -> ToolDefinition:
        return ToolDefinition(
            name="mastermind_expected_information",
            description=(
                "Compute the expected information, in bits, for a proposed guess "
                "over the current candidate set. Higher entropy means the guess "
                "splits candidates more evenly."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "guess": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Candidate guess code.",
                    }
                },
                "required": ["guess"],
            },
        )

    def _expected_information(self, guess: Sequence[str]) -> dict[str, Any]:
        guess_tuple = self._normalise_guess(guess)
        candidates = self._candidates()
        if not candidates:
            return {
                "guess": list(guess_tuple),
                "candidate_count": 0,
                "expected_information_bits": 0.0,
                "expected_remaining": 0.0,
                "is_candidate": False,
            }

        partitions: dict[tuple[int, int], int] = defaultdict(int)
        for code in candidates:
            partitions[score_guess(guess_tuple, code)] += 1

        total = len(candidates)
        entropy = -sum(
            (count / total) * math.log2(count / total)
            for count in partitions.values()
        )
        expected_remaining = sum((count / total) * count for count in partitions.values())
        largest_bucket = max(partitions.values()) if partitions else 0
        sorted_partitions = sorted(
            partitions.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return {
            "guess": list(guess_tuple),
            "candidate_count": total,
            "expected_information_bits": round(entropy, 4),
            "expected_remaining": round(expected_remaining, 3),
            "largest_partition": largest_bucket,
            "is_candidate": guess_tuple in candidates,
            "top_partitions": [
                {"exact": exact, "partial": partial, "count": count}
                for (exact, partial), count in sorted_partitions[:10]
            ],
        }

    def _normalise_guess(self, guess: Sequence[str]) -> tuple[str, ...]:
        normalised = tuple(str(symbol) for symbol in guess)
        if len(normalised) != self._env.code_length:
            raise ValueError(f"Guess must contain exactly {self._env.code_length} symbols.")
        invalid = [symbol for symbol in normalised if symbol not in self._env.colors]
        if invalid:
            raise ValueError(f"Invalid Mastermind symbol(s): {invalid}.")
        if not self._env.duplicates_allowed and len(set(normalised)) != len(normalised):
            raise ValueError("Duplicate symbols are disabled for this game.")
        return normalised

    def _candidates(self) -> list[tuple[str, ...]]:
        candidates = generate_all_codes(
            self._env.colors,
            self._env.code_length,
            self._env.duplicates_allowed,
        )
        for record in self._env.history:
            guess = tuple(record["guess"])
            feedback = (int(record["exact"]), int(record["partial"]))
            candidates = [
                code for code in candidates
                if score_guess(guess, code) == feedback
            ]
        return candidates


def generate_all_codes(
    colors: Sequence[str],
    code_length: int,
    duplicates_allowed: bool,
) -> list[tuple[str, ...]]:
    if duplicates_allowed:
        return list(product(colors, repeat=code_length))
    return list(permutations(colors, code_length))


def score_guess(guess: Sequence[str], code: Sequence[str]) -> tuple[int, int]:
    exact = sum(g == c for g, c in zip(guess, code))
    remaining_guess = [g for g, c in zip(guess, code) if g != c]
    remaining_code = [c for g, c in zip(guess, code) if g != c]
    guess_counts = Counter(remaining_guess)
    code_counts = Counter(remaining_code)
    partial = sum(
        min(count, code_counts.get(color, 0))
        for color, count in guess_counts.items()
    )
    return exact, partial

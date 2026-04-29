"""
Evaluate or interactively play the local 2048 environment.

This follows the same practical shape as Orak's 2048 setup: log each board
state, chosen direction, score, max tile, and termination signal. It does not
require a graphical game process.

Usage:
    python -m evaluations.game_2048.eval --policy greedy --episodes 20
    python -m evaluations.game_2048.eval --policy random --episodes 20
    python -m evaluations.game_2048.eval --policy interactive --max-turns 200
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from causal_agent import (
    Actor,
    FeedbackProcessor,
    MemoryEntry,
    MemoryStore,
    Planner,
)
from causal_agent.acting import GameAction
from evaluations.common import (
    TraceLogger,
    add_llm_args,
    build_llm,
    dataclass_to_dict,
    write_summary,
)
from games.game_2048 import Game2048Env


DirectionPolicy = Callable[[Game2048Env, random.Random, int], str]


@dataclass
class EpisodeResult:
    episode: int
    seed: int
    policy: str
    score: int
    max_tile: int
    turns: int
    terminal: bool
    invalid_moves: int


def board_text(board: list[list[int]]) -> str:
    return "\n".join(" ".join(f"{value:4d}" for value in row) for row in board)


def max_tile(board: list[list[int]]) -> int:
    return max(max(row) for row in board)


def legal_directions(env: Game2048Env) -> list[str]:
    return list(env.observe("Agent")["legal_directions"])


def choose_cycle(env: Game2048Env, rng: random.Random, turn: int) -> str:
    # The action type is always "slide"; pick the direction from the current spec.
    directions = legal_directions(env)
    preferred = ("left", "up", "right", "down")[turn % 4]
    return preferred if preferred in directions else directions[0]


def choose_random(env: Game2048Env, rng: random.Random, turn: int) -> str:
    directions = legal_directions(env)
    return rng.choice(directions)


def choose_greedy(env: Game2048Env, rng: random.Random, turn: int) -> str:
    directions = legal_directions(env)
    best_direction = directions[0]
    best_value: tuple[int, int, int] | None = None

    for direction in directions:
        moved_board, gained = env._move(env.board, direction)
        empty_cells = sum(1 for row in moved_board for value in row if value == 0)
        highest = max_tile(moved_board)
        # Immediate merges first, then board flexibility, then current max tile.
        value = (gained, empty_cells, highest)
        if best_value is None or value > best_value:
            best_value = value
            best_direction = direction

    return best_direction


def choose_interactive(env: Game2048Env, rng: random.Random, turn: int) -> str:
    directions = legal_directions(env)
    print("\nCurrent board:")
    print(board_text(env.board))
    print(f"Score: {env.score} | Max tile: {max_tile(env.board)}")
    while True:
        choice = input(f"Move {directions}: ").strip().lower()
        aliases = {"w": "up", "a": "left", "s": "down", "d": "right"}
        choice = aliases.get(choice, choice)
        if choice in directions:
            return choice
        print("That move is not currently legal.")


POLICIES: dict[str, DirectionPolicy] = {
    "cycle": choose_cycle,
    "random": choose_random,
    "greedy": choose_greedy,
    "interactive": choose_interactive,
}

_MOCK_2048_RESPONSES = [
    '{"intent": "merge while preserving space", "action_type": "slide", '
    '"parameters": {"direction": "left"}, "public_rationale": "Move tiles toward an edge."}',
    '{"intent": "stack tiles upward", "action_type": "slide", '
    '"parameters": {"direction": "up"}, "public_rationale": "Keep the board compact."}',
    '{"intent": "seek immediate merges", "action_type": "slide", '
    '"parameters": {"direction": "right"}, "public_rationale": "Try the opposite merge lane."}',
    '{"intent": "rebalance columns", "action_type": "slide", '
    '"parameters": {"direction": "down"}, "public_rationale": "Open space for future tiles."}',
]


def run_episode(
    episode: int,
    seed: int,
    policy_name: str,
    max_turns: int,
    log_dir: Path | None,
    verbose: bool,
    llm: Any | None = None,
) -> EpisodeResult:
    rng = random.Random(seed)
    env = Game2048Env(seed=seed, agent_id="Agent")
    policy = POLICIES.get(policy_name)
    planner = Planner(llm, simulate_before_plan=False) if policy_name == "llm" else None
    actor = Actor()
    feedback_processor = FeedbackProcessor()
    memory = MemoryStore(max_short_term=80)
    kripke = env.initial_kripke("Agent")
    invalid_moves = 0

    trace_filename = f"episode_{episode:04d}_{policy_name}_seed_{seed}.jsonl"
    with TraceLogger(log_dir, trace_filename) as trace:
        turns = 0
        for turn in range(max_turns):
            obs = env.observe("Agent")
            if obs.get("terminal") or env.is_terminal:
                break

            plan = None
            if policy_name == "llm":
                event = feedback_processor.process(obs, turn)
                memory.add(MemoryEntry(
                    turn=turn,
                    kind=event.kind.value,
                    source=event.source,
                    content=event.content,
                    metadata={
                        "facts": event.facts,
                        "board": obs["board"],
                        "legal_directions": obs["legal_directions"],
                    },
                ))
                if event.facts:
                    kripke = kripke.update_with_facts(event.facts)
                memory.snapshot_kripke(turn, kripke)
                action_specs = env.action_specs("Agent")
                if planner is None:
                    raise RuntimeError("LLM policy was selected without a planner.")
                plan = planner.plan(
                    kripke=kripke,
                    memory=memory,
                    goal=(
                        "Play 2048 well: maximize score, preserve empty cells, "
                        "build larger tiles, and avoid terminal boards."
                    ),
                    agent_id="Agent",
                    action_specs=action_specs,
                )
                action = actor.act(plan, action_specs, "Agent")
                direction = str(action.payload["direction"])
            else:
                if policy is None:
                    raise ValueError(f"Unknown policy: {policy_name}")
                direction = policy(env, rng, turn)
                action = GameAction(
                    action_type="slide",
                    payload={"direction": direction},
                    agent_id="Agent",
                )
            feedback = env.step("Agent", action)
            turns = turn + 1
            if feedback.get("kind") == "illegal_move":
                invalid_moves += 1

            record = {
                "episode": episode,
                "turn": turn,
                "seed": seed,
                "policy": policy_name,
                "board_before": obs["board"],
                "legal_directions": obs["legal_directions"],
                "action": direction,
                "feedback": feedback["content"],
                "intent": plan.intent if plan else "",
                "rationale": plan.reasoning if plan else "",
                "board_after": env.board,
                "score": env.score,
                "max_tile": max_tile(env.board),
                "terminal": env.is_terminal,
            }
            trace.write(record)

            if verbose:
                print(
                    f"[ep={episode} t={turn}] action={direction} "
                    f"score={env.score} max={record['max_tile']}"
                )
                print(board_text(env.board))

            if env.is_terminal:
                break

        return EpisodeResult(
            episode=episode,
            seed=seed,
            policy=policy_name,
            score=env.score,
            max_tile=max_tile(env.board),
            turns=turns,
            terminal=env.is_terminal,
            invalid_moves=invalid_moves,
        )


def summarize(results: list[EpisodeResult]) -> dict:
    scores = [result.score for result in results]
    max_tiles = [result.max_tile for result in results]
    turns = [result.turns for result in results]
    return {
        "game": "2048",
        "episodes": len(results),
        "policy": results[0].policy if results else "",
        "mean_score": statistics.mean(scores) if scores else 0,
        "median_score": statistics.median(scores) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "mean_max_tile": statistics.mean(max_tiles) if max_tiles else 0,
        "best_max_tile": max(max_tiles) if max_tiles else 0,
        "mean_turns": statistics.mean(turns) if turns else 0,
        "terminal_episodes": sum(result.terminal for result in results),
        "invalid_moves": sum(result.invalid_moves for result in results),
    }


def run(args: argparse.Namespace) -> None:
    log_dir = Path(args.log_dir or f"logs/evaluations/2048/{args.policy}")
    llm = build_llm(args, _MOCK_2048_RESPONSES) if args.policy == "llm" else None
    results = [
        run_episode(
            episode=episode,
            seed=args.seed + episode,
            policy_name=args.policy,
            max_turns=args.max_turns,
            log_dir=log_dir,
            verbose=args.verbose or args.policy == "interactive",
            llm=llm,
        )
        for episode in range(args.episodes)
    ]

    print("\nEpisode results:")
    for result in results:
        print(json.dumps(dataclass_to_dict(result), sort_keys=True))

    summary = summarize(results)
    print("\nSummary:")
    print(json.dumps(summary, indent=2, sort_keys=True))

    if write_summary(log_dir, args.policy, summary) is not None:
        print(f"\nWrote logs to {log_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the local 2048 environment.")
    parser.add_argument("--policy", choices=sorted([*POLICIES, "llm"]), default="greedy")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--max-turns", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--verbose", action="store_true")
    add_llm_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())

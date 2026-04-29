"""
Evaluate or interactively play the local Mastermind environment.

This mirrors the agentic evaluation shape from flairNLP/mastermind: run many
hidden-code games, log every guess with exact/partial feedback, and summarize
solve rate plus number of guesses. The local runner also includes deterministic
candidate-filter and minimax baselines for comparison with LLM agents.

Usage:
    python -m evaluations.mastermind.eval --policy candidate --episodes 20
    python -m evaluations.mastermind.eval --policy knuth --episodes 20
    python -m evaluations.mastermind.eval --policy llm --model mock --episodes 5
    python -m evaluations.mastermind.eval --policy interactive --episodes 1
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import permutations, product
from pathlib import Path
from typing import Any, Callable, Sequence

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
from games.mastermind import MastermindEnv


FLAIR_COLORS = (
    "red",
    "blue",
    "green",
    "yellow",
    "orange",
    "purple",
    "pink",
    "brown",
    "black",
    "white",
)

Guess = list[str]
GuessPolicy = Callable[["MastermindEvalState", random.Random], Guess]


@dataclass
class MastermindEvalState:
    colors: list[str]
    code_length: int
    duplicates_allowed: bool
    history: list[dict[str, Any]]
    all_codes: list[tuple[str, ...]]


@dataclass
class EpisodeResult:
    episode: int
    seed: int
    policy: str
    solved: bool
    guesses: int
    exact: int
    partial: int
    invalid_moves: int
    secret: list[str]
    remaining_candidates: int


def score_guess(guess: Sequence[str], code: Sequence[str]) -> tuple[int, int]:
    exact = sum(g == c for g, c in zip(guess, code))
    remaining_guess = [g for g, c in zip(guess, code) if g != c]
    remaining_code = [c for g, c in zip(guess, code) if g != c]
    guess_counts = Counter(remaining_guess)
    code_counts = Counter(remaining_code)
    partial = sum(min(count, code_counts.get(color, 0)) for color, count in guess_counts.items())
    return exact, partial


def generate_all_codes(
    colors: Sequence[str],
    code_length: int,
    duplicates_allowed: bool,
) -> list[tuple[str, ...]]:
    if duplicates_allowed:
        return list(product(colors, repeat=code_length))
    return list(permutations(colors, code_length))


def consistent_candidates(state: MastermindEvalState) -> list[tuple[str, ...]]:
    candidates = state.all_codes
    for record in state.history:
        guess = tuple(record["guess"])
        feedback = (int(record["exact"]), int(record["partial"]))
        candidates = [
            code for code in candidates
            if score_guess(guess, code) == feedback
        ]
    return candidates


def choose_random(state: MastermindEvalState, rng: random.Random) -> Guess:
    if state.duplicates_allowed:
        return [rng.choice(state.colors) for _ in range(state.code_length)]
    return rng.sample(state.colors, k=state.code_length)


def choose_candidate(state: MastermindEvalState, rng: random.Random) -> Guess:
    guessed = {tuple(record["guess"]) for record in state.history}
    for candidate in consistent_candidates(state):
        if candidate not in guessed:
            return list(candidate)
    return choose_random(state, rng)


def choose_knuth(state: MastermindEvalState, rng: random.Random) -> Guess:
    remaining = consistent_candidates(state)
    if len(remaining) <= 1:
        return list(remaining[0]) if remaining else choose_random(state, rng)

    guessed = {tuple(record["guess"]) for record in state.history}
    best_guess = remaining[0]
    best_score: tuple[int, int, int] | None = None

    for possible_guess in state.all_codes:
        if possible_guess in guessed:
            continue

        partitions: dict[tuple[int, int], int] = defaultdict(int)
        for possible_secret in remaining:
            partitions[score_guess(possible_guess, possible_secret)] += 1

        worst_partition = max(partitions.values())
        in_remaining = 1 if possible_guess in remaining else 0
        # Minimize worst case; prefer guesses still possible as the answer.
        score = (-worst_partition, in_remaining, -state.all_codes.index(possible_guess))
        if best_score is None or score > best_score:
            best_score = score
            best_guess = possible_guess

    return list(best_guess)


def choose_interactive(state: MastermindEvalState, rng: random.Random) -> Guess:
    print("\nHistory:")
    if not state.history:
        print("(no guesses yet)")
    for record in state.history:
        print(
            f"guess={record['guess']} exact={record['exact']} "
            f"partial={record['partial']}"
        )
    print(f"Colors: {state.colors}")
    while True:
        raw = input(f"Guess {state.code_length} colors separated by spaces: ").strip()
        guess = [part.strip().lower() for part in raw.replace(",", " ").split() if part.strip()]
        if len(guess) != state.code_length:
            print(f"Need exactly {state.code_length} colors.")
            continue
        invalid = [color for color in guess if color not in state.colors]
        if invalid:
            print(f"Invalid colors: {invalid}")
            continue
        if not state.duplicates_allowed and len(set(guess)) != len(guess):
            print("Duplicates are disabled for this run.")
            continue
        return guess


POLICIES: dict[str, GuessPolicy] = {
    "candidate": choose_candidate,
    "interactive": choose_interactive,
    "knuth": choose_knuth,
    "random": choose_random,
}

_MOCK_MASTERMIND_RESPONSES = [
    '{"intent": "test common first colors", "action_type": "guess", '
    '"parameters": {"code": ["red", "blue", "green", "yellow"]}, '
    '"public_rationale": "Start with four distinct colors."}',
    '{"intent": "test remaining colors", "action_type": "guess", '
    '"parameters": {"code": ["orange", "purple", "pink", "brown"]}, '
    '"public_rationale": "Probe colors not used in the first guess."}',
    '{"intent": "try a mixed candidate", "action_type": "guess", '
    '"parameters": {"code": ["red", "orange", "blue", "purple"]}, '
    '"public_rationale": "Combine colors that may be present."}',
]


def build_secret(
    rng: random.Random,
    colors: Sequence[str],
    code_length: int,
    duplicates_allowed: bool,
) -> list[str]:
    if duplicates_allowed:
        return [rng.choice(colors) for _ in range(code_length)]
    return rng.sample(list(colors), k=code_length)


def run_episode(
    episode: int,
    seed: int,
    policy_name: str,
    colors: list[str],
    code_length: int,
    max_attempts: int,
    duplicates_allowed: bool,
    log_dir: Path | None,
    verbose: bool,
    llm: Any | None = None,
) -> EpisodeResult:
    rng = random.Random(seed)
    secret = build_secret(rng, colors, code_length, duplicates_allowed)
    env = MastermindEnv(
        colors=colors,
        code_length=code_length,
        max_attempts=max_attempts,
        secret=secret,
        agent_id="Agent",
    )
    all_codes = generate_all_codes(colors, code_length, duplicates_allowed)
    policy = POLICIES.get(policy_name)
    planner = Planner(llm, simulate_before_plan=False) if policy_name == "llm" else None
    actor = Actor()
    feedback_processor = FeedbackProcessor()
    memory = MemoryStore(max_short_term=80)
    kripke = env.initial_kripke("Agent")
    invalid_moves = 0

    trace_filename = f"episode_{episode:04d}_{policy_name}_seed_{seed}.jsonl"
    with TraceLogger(log_dir, trace_filename) as trace:
        final_exact = 0
        final_partial = 0
        for turn in range(max_attempts):
            obs = env.observe("Agent")
            if obs.get("terminal") or env.is_terminal:
                break

            state = MastermindEvalState(
                colors=colors,
                code_length=code_length,
                duplicates_allowed=duplicates_allowed,
                history=list(env.history),
                all_codes=all_codes,
            )
            before_remaining = len(consistent_candidates(state))
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
                        "history": obs["history"],
                        "colors": colors,
                        "code_length": code_length,
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
                        "Solve Mastermind: infer the hidden code from exact and "
                        "partial feedback while using as few guesses as possible."
                    ),
                    agent_id="Agent",
                    action_specs=action_specs,
                )
                action = actor.act(plan, action_specs, "Agent")
                guess = list(action.payload["code"])
            else:
                if policy is None:
                    raise ValueError(f"Unknown policy: {policy_name}")
                guess = policy(state, rng)
                action = GameAction(
                    action_type="guess",
                    payload={"code": guess},
                    agent_id="Agent",
                )

            feedback = env.step("Agent", action)
            if feedback.get("kind") == "illegal_move":
                invalid_moves += 1
            elif env.history:
                final_exact = int(env.history[-1]["exact"])
                final_partial = int(env.history[-1]["partial"])

            after_state = MastermindEvalState(
                colors=colors,
                code_length=code_length,
                duplicates_allowed=duplicates_allowed,
                history=list(env.history),
                all_codes=all_codes,
            )
            after_remaining = len(consistent_candidates(after_state))
            record = {
                "episode": episode,
                "turn": turn,
                "seed": seed,
                "policy": policy_name,
                "colors": colors,
                "code_length": code_length,
                "max_attempts": max_attempts,
                "duplicates_allowed": duplicates_allowed,
                "secret": secret,
                "guess": guess,
                "feedback": feedback["content"],
                "exact": final_exact,
                "partial": final_partial,
                "remaining_candidates_before": before_remaining,
                "remaining_candidates_after": after_remaining,
                "intent": plan.intent if plan else "",
                "rationale": plan.reasoning if plan else "",
                "solved": env.is_terminal and bool(feedback.get("reward", 0.0) > 0),
                "terminal": env.is_terminal,
            }
            trace.write(record)

            if verbose:
                print(
                    f"[ep={episode} t={turn}] guess={guess} exact={final_exact} "
                    f"partial={final_partial} remaining={after_remaining}"
                )

            if env.is_terminal:
                break

        final_state = MastermindEvalState(colors, code_length, duplicates_allowed, list(env.history), all_codes)
        return EpisodeResult(
            episode=episode,
            seed=seed,
            policy=policy_name,
            solved=bool(env.history and env.history[-1]["exact"] == code_length),
            guesses=len(env.history),
            exact=final_exact,
            partial=final_partial,
            invalid_moves=invalid_moves,
            secret=secret,
            remaining_candidates=len(consistent_candidates(final_state)),
        )


def summarize(results: list[EpisodeResult]) -> dict[str, Any]:
    guesses = [result.guesses for result in results]
    solved_results = [result for result in results if result.solved]
    return {
        "game": "mastermind",
        "episodes": len(results),
        "policy": results[0].policy if results else "",
        "games_solved": len(solved_results),
        "solve_rate": (len(solved_results) / len(results)) if results else 0.0,
        "mean_guesses": statistics.mean(guesses) if guesses else 0,
        "median_guesses": statistics.median(guesses) if guesses else 0,
        "mean_guesses_solved": (
            statistics.mean([result.guesses for result in solved_results])
            if solved_results else 0
        ),
        "invalid_moves": sum(result.invalid_moves for result in results),
        "mean_remaining_candidates": (
            statistics.mean([result.remaining_candidates for result in results])
            if results else 0
        ),
    }


def run(args: argparse.Namespace) -> None:
    colors = list(FLAIR_COLORS[: args.num_colors])
    if args.code_length > len(colors) and not args.duplicates_allowed:
        raise ValueError("code_length cannot exceed num_colors when duplicates are disabled.")

    log_dir = Path(args.log_dir or f"logs/evaluations/mastermind/{args.policy}")
    llm = build_llm(args, _MOCK_MASTERMIND_RESPONSES) if args.policy == "llm" else None
    results = [
        run_episode(
            episode=episode,
            seed=args.seed + episode,
            policy_name=args.policy,
            colors=colors,
            code_length=args.code_length,
            max_attempts=args.max_attempts,
            duplicates_allowed=args.duplicates_allowed,
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
    summary.update({
        "code_length": args.code_length,
        "num_colors": args.num_colors,
        "max_attempts": args.max_attempts,
        "duplicates_allowed": args.duplicates_allowed,
    })
    print("\nSummary:")
    print(json.dumps(summary, indent=2, sort_keys=True))

    if write_summary(log_dir, args.policy, summary) is not None:
        print(f"\nWrote logs to {log_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the local Mastermind environment.")
    parser.add_argument("--policy", choices=sorted([*POLICIES, "llm"]), default="candidate")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--code-length", type=int, default=4)
    parser.add_argument("--num-colors", type=int, default=6)
    parser.add_argument("--max-attempts", type=int, default=10)
    parser.add_argument("--duplicates-allowed", action="store_true")
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--verbose", action="store_true")
    add_llm_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())

"""Evaluate the local Werewolf environment with optional error localization.

Usage:
    python -m evaluations.werewolf.eval --episodes 5 --model mock
    python -m evaluations.werewolf.eval --episodes 5 --model openai --localization trace
    python -m evaluations.werewolf.eval --episodes 5 --model openai --localization feedback
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from causal_agent import (
    Actor,
    FeedbackProcessor,
    MemoryEntry,
    MemoryStore,
)
from causal_agent.acting import GameAction
from causal_agent.error_localization import (
    TracerAdapter,
    add_error_localization_args,
    build_turn_audit_script,
    config_from_args,
    localization_goal,
    sanitize_observation,
)
from evaluations.common import (
    TraceLogger,
    add_llm_args,
    build_llm,
    build_planner,
    dataclass_to_dict,
    plan_action_with_retry,
    write_summary,
)
from games.werewolf import WerewolfEnv


DEFAULT_PLAYERS = ("Agent", "Alice", "Bob", "Charlie", "Dave")
AGENT_GOAL = (
    "Win Werewolf. If you are a villager, identify and eliminate the werewolf. "
    "If you are the werewolf, eliminate villagers without being caught."
)

_MOCK_WEREWOLF_RESPONSES = [
    '{"intent": "open discussion", "action_type": "speak", '
    '"parameters": {"message": "I am tracking contradictions in the public claims before voting."}, '
    '"public_rationale": "Start by asking for evidence without overcommitting."}',
    '{"intent": "vote on available suspicion", "action_type": "vote", '
    '"parameters": {"target": "Alice"}, '
    '"public_rationale": "Alice is the first available vote target in this simple baseline."}',
    '{"intent": "remove a villager at night", "action_type": "kill", '
    '"parameters": {"target": "Bob"}, '
    '"public_rationale": "If I am the werewolf, remove a living non-self player."}',
]


@dataclass
class EpisodeResult:
    episode: int
    seed: int
    policy: str
    localization: str
    won: bool
    reward: float
    survived: bool
    terminal: bool
    winner: str
    agent_role: str
    turns: int
    actions: int
    invalid_moves: int
    localization_runs: int
    localization_findings: int
    localization_logic_findings: int
    localization_skipped: int
    replans_triggered: int
    action_changed_after_localization: int


def run_episode(
    episode: int,
    seed: int,
    policy_name: str,
    players: list[str],
    n_werewolves: int,
    max_turns: int,
    log_dir: Path | None,
    verbose: bool,
    llm: Any,
    localization_config,
    simulate_before_plan: bool = False,
) -> EpisodeResult:
    if policy_name != "llm":
        raise ValueError(f"Unsupported Werewolf policy: {policy_name}")

    agent_id = "Agent"
    env = WerewolfEnv(
        players=players,
        agent_id=agent_id,
        n_werewolves=n_werewolves,
        seed=seed,
    )
    planner = build_planner(
        env,
        llm,
        agent_id=agent_id,
        simulate_before_plan=simulate_before_plan,
    )
    actor = Actor(post_processors=[Actor.truncate_message(250), Actor.normalise_target_case()])
    feedback_processor = FeedbackProcessor()
    memory = MemoryStore(max_short_term=100)
    kripke = env.initial_kripke(agent_id)
    localizer = TracerAdapter(localization_config)

    invalid_moves = 0
    localization_runs = 0
    localization_findings = 0
    localization_logic_findings = 0
    localization_skipped = 0
    replans_triggered = 0
    changed_after_localization = 0
    actions_taken = 0
    final_reward = 0.0
    loop_turns = 0

    trace_filename = f"episode_{episode:04d}_{policy_name}_{localization_config.mode}_seed_{seed}.jsonl"
    with TraceLogger(log_dir, trace_filename) as trace:
        for turn in range(max_turns):
            loop_turns = turn + 1
            obs = env.observe(agent_id)
            final_reward = float(obs.get("reward", final_reward))
            if obs.get("terminal") or env.is_terminal:
                break

            event = feedback_processor.process(obs, turn)
            memory.add(MemoryEntry(
                turn=turn,
                kind=event.kind.value,
                source=event.source,
                content=event.content,
                metadata={
                    "facts": event.facts,
                    "phase": obs.get("phase", ""),
                    "alive_players": obs.get("alive_players", []),
                    "public_log": obs.get("public_log", []),
                },
            ))
            if event.facts:
                kripke = kripke.update_with_facts(event.facts)
            memory.snapshot_kripke(turn, kripke)

            action_specs = env.action_specs(agent_id)
            if not action_specs:
                continue

            plan, action, invalid_count = plan_action_with_retry(
                planner=planner,
                actor=actor,
                kripke=kripke,
                memory=memory,
                goal=AGENT_GOAL,
                agent_id=agent_id,
                action_specs=action_specs,
                turn=turn,
            )
            invalid_moves += invalid_count
            pre_localization_action = _action_to_dict(action)
            localization_result = None
            replanned = False

            if localization_config.mode == "feedback":
                localization_result = _audit_turn(
                    localizer=localizer,
                    turn=turn,
                    observation=obs,
                    plan=plan,
                    action=action,
                    action_specs=action_specs,
                    agent_id=agent_id,
                )
                localization_runs += int(localization_result.ran)
                localization_findings += localization_result.finding_count
                localization_logic_findings += int(localization_result.has_logic_error)
                localization_skipped += int(bool(localization_result.skipped_reason))

                if localization_result.has_logic_error:
                    replanned = True
                    replans_triggered += 1
                    memory.add(MemoryEntry(
                        turn=turn,
                        kind="error_localization",
                        source="tracer",
                        content=localization_result.summary(),
                        metadata=localization_result.to_dict(),
                    ))
                    plan, action, invalid_count = plan_action_with_retry(
                        planner=planner,
                        actor=actor,
                        kripke=kripke,
                        memory=memory,
                        goal=AGENT_GOAL,
                        agent_id=agent_id,
                        action_specs=action_specs,
                        turn=turn,
                    )
                    invalid_moves += invalid_count
                    if _action_to_dict(action) != pre_localization_action:
                        changed_after_localization += 1

            feedback = env.step(agent_id, action)
            final_reward = float(feedback.get("reward", final_reward))
            if feedback.get("kind") == "illegal_move":
                invalid_moves += 1
            actions_taken += 1

            if localization_config.mode == "trace":
                localization_result = _audit_turn(
                    localizer=localizer,
                    turn=turn,
                    observation=obs,
                    plan=plan,
                    action=action,
                    action_specs=action_specs,
                    agent_id=agent_id,
                    feedback=feedback,
                )
                localization_runs += int(localization_result.ran)
                localization_findings += localization_result.finding_count
                localization_logic_findings += int(localization_result.has_logic_error)
                localization_skipped += int(bool(localization_result.skipped_reason))

            record = {
                "episode": episode,
                "turn": turn,
                "seed": seed,
                "policy": policy_name,
                "localization": localization_config.mode,
                "observed_turn_state": sanitize_observation(obs, agent_id=agent_id),
                "planner_trace": planner.last_trace,
                "pre_localization_action": pre_localization_action,
                "action": _action_to_dict(action),
                "feedback": {
                    "kind": str(feedback.get("kind", "")),
                    "content": str(feedback.get("content", "")),
                    "reward": float(feedback.get("reward", 0.0)),
                    "terminal": bool(feedback.get("terminal", False)),
                },
                "localization_result": (
                    localization_result.to_dict()
                    if localization_result is not None
                    else None
                ),
                "replanned_after_localization": replanned,
                "action_changed_after_localization": (
                    _action_to_dict(action) != pre_localization_action
                ),
                "terminal": env.is_terminal,
                "winner": env._winner or "",
                "agent_role": env._players[agent_id].role,
                "role_assignments": {
                    name: player.role for name, player in env._players.items()
                },
            }
            trace.write(record)

            if verbose:
                print(
                    f"[ep={episode} t={turn}] action={action.action_type} "
                    f"payload={action.payload} feedback={feedback.get('content', '')}"
                )
                if localization_result is not None:
                    print(f"  localization: {localization_result.summary()}")

            if env.is_terminal:
                break

    final_obs = env.observe(agent_id)
    final_reward = float(final_obs.get("reward", final_reward))
    session_terminal = bool(final_obs.get("terminal", False) or env.is_terminal)
    return EpisodeResult(
        episode=episode,
        seed=seed,
        policy=policy_name,
        localization=localization_config.mode,
        won=final_reward > 0,
        reward=final_reward,
        survived=bool(env._players[agent_id].alive),
        terminal=session_terminal,
        winner=env._winner or "",
        agent_role=env._players[agent_id].role,
        turns=loop_turns,
        actions=actions_taken,
        invalid_moves=invalid_moves,
        localization_runs=localization_runs,
        localization_findings=localization_findings,
        localization_logic_findings=localization_logic_findings,
        localization_skipped=localization_skipped,
        replans_triggered=replans_triggered,
        action_changed_after_localization=changed_after_localization,
    )


def summarize(results: list[EpisodeResult]) -> dict[str, Any]:
    rewards = [result.reward for result in results]
    turns = [result.turns for result in results]
    return {
        "game": "werewolf",
        "episodes": len(results),
        "policy": results[0].policy if results else "",
        "localization": results[0].localization if results else "",
        "wins": sum(result.won for result in results),
        "win_rate": (sum(result.won for result in results) / len(results)) if results else 0.0,
        "mean_reward": statistics.mean(rewards) if rewards else 0.0,
        "survival_rate": (
            sum(result.survived for result in results) / len(results)
            if results else 0.0
        ),
        "mean_turns": statistics.mean(turns) if turns else 0.0,
        "terminal_episodes": sum(result.terminal for result in results),
        "invalid_moves": sum(result.invalid_moves for result in results),
        "localization_runs": sum(result.localization_runs for result in results),
        "localization_findings": sum(result.localization_findings for result in results),
        "localization_logic_findings": sum(
            result.localization_logic_findings for result in results
        ),
        "localization_skipped": sum(result.localization_skipped for result in results),
        "replans_triggered": sum(result.replans_triggered for result in results),
        "action_changed_after_localization": sum(
            result.action_changed_after_localization for result in results
        ),
    }


def run(args: argparse.Namespace) -> None:
    players = _parse_players(args.players)
    if "Agent" not in players:
        raise ValueError("--players must include Agent")
    if not 1 <= args.n_werewolves < len(players):
        raise ValueError("--n-werewolves must be at least 1 and less than player count")

    log_dir = Path(
        args.log_dir
        or Path("logs") / "evaluations" / "werewolf" / args.policy / args.localization
    )
    llm = build_llm(args, _MOCK_WEREWOLF_RESPONSES)
    localization_config = config_from_args(args)
    results = [
        run_episode(
            episode=episode,
            seed=args.seed + episode,
            policy_name=args.policy,
            players=players,
            n_werewolves=args.n_werewolves,
            max_turns=args.max_turns,
            log_dir=log_dir,
            verbose=args.verbose,
            llm=llm,
            localization_config=localization_config,
            simulate_before_plan=args.simulate_before_plan,
        )
        for episode in range(args.episodes)
    ]

    print("\nEpisode results:")
    for result in results:
        print(json.dumps(dataclass_to_dict(result), sort_keys=True))

    summary = summarize(results)
    summary.update({
        "players": players,
        "n_werewolves": args.n_werewolves,
        "max_turns": args.max_turns,
    })
    print("\nSummary:")
    print(json.dumps(summary, indent=2, sort_keys=True))

    summary_path = write_summary(log_dir, f"{args.policy}_{args.localization}", summary)
    if summary_path is not None:
        print(f"\nWrote logs to {log_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the local Werewolf environment.")
    parser.add_argument("--policy", choices=["llm"], default="llm")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--players", default=",".join(DEFAULT_PLAYERS))
    parser.add_argument("--n-werewolves", type=int, default=1)
    parser.add_argument("--max-turns", type=int, default=50)
    parser.add_argument("--simulate-before-plan", action="store_true")
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--verbose", action="store_true")
    add_llm_args(parser)
    add_error_localization_args(parser)
    return parser.parse_args()


def _audit_turn(
    *,
    localizer: TracerAdapter,
    turn: int,
    observation: dict[str, Any],
    plan,
    action: GameAction,
    action_specs,
    agent_id: str,
    feedback: dict[str, Any] | None = None,
):
    script = build_turn_audit_script(
        game="werewolf",
        turn=turn,
        goal=AGENT_GOAL,
        observation=observation,
        plan=plan,
        action=action,
        agent_id=agent_id,
        feedback=feedback,
        legal_actions=[spec.action_type for spec in action_specs],
    )
    return localizer.audit_script(script, localization_goal("werewolf", AGENT_GOAL))


def _action_to_dict(action: GameAction) -> dict[str, Any]:
    return {
        "action_type": action.action_type,
        "payload": dict(action.payload),
        "agent_id": action.agent_id,
    }


def _parse_players(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


if __name__ == "__main__":
    run(parse_args())

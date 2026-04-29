"""
Run a small Mastermind session with structured game actions.

Usage:
    python -m examples.run_mastermind
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from causal_agent import (  # noqa: E402
    AgentConfig,
    Actor,
    FeedbackProcessor,
    MemoryStore,
    MockLLM,
    Orchestrator,
    Planner,
)
from games.mastermind import MastermindEnv  # noqa: E402


def run(args: argparse.Namespace) -> None:
    agent_id = "Agent"
    secret = ["red", "green", "blue", "yellow"]
    responses = [
        '{"intent": "test a complete candidate", "action_type": "guess", '
        '"parameters": {"code": ["red", "green", "blue", "yellow"]}, '
        '"public_rationale": "This is a valid exact-length candidate."}'
    ]

    env = MastermindEnv(secret=secret, max_attempts=args.max_attempts, agent_id=agent_id)
    orchestrator = Orchestrator(
        env=env,
        planner=Planner(MockLLM(responses), simulate_before_plan=False),
        actor=Actor(),
        feedback_processor=FeedbackProcessor(),
        memory=MemoryStore(max_short_term=40),
        kripke=env.initial_kripke(agent_id),
        config=AgentConfig(
            agent_id=agent_id,
            goal="Solve the Mastermind code using structured guesses and feedback.",
            max_turns=args.max_attempts + 1,
            verbose=True,
        ),
    )

    print("Starting Mastermind session...")
    result = orchestrator.run_session()
    print(result.summary())
    print(f"Secret: {env.secret}")
    print(f"History: {env.history}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mastermind demo for causal_agent.")
    parser.add_argument("--max-attempts", type=int, default=6)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())

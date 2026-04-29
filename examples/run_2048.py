"""
Run a small 2048 session with structured game actions.

Usage:
    python -m examples.run_2048
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
from games.game_2048 import Game2048Env  # noqa: E402


def run(args: argparse.Namespace) -> None:
    agent_id = "Agent"
    responses = [
        '{"intent": "keep the board mobile", "action_type": "slide", '
        '"parameters": {"direction": "left"}, "public_rationale": "Merge low tiles."}',
        '{"intent": "open space", "action_type": "slide", '
        '"parameters": {"direction": "up"}, "public_rationale": "Move tiles upward."}',
        '{"intent": "seek merges", "action_type": "slide", '
        '"parameters": {"direction": "right"}, "public_rationale": "Try another merge lane."}',
        '{"intent": "avoid stalling", "action_type": "slide", '
        '"parameters": {"direction": "down"}, "public_rationale": "Rebalance the board."}',
    ]

    env = Game2048Env(seed=args.seed, agent_id=agent_id)
    orchestrator = Orchestrator(
        env=env,
        planner=Planner(MockLLM(responses), simulate_before_plan=False),
        actor=Actor(),
        feedback_processor=FeedbackProcessor(),
        memory=MemoryStore(max_short_term=40),
        kripke=env.initial_kripke(agent_id),
        config=AgentConfig(
            agent_id=agent_id,
            goal="Maximize score in 2048 by choosing legal slide directions.",
            max_turns=args.max_turns,
            verbose=True,
        ),
    )

    print("Starting 2048 session...")
    result = orchestrator.run_session()
    print(result.summary())
    print(f"Score: {env.score}")
    print(f"Board: {env.board}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2048 demo for causal_agent.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-turns", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())

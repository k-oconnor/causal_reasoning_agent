from __future__ import annotations

import unittest

from causal_agent import (
    AgentConfig,
    Actor,
    FeedbackProcessor,
    MemoryStore,
    MockLLM,
    Orchestrator,
    Planner,
)
from games.game_2048 import Game2048Env
from games.mastermind import MastermindEnv
from games.werewolf import WerewolfEnv


class GameSmokeTests(unittest.TestCase):
    def test_werewolf_smoke_with_action_specs(self) -> None:
        agent_id = "Agent"
        env = WerewolfEnv(
            players=["Agent", "Alice", "Bob", "Charlie"],
            agent_id=agent_id,
            seed=1,
        )
        result = Orchestrator(
            env=env,
            planner=Planner(MockLLM(), simulate_before_plan=True),
            actor=Actor(post_processors=[Actor.truncate_message(250)]),
            feedback_processor=FeedbackProcessor(),
            memory=MemoryStore(max_short_term=20),
            kripke=env.initial_kripke(agent_id),
            config=AgentConfig(
                agent_id=agent_id,
                goal="Win Werewolf.",
                max_turns=4,
                verbose=False,
            ),
        ).run_session()

        self.assertGreaterEqual(result.total_turns, 0)

    def test_2048_smoke_with_action_specs(self) -> None:
        agent_id = "Agent"
        env = Game2048Env(seed=3, agent_id=agent_id)
        result = Orchestrator(
            env=env,
            planner=Planner(
                MockLLM([
                    '{"intent": "move", "action_type": "slide", '
                    '"parameters": {"direction": "left"}, "public_rationale": "merge"}'
                ]),
                simulate_before_plan=False,
            ),
            actor=Actor(),
            feedback_processor=FeedbackProcessor(),
            memory=MemoryStore(max_short_term=20),
            kripke=env.initial_kripke(agent_id),
            config=AgentConfig(
                agent_id=agent_id,
                goal="Maximize score.",
                max_turns=3,
                verbose=False,
            ),
        ).run_session()

        self.assertGreaterEqual(result.total_turns, 0)
        self.assertIsInstance(env.board, list)

    def test_mastermind_smoke_with_action_specs(self) -> None:
        agent_id = "Agent"
        env = MastermindEnv(
            secret=["red", "green", "blue", "yellow"],
            max_attempts=3,
            agent_id=agent_id,
        )
        result = Orchestrator(
            env=env,
            planner=Planner(
                MockLLM([
                    '{"intent": "solve", "action_type": "guess", '
                    '"parameters": {"code": ["red", "green", "blue", "yellow"]}, '
                    '"public_rationale": "try exact candidate"}'
                ]),
                simulate_before_plan=False,
            ),
            actor=Actor(),
            feedback_processor=FeedbackProcessor(),
            memory=MemoryStore(max_short_term=20),
            kripke=env.initial_kripke(agent_id),
            config=AgentConfig(
                agent_id=agent_id,
                goal="Solve Mastermind.",
                max_turns=3,
                verbose=False,
            ),
        ).run_session()

        self.assertTrue(env.is_terminal)
        self.assertTrue(result.terminal)


if __name__ == "__main__":
    unittest.main()

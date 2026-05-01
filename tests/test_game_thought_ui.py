from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from causal_agent.game_trace import GameRunConfig, GameThoughtSession
from causal_agent.llm import MockLLM


class GameThoughtSessionTests(unittest.TestCase):
    def test_2048_step_records_safe_decision_trace(self) -> None:
        session = GameThoughtSession(
            GameRunConfig(game="2048", seed=3, max_turns=5),
            MockLLM([
                '{"intent": "move left", "action_type": "slide", '
                '"parameters": {"direction": "left"}, '
                '"public_rationale": "Merge tiles while keeping space."}'
            ]),
        )

        trace = session.step()
        snapshot = session.snapshot()

        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual(len(snapshot["history"]), 1)
        self.assertEqual(snapshot["latest_act"]["action_type"], "slide")
        self.assertIn("board", trace["state_before"])
        self.assertIn("board", trace["state_after"])
        self.assertTrue(trace["legal_options"])
        self.assertEqual(trace["action"]["action_type"], "slide")
        self.assertEqual(
            trace["planner_trace"]["decision"]["public_rationale"],
            "Merge tiles while keeping space.",
        )
        self.assertIn("preview_notes", trace["planner_trace"])
        self.assertIn("tool_calls", trace["planner_trace"])
        self._assert_no_private_trace_keys(trace["planner_trace"])

    def test_mastermind_step_hides_secret_until_terminal(self) -> None:
        session = GameThoughtSession(
            GameRunConfig(
                game="mastermind",
                seed=1,
                max_turns=3,
                mastermind_colors=("red", "blue", "green", "yellow"),
                mastermind_code_length=2,
                mastermind_max_attempts=3,
                mastermind_duplicates_allowed=False,
                mastermind_secret=("green", "yellow"),
            ),
            MockLLM([
                '{"intent": "probe colors", "action_type": "guess", '
                '"parameters": {"code": ["red", "blue"]}, '
                '"public_rationale": "Test two colors and positions."}'
            ]),
        )

        before = session.snapshot()
        self.assertNotIn("secret", before["state"])

        trace = session.step()
        after = session.snapshot()

        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertNotIn("secret", trace["state_before"])
        self.assertNotIn("secret", trace["state_after"])
        self.assertNotIn("secret", after["state"])
        self.assertEqual(trace["action"]["payload"]["code"], ["red", "blue"])
        self.assertIn("candidate_count_before", trace["action_analysis"])
        self.assertIn("candidate_count_after", trace["action_analysis"])
        self.assertIn("chosen_guess_info", trace["action_analysis"])
        self.assertEqual(
            trace["planner_trace"]["decision"]["public_rationale"],
            "Test two colors and positions.",
        )
        self._assert_no_private_trace_keys(trace["planner_trace"])

    def test_planner_trace_serializes_without_prompt_or_raw_messages(self) -> None:
        session = GameThoughtSession(
            GameRunConfig(game="2048", seed=4, max_turns=2),
            MockLLM([
                '{"intent": "move up", "action_type": "slide", '
                '"parameters": {"direction": "up"}, "public_rationale": "Open columns."}'
            ]),
        )

        trace = session.step()
        assert trace is not None
        planner_trace = trace["planner_trace"]
        encoded = json.dumps(planner_trace).lower()

        self.assertNotIn("=== agent", encoded)
        self.assertNotIn("legal action schemas", encoded)
        self._assert_no_private_trace_keys(planner_trace)

    def test_step_appends_one_jsonl_record_per_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = GameThoughtSession(
                GameRunConfig(
                    game="2048",
                    seed=5,
                    max_turns=3,
                    log_dir=tmp,
                    episode=2,
                ),
                MockLLM([
                    '{"intent": "move left", "action_type": "slide", '
                    '"parameters": {"direction": "left"}, "public_rationale": "Merge."}',
                    '{"intent": "move up", "action_type": "slide", '
                    '"parameters": {"direction": "up"}, "public_rationale": "Open space."}',
                ]),
            )

            first = session.step()
            second = session.step()
            self.assertIsNotNone(first)
            self.assertIsNotNone(second)

            log_path = Path(session.snapshot()["log_path"])
            self.assertEqual(log_path, Path(tmp) / "episode_0002_llm_seed_5.jsonl")
            records = [
                json.loads(line)
                for line in log_path.read_text().splitlines()
                if line.strip()
            ]

            self.assertEqual(len(records), 2)
            self.assertEqual([record["turn"] for record in records], [0, 1])
            self.assertEqual(records[0]["policy"], "llm")
            self.assertEqual(records[0]["game"], "2048")
            self.assertIn("planner_trace", records[0])
            self.assertIn("board_before", records[0])
            self.assertIn("board_after", records[0])

    def _assert_no_private_trace_keys(self, value) -> None:
        private_keys = {"prompt", "raw", "messages", "raw_output", "raw_response"}
        if isinstance(value, dict):
            for key, item in value.items():
                self.assertNotIn(str(key).lower(), private_keys)
                self._assert_no_private_trace_keys(item)
        elif isinstance(value, list):
            for item in value:
                self._assert_no_private_trace_keys(item)


if __name__ == "__main__":
    unittest.main()

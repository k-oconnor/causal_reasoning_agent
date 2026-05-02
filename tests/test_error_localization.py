from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from causal_agent.acting import GameAction
from causal_agent.error_localization import (
    ErrorLocalizationConfig,
    LocalizationFinding,
    TracerAdapter,
    build_turn_audit_script,
)
from causal_agent.planning import Plan


class ErrorLocalizationTests(unittest.TestCase):
    def test_resolves_explicit_tracer_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracer_dir = Path(tmp)
            for filename in ("parser.py", "executor.py", "judge.py", "reporter.py"):
                (tracer_dir / filename).write_text("# fake tracer module\n")

            adapter = TracerAdapter(ErrorLocalizationConfig(mode="trace", tracer_dir=tracer_dir))

            self.assertEqual(adapter.resolve_tracer_dir(), tracer_dir.resolve())

    def test_unavailable_tracer_returns_skipped_result(self) -> None:
        adapter = TracerAdapter(ErrorLocalizationConfig(mode="trace"))

        result = adapter.audit_script("print('hello')", "Say hello.")

        self.assertFalse(result.ran)
        self.assertTrue(result.skipped_reason or result.error)

    def test_turn_audit_script_omits_hidden_role_facts(self) -> None:
        script = build_turn_audit_script(
            game="werewolf",
            turn=2,
            goal="Win Werewolf.",
            agent_id="Agent",
            observation={
                "kind": "observation",
                "phase": "day_vote",
                "alive_players": ["Agent", "Alice", "Bob"],
                "public_log": [],
                "facts": {
                    "role_Agent": "villager",
                    "role_Alice": "werewolf",
                },
            },
            plan=Plan(
                intent="vote",
                action_type="vote",
                parameters={"target": "Alice"},
                reasoning="Alice is suspicious.",
            ),
            action=GameAction("vote", {"target": "Alice"}, "Agent"),
            legal_actions=["vote"],
        )

        self.assertIn("role_Agent", script)
        self.assertNotIn("role_Alice", script)

    def test_fake_runner_findings_are_serialized(self) -> None:
        def fake_runner(source, goal, config):
            self.assertIn("print", source)
            self.assertEqual(goal, "Goal.")
            return [
                LocalizationFinding(
                    lineno=10,
                    code="inspect_action(state)",
                    error_type="LogicError",
                    error_message="Action is not aligned.",
                )
            ]

        adapter = TracerAdapter(
            ErrorLocalizationConfig(mode="feedback"),
            runner=fake_runner,
        )

        result = adapter.audit_script("print('x')", "Goal.")

        self.assertTrue(result.ran)
        self.assertTrue(result.has_logic_error)
        self.assertEqual(result.to_dict()["findings"][0]["lineno"], 10)


if __name__ == "__main__":
    unittest.main()

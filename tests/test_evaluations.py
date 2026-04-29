from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from evaluations.common import TraceLogger, dataclass_to_dict, write_summary


@dataclass
class _TinyResult:
    episode: int
    score: int


class EvaluationCommonTests(unittest.TestCase):
    def test_trace_summary_and_dataclass_serialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            with TraceLogger(log_dir, "episode.jsonl") as trace:
                trace.write({"turn": 0, "action": "left"})

            trace_path = log_dir / "episode.jsonl"
            self.assertTrue(trace_path.exists())
            self.assertEqual(
                json.loads(trace_path.read_text().strip()),
                {"turn": 0, "action": "left"},
            )

            summary_path = write_summary(log_dir, "tiny", {"episodes": 1})
            self.assertEqual(summary_path, log_dir / "summary_tiny.json")
            self.assertEqual(json.loads(summary_path.read_text()), {"episodes": 1})

            self.assertEqual(
                dataclass_to_dict(_TinyResult(episode=2, score=64)),
                {"episode": 2, "score": 64},
            )


class EvaluationSmokeTests(unittest.TestCase):
    def test_2048_eval_cli_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evaluations.game_2048.eval",
                    "--policy",
                    "greedy",
                    "--episodes",
                    "1",
                    "--max-turns",
                    "20",
                    "--log-dir",
                    tmp,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(tmp) / "summary_greedy.json").exists())

    def test_mastermind_eval_cli_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evaluations.mastermind.eval",
                    "--policy",
                    "candidate",
                    "--episodes",
                    "1",
                    "--log-dir",
                    tmp,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(tmp) / "summary_candidate.json").exists())


if __name__ == "__main__":
    unittest.main()


from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from causal_agent import SkillBootstrapper, SkillSpec
from causal_agent.llm import BaseLLM
from causal_agent.tools import LLMResponse, ToolCall


class _NoCallLLM(BaseLLM):
    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        raise AssertionError("LLM should not be called")

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        raise AssertionError("LLM should not be called")


class _ToolCallingLLM(BaseLLM):
    def __init__(self, tool_calls: list[ToolCall]) -> None:
        self._tool_calls = tool_calls
        self.calls = 0

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        return ""

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(tool_calls=self._tool_calls)
        return LLMResponse(content="done")


class SkillBootstrapTests(unittest.TestCase):
    def test_existing_skills_are_loaded_without_llm_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = Path(tmp) / "2048"
            game_dir.mkdir()
            (game_dir / "strategy.md").write_text("# Strategy\n\nKeep a stable corner.\n", encoding="utf-8")

            docs = SkillBootstrapper(skills_root=tmp).ensure_skills(
                "2048",
                [SkillSpec("strategy.md", "2048 strategy", "Useful tactical advice.")],
                _NoCallLLM(),
            )

        self.assertEqual(len(docs), 1)
        self.assertIn("2048/strategy", docs[0])
        self.assertIn("stable corner", docs[0])

    def test_missing_skill_can_be_written_by_scoped_save_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            llm = _ToolCallingLLM([
                ToolCall(
                    id="call_1",
                    name="save_skill",
                    arguments={
                        "filename": "strategy.md",
                        "content": "# Strategy\n\nPrefer corners.\n\n## Sources\n- https://example.com",
                    },
                )
            ])

            docs = SkillBootstrapper(
                skills_root=tmp,
                enable_research=False,
            ).ensure_skills(
                "2048",
                [SkillSpec("strategy.md", "2048 strategy", "Contains sources.")],
                llm,
            )

            path = Path(tmp) / "2048" / "strategy.md"
            self.assertTrue(path.exists())
            self.assertIn("Prefer corners", path.read_text(encoding="utf-8"))
            self.assertIn("Prefer corners", docs[0])
            self.assertEqual(llm.calls, 1)

    def test_save_tool_does_not_overwrite_existing_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = Path(tmp) / "mastermind"
            game_dir.mkdir()
            existing = game_dir / "existing.md"
            existing.write_text("# Existing\n\nKeep me.\n", encoding="utf-8")

            llm = _ToolCallingLLM([
                ToolCall(
                    id="call_1",
                    name="save_skill",
                    arguments={"filename": "existing.md", "content": "overwrite"},
                ),
                ToolCall(
                    id="call_2",
                    name="save_skill",
                    arguments={
                        "filename": "missing.md",
                        "content": "# Missing\n\nNew doc.\n\n## Sources\n- https://example.com",
                    },
                ),
            ])

            docs = SkillBootstrapper(
                skills_root=tmp,
                enable_research=False,
            ).ensure_skills(
                "mastermind",
                [
                    SkillSpec("existing.md", "Existing", "Preserved."),
                    SkillSpec("missing.md", "Missing", "Created."),
                ],
                llm,
            )

            self.assertEqual(existing.read_text(encoding="utf-8"), "# Existing\n\nKeep me.\n")
            self.assertEqual(len(docs), 2)
            self.assertIn("New doc", docs[1])

    def test_manifest_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                SkillBootstrapper(skills_root=tmp).ensure_skills(
                    "2048",
                    [SkillSpec("../bad.md", "Bad", "Must not escape root.")],
                    _NoCallLLM(),
                )


if __name__ == "__main__":
    unittest.main()

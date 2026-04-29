"""
causal_agent/skill_bootstrap.py

One-time research-to-skill bootstrap for game evaluations.

The bootstrapper uses the existing research tools to let an LLM gather
strategy material, then writes a fixed set of Markdown skill files. Existing
skills are loaded and preserved; only missing files from the supplied manifest
may be written.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from causal_agent.llm import BaseLLM
from causal_agent.research_tools import ResearchTools
from causal_agent.tools import ToolCall, ToolDefinition, ToolRegistry

log = logging.getLogger("causal_agent.skill_bootstrap")

DEFAULT_SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills" / "generated"


@dataclass(frozen=True)
class SkillSpec:
    """Manifest entry for one generated Markdown skill."""

    filename: str
    topic: str
    success_criteria: str


class SkillBootstrapper:
    """
    Generate missing per-game skills by researching with existing tools.

    Parameters
    ----------
    skills_root : Directory containing generated per-game subdirectories.
    tavily_api_key : Optional Tavily key; defaults to TAVILY_API_KEY.
    enable_research : If False, only save_skill is registered. This is mainly
                      useful for tests with fake tool-calling LLMs.
    """

    def __init__(
        self,
        skills_root: str | Path = DEFAULT_SKILLS_ROOT,
        tavily_api_key: str | None = None,
        max_iterations: int = 12,
        max_tokens: int = 4096,
        enable_research: bool = True,
    ) -> None:
        self._skills_root = Path(skills_root).resolve()
        self._tavily_api_key = tavily_api_key
        self._max_iterations = max_iterations
        self._max_tokens = max_tokens
        self._enable_research = enable_research

    def ensure_skills(
        self,
        game_id: str,
        manifest: list[SkillSpec],
        llm: BaseLLM,
    ) -> list[str]:
        """
        Ensure all manifest skills exist, generating only missing files.

        Returns loaded Markdown docs in manifest order. If all files already
        exist, this returns without making any LLM or Tavily calls.
        """
        if not manifest:
            return []

        safe_game_id = self._validate_game_id(game_id)
        for spec in manifest:
            self._validate_filename(spec.filename)

        game_dir = (self._skills_root / safe_game_id).resolve()
        self._assert_inside(self._skills_root, game_dir)
        game_dir.mkdir(parents=True, exist_ok=True)

        missing = self._missing_specs(game_dir, manifest)
        if not missing:
            log.info("Loaded existing generated skills for %s from %s", game_id, game_dir)
            return self._load_docs(game_id, game_dir, manifest)

        log.info(
            "Bootstrapping %d missing generated skill(s) for %s in %s",
            len(missing),
            game_id,
            game_dir,
        )

        registry = ToolRegistry()
        if self._enable_research:
            try:
                ResearchTools(tavily_api_key=self._tavily_api_key).register_all(registry)
            except ValueError as exc:
                raise ValueError(
                    "Skill bootstrap requires TAVILY_API_KEY for web_search. "
                    "Set TAVILY_API_KEY, pass tavily_api_key=, or disable bootstrap."
                ) from exc
        self._register_save_skill(registry, game_dir, missing)

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": self._build_prompt(game_id, manifest, missing)}
        ]

        for iteration in range(1, self._max_iterations + 1):
            response = llm.complete_with_tools(
                messages=messages,
                registry=registry,
                system=SKILL_BOOTSTRAP_SYSTEM,
                max_tokens=self._max_tokens,
            )

            if response.is_final:
                break

            messages.append(self._assistant_message(response.tool_calls))
            for tc in response.tool_calls:
                result = registry.dispatch(tc)
                log.info("skill bootstrap tool result << %s: %.200s", result.name, result.content)
                messages.append(result.to_openai_message())

            if not self._missing_specs(game_dir, manifest):
                log.info("Skill bootstrap complete for %s after %d iteration(s)", game_id, iteration)
                return self._load_docs(game_id, game_dir, manifest)

        still_missing = self._missing_specs(game_dir, manifest)
        if still_missing:
            filenames = ", ".join(spec.filename for spec in still_missing)
            raise RuntimeError(f"Skill bootstrap did not create required file(s): {filenames}")

        return self._load_docs(game_id, game_dir, manifest)

    def _register_save_skill(
        self,
        registry: ToolRegistry,
        game_dir: Path,
        missing: list[SkillSpec],
    ) -> None:
        allowed = {spec.filename for spec in missing}

        defn = ToolDefinition(
            name="save_skill",
            description=(
                "Write one generated Markdown skill file. You may only write "
                "filenames listed as missing in the manifest. Existing skill files "
                "cannot be overwritten."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "One allowed missing Markdown filename, e.g. strategy.md.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete Markdown content for the skill.",
                    },
                },
                "required": ["filename", "content"],
            },
        )

        def save_skill(filename: str, content: str) -> str:
            try:
                safe_name = self._validate_filename(filename)
            except ValueError as exc:
                return f"Error: {exc}"
            if safe_name not in allowed:
                return f"Error: {safe_name!r} is not one of the missing required skills."

            path = (game_dir / safe_name).resolve()
            self._assert_inside(game_dir, path)
            if path.exists():
                return f"Error: {safe_name!r} already exists and will not be overwritten."

            path.write_text(content.strip() + "\n", encoding="utf-8")
            log.info("save_skill: wrote %d chars to %s", len(content), path)
            return f"Saved skill to {path}"

        registry.register(defn, save_skill)

    def _build_prompt(
        self,
        game_id: str,
        manifest: list[SkillSpec],
        missing: list[SkillSpec],
    ) -> str:
        all_lines = [
            f"## Game\n{game_id}",
            "## Required Skill Manifest",
        ]
        for spec in manifest:
            status = "missing" if spec in missing else "exists"
            all_lines.append(
                f"- `{spec.filename}` [{status}]\n"
                f"  Topic: {spec.topic}\n"
                f"  Success criteria: {spec.success_criteria}"
            )

        missing_names = ", ".join(f"`{spec.filename}`" for spec in missing)
        all_lines.extend([
            "## Task",
            (
                "Research the missing skills using web_search and fetch_page. "
                f"Create only these missing files: {missing_names}."
            ),
            (
                "For each missing file, call save_skill(filename, content) exactly once. "
                "Each Markdown skill must include concrete tactical guidance, avoid vague "
                "background prose, and end with a short `## Sources` section containing "
                "the URLs you used."
            ),
            "Do not rewrite existing skills. Do not create extra files.",
        ])
        return "\n\n".join(all_lines)

    def _load_docs(
        self,
        game_id: str,
        game_dir: Path,
        manifest: list[SkillSpec],
    ) -> list[str]:
        docs: list[str] = []
        for spec in manifest:
            path = (game_dir / spec.filename).resolve()
            self._assert_inside(game_dir, path)
            content = path.read_text(encoding="utf-8").strip()
            if content:
                docs.append(f"### {game_id}/{Path(spec.filename).stem}\n\n{content}")
        return docs

    def _missing_specs(self, game_dir: Path, manifest: list[SkillSpec]) -> list[SkillSpec]:
        return [spec for spec in manifest if not (game_dir / spec.filename).exists()]

    def _assistant_message(self, tool_calls: list[ToolCall]) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in tool_calls
            ],
        }

    def _validate_game_id(self, game_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", game_id):
            raise ValueError(
                "game_id must contain only letters, numbers, underscores, dots, or hyphens."
            )
        return game_id

    def _validate_filename(self, filename: str) -> str:
        name = filename.replace("\\", "/")
        if not name or name != Path(name).name:
            raise ValueError(f"{filename!r} is not a bare filename.")
        if name in {".", ".."} or not name.endswith(".md"):
            raise ValueError(f"{filename!r} must be a Markdown filename ending in .md.")
        return name

    def _assert_inside(self, root: Path, path: Path) -> None:
        path.relative_to(root.resolve())


SKILL_BOOTSTRAP_SYSTEM = """
You are building reusable game-playing skills for an LLM agent.

Use the available research tools to find practical, source-backed strategy
guidance. Then write concise Markdown skill files with the save_skill tool.
The manifest is authoritative: write only missing files, use exact filenames,
and never overwrite an existing skill. Each skill should be directly useful
inside a turn-by-turn planner prompt.
""".strip()

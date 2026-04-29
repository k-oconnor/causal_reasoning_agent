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
from datetime import datetime, timezone
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
        audit_log_path: str | Path | None = None,
    ) -> None:
        self._skills_root = Path(skills_root).resolve()
        self._tavily_api_key = tavily_api_key
        self._max_iterations = max_iterations
        self._max_tokens = max_tokens
        self._enable_research = enable_research
        self._audit_log_path = Path(audit_log_path).resolve() if audit_log_path else None

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
        source_urls: set[str] = set()
        self._register_save_skill(registry, game_dir, missing, source_urls)

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": self._build_prompt(game_id, manifest, missing)}
        ]
        final_without_progress = 0

        for iteration in range(1, self._max_iterations + 1):
            kwargs: dict[str, Any] = {"max_tokens": self._max_tokens}
            if llm.__class__.__name__ in {"OpenAILLM", "DeepSeekLLM"}:
                kwargs["tool_choice"] = "required"
            response = llm.complete_with_tools(
                messages=messages,
                registry=registry,
                system=SKILL_BOOTSTRAP_SYSTEM,
                **kwargs,
            )

            if response.is_final:
                still_missing = self._missing_specs(game_dir, manifest)
                if not still_missing:
                    break
                final_without_progress += 1
                if final_without_progress >= 2:
                    if not self._enable_research:
                        filenames = ", ".join(spec.filename for spec in still_missing)
                        raise RuntimeError(
                            f"Skill bootstrap did not create required file(s): {filenames}"
                        )
                    self._fallback_generate_missing(game_id, game_dir, still_missing, llm)
                    return self._load_docs(game_id, game_dir, manifest)
                filenames = ", ".join(spec.filename for spec in still_missing)
                messages.append({"role": "assistant", "content": response.content or ""})
                messages.append({
                    "role": "user",
                    "content": (
                        "The required skill files still do not exist. You must use "
                        f"the save_skill tool to create these exact missing files: {filenames}. "
                        "Do not answer in prose until every missing file has been saved."
                    ),
                })
                continue

            messages.append(self._assistant_message(response.tool_calls))
            for tc in response.tool_calls:
                result = self._dispatch_with_audit(registry, tc, requested_by="llm")
                if tc.name in {"web_search", "fetch_page"}:
                    source_urls.update(self._extract_urls(result.content))
                log.info("skill bootstrap tool result << %s: %.200s", result.name, result.content)
                messages.append(result.to_openai_message())

            if not self._missing_specs(game_dir, manifest):
                log.info("Skill bootstrap complete for %s after %d iteration(s)", game_id, iteration)
                return self._load_docs(game_id, game_dir, manifest)

        still_missing = self._missing_specs(game_dir, manifest)
        if still_missing:
            if not self._enable_research:
                filenames = ", ".join(spec.filename for spec in still_missing)
                raise RuntimeError(f"Skill bootstrap did not create required file(s): {filenames}")
            self._fallback_generate_missing(game_id, game_dir, still_missing, llm)

        return self._load_docs(game_id, game_dir, manifest)

    def _fallback_generate_missing(
        self,
        game_id: str,
        game_dir: Path,
        missing: list[SkillSpec],
        llm: BaseLLM,
    ) -> None:
        """
        Deterministic fallback for models that decline tool calls.

        This still uses the existing Tavily-backed web_search tool; the caller
        orchestrates the search, then asks the LLM to synthesize Markdown from
        the returned sources.
        """
        registry = ToolRegistry()
        ResearchTools(tavily_api_key=self._tavily_api_key).register_all(registry)

        for spec in missing:
            path = (game_dir / spec.filename).resolve()
            self._assert_inside(game_dir, path)
            if path.exists():
                continue

            query = f"{game_id} {spec.topic} strategy guide best practices"
            search_result = self._dispatch_with_audit(registry, ToolCall(
                id=f"fallback_search_{spec.filename}",
                name="web_search",
                arguments={"query": query, "max_results": 5},
            ), requested_by="framework").content
            source_urls = set(self._extract_urls(search_result))

            fetched_pages: list[str] = []
            for index, url in enumerate(sorted(source_urls)[:2], 1):
                fetched = self._dispatch_with_audit(registry, ToolCall(
                    id=f"fallback_fetch_{spec.filename}_{index}",
                    name="fetch_page",
                    arguments={"url": url, "max_chars": 3000},
                ), requested_by="framework").content
                source_urls.update(self._extract_urls(fetched))
                fetched_pages.append(f"## Fetched Page {index}: {url}\n{fetched}")

            content = self._synthesise_skill_from_research(
                game_id=game_id,
                spec=spec,
                llm=llm,
                search_result=search_result,
                fetched_pages=fetched_pages,
                source_urls=source_urls,
            )
            self._audit_event({
                "event": "tool_request",
                "requested_by": "framework",
                "tool": "save_skill",
                "arguments": {"filename": spec.filename, "content_chars": len(content)},
            })
            path.write_text(content + "\n", encoding="utf-8")
            self._audit_event({
                "event": "tool_result",
                "requested_by": "framework",
                "tool": "save_skill",
                "content": f"Saved skill to {path}",
                "is_error": False,
            })
            log.info("fallback skill bootstrap: wrote %d chars to %s", len(content), path)

    def _synthesise_skill_from_research(
        self,
        game_id: str,
        spec: SkillSpec,
        llm: BaseLLM,
        search_result: str,
        fetched_pages: list[str],
        source_urls: set[str],
    ) -> str:
        allowed_sources = "\n".join(f"- {url}" for url in sorted(source_urls))
        research_context = "\n\n".join([search_result, *fetched_pages]).strip()
        correction = ""

        for attempt in range(1, 4):
            prompt = (
                f"Create a raw Markdown skill file for the game `{game_id}`.\n\n"
                f"Filename: {spec.filename}\n"
                f"Topic: {spec.topic}\n"
                f"Success criteria: {spec.success_criteria}\n\n"
                "The framework has already executed web research for you. Do not say "
                "you cannot search, browse, install packages, or access the web. Use "
                "only the research results below as source material.\n\n"
                "Return only raw Markdown. Do not wrap the file in ```markdown fences. "
                "Start with a single top-level # heading. Include concrete tactical "
                "guidance for a turn-by-turn LLM game planner. End with `## Sources` "
                "and cite only URLs from the allowed source list.\n\n"
                f"Allowed source URLs:\n{allowed_sources}\n\n"
                f"Research results:\n{research_context}"
                f"{correction}"
            )
            content = llm.complete(prompt, system=SKILL_BOOTSTRAP_SYSTEM, max_tokens=self._max_tokens)
            try:
                return self._validate_skill_content(
                    content,
                    source_urls=source_urls,
                    require_known_sources=True,
                )
            except ValueError as exc:
                if attempt == 3:
                    raise RuntimeError(
                        f"Generated skill {spec.filename!r} failed validation: {exc}"
                    ) from exc
                correction = (
                    "\n\nYour previous Markdown failed validation: "
                    f"{exc}. Return a corrected raw Markdown file only."
                )

        raise RuntimeError(f"Generated skill {spec.filename!r} failed validation.")

    def _register_save_skill(
        self,
        registry: ToolRegistry,
        game_dir: Path,
        missing: list[SkillSpec],
        source_urls: set[str],
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

            try:
                cleaned = self._validate_skill_content(
                    content,
                    source_urls=source_urls,
                    require_known_sources=self._enable_research,
                )
            except ValueError as exc:
                return f"Error: generated skill failed validation: {exc}"

            path.write_text(cleaned + "\n", encoding="utf-8")
            log.info("save_skill: wrote %d chars to %s", len(cleaned), path)
            return f"Saved skill to {path}"

        registry.register(defn, save_skill)

    def _dispatch_with_audit(
        self,
        registry: ToolRegistry,
        tool_call: ToolCall,
        requested_by: str,
    ):
        self._audit_event({
            "event": "tool_request",
            "requested_by": requested_by,
            "tool": tool_call.name,
            "arguments": self._audit_arguments(tool_call.arguments),
        })
        result = registry.dispatch(tool_call)
        self._audit_event({
            "event": "tool_result",
            "requested_by": requested_by,
            "tool": result.name,
            "content": self._truncate(result.content),
            "is_error": result.content.startswith("Error"),
        })
        return result

    def _audit_event(self, event: dict[str, Any]) -> None:
        if self._audit_log_path is None:
            return
        self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        with self._audit_log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")

    def _audit_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        safe = dict(arguments)
        if "content" in safe:
            content = str(safe["content"])
            safe["content_chars"] = len(content)
            safe["content_preview"] = self._truncate(content, max_chars=500)
            del safe["content"]
        return safe

    def _validate_skill_content(
        self,
        content: str,
        source_urls: set[str],
        require_known_sources: bool,
    ) -> str:
        cleaned = content.strip()
        lowered = cleaned.lower()
        forbidden = [
            "i cannot directly execute web searches",
            "i can not directly execute web searches",
            "i cannot browse",
            "i can't browse",
            "i do not have access to the web",
            "i don't have access to the web",
            "based on the well-known",
            "i have been trained on",
        ]
        for phrase in forbidden:
            if phrase in lowered:
                raise ValueError(f"contains unsupported non-research disclaimer: {phrase!r}")

        if cleaned.startswith("```"):
            raise ValueError("whole-file Markdown fences are not allowed")

        first_line = next((line.strip() for line in cleaned.splitlines() if line.strip()), "")
        if not first_line.startswith("# "):
            raise ValueError("skill must start with a top-level '# ' heading")

        if "## Sources" not in cleaned:
            raise ValueError("skill must include a '## Sources' section")

        sources_section = cleaned.split("## Sources", 1)[1]
        cited_urls = set(self._extract_urls(sources_section))
        if not cited_urls:
            raise ValueError("Sources section must include at least one http(s) URL")

        if require_known_sources:
            if not source_urls:
                raise ValueError("no research URLs were collected before saving")
            if not self._has_known_source(cited_urls, source_urls):
                raise ValueError("Sources section must cite at least one URL from research results")

        return cleaned

    def _has_known_source(self, cited_urls: set[str], source_urls: set[str]) -> bool:
        known = {self._normalise_url(url) for url in source_urls}
        for cited in cited_urls:
            if self._normalise_url(cited) in known:
                return True
        return False

    def _extract_urls(self, text: str) -> list[str]:
        return [
            self._normalise_url(match)
            for match in re.findall(r"https?://[^\s)\]>]+", text)
        ]

    def _normalise_url(self, url: str) -> str:
        return url.strip().rstrip(".,;:)]}'\"")

    def _truncate(self, text: str, max_chars: int = 2000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + f"\n[… truncated at {max_chars} chars]"

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

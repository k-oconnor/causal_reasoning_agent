from __future__ import annotations

from typing import Any, Sequence

from causal_agent import SkillBootstrapper, SkillSpec


def load_or_bootstrap_skill_docs(
    game_id: str,
    manifest: Sequence[SkillSpec],
    llm: Any | None,
    model_name: str,
    disabled: bool = False,
) -> list[str]:
    """
    Load generated game skills, creating missing ones for real LLM evals.

    Mock runs skip the bootstrap entirely so smoke tests remain offline and
    key-free.
    """
    if disabled or llm is None or model_name == "mock":
        return []
    return SkillBootstrapper().ensure_skills(game_id, list(manifest), llm)

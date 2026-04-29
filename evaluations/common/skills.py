from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from causal_agent import SkillBootstrapper, SkillSpec


def load_or_bootstrap_skill_docs(
    game_id: str,
    manifest: Sequence[SkillSpec],
    llm: Any | None,
    model_name: str,
    disabled: bool = False,
    log_dir: str | Path | None = None,
) -> list[str]:
    """
    Load generated game skills, creating missing ones for real LLM evals.

    Mock runs skip the bootstrap entirely so smoke tests remain offline and
    key-free.
    """
    if disabled or llm is None or model_name == "mock":
        return []
    audit_log_path = (Path(log_dir) / "skill_bootstrap.jsonl") if log_dir else None
    return SkillBootstrapper(audit_log_path=audit_log_path).ensure_skills(
        game_id,
        list(manifest),
        llm,
    )

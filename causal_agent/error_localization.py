"""Optional Tracer-backed error localization for game evaluations.

The integration is deliberately thin: this module builds a pure Python script
from already-observed turn data, then asks the external Tracer project to audit
that script. Tracer is not vendored into this repository.
"""

from __future__ import annotations

import argparse
import copy
import importlib
import importlib.util
import json
import os
import sys
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from causal_agent.acting import GameAction
from causal_agent.planning import Plan


LOCALIZATION_MODES = ("off", "trace", "feedback")


@dataclass(frozen=True)
class ErrorLocalizationConfig:
    """Runtime settings for optional error localization."""

    mode: str = "off"
    tracer_dir: str | Path | None = None
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    continue_on_error: bool = True

    def __post_init__(self) -> None:
        if self.mode not in LOCALIZATION_MODES:
            raise ValueError(
                f"Unknown localization mode {self.mode!r}; "
                f"expected one of {LOCALIZATION_MODES}."
            )

    @property
    def enabled(self) -> bool:
        return self.mode != "off"


@dataclass
class LocalizationFinding:
    """One localized issue reported by Tracer."""

    lineno: int
    code: str
    error_type: str
    error_message: str
    traceback: str | None = None

    @classmethod
    def from_error_info(cls, value: Any) -> "LocalizationFinding":
        return cls(
            lineno=int(getattr(value, "lineno", 0) or 0),
            code=str(getattr(value, "code", "")),
            error_type=str(getattr(value, "error_type", "")),
            error_message=str(getattr(value, "error_message", "")),
            traceback=getattr(value, "traceback", None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LocalizationResult:
    """Outcome of one localization attempt."""

    mode: str
    script_goal: str
    findings: list[LocalizationFinding] = field(default_factory=list)
    ran: bool = False
    skipped_reason: str = ""
    tracer_dir: str = ""
    error: str = ""

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)

    @property
    def has_logic_error(self) -> bool:
        return any("logic" in finding.error_type.lower() for finding in self.findings)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    def summary(self) -> str:
        if self.skipped_reason:
            return f"error localization skipped: {self.skipped_reason}"
        if self.error:
            return f"error localization failed: {self.error}"
        if not self.findings:
            return "error localization found no issues"
        return "; ".join(
            f"line {finding.lineno}: {finding.error_type} - {finding.error_message}"
            for finding in self.findings
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "script_goal": self.script_goal,
            "ran": self.ran,
            "skipped_reason": self.skipped_reason,
            "tracer_dir": self.tracer_dir,
            "error": self.error,
            "finding_count": self.finding_count,
            "has_logic_error": self.has_logic_error,
            "findings": [finding.to_dict() for finding in self.findings],
        }


FakeTracerRunner = Callable[[str, str, ErrorLocalizationConfig], Any]


class TracerAdapter:
    """Adapter for the external Yungxi/Tracer project."""

    _REQUIRED_FILES = ("parser.py", "executor.py", "judge.py", "reporter.py")
    _REQUIRED_MODULES = ("parser", "executor", "judge", "reporter")

    def __init__(
        self,
        config: ErrorLocalizationConfig | None = None,
        *,
        runner: FakeTracerRunner | None = None,
    ) -> None:
        self.config = config or ErrorLocalizationConfig()
        self._runner = runner

    def resolve_tracer_dir(self) -> Path | None:
        """Return Tracer's directory, or None when modules are already importable."""
        if self.config.tracer_dir:
            path = Path(self.config.tracer_dir).expanduser().resolve()
            if self._looks_like_tracer_dir(path):
                return path
            raise FileNotFoundError(f"Tracer not found at {path}")

        env_dir = os.environ.get("TRACER_DIR")
        if env_dir:
            path = Path(env_dir).expanduser().resolve()
            if self._looks_like_tracer_dir(path):
                return path
            raise FileNotFoundError(f"TRACER_DIR does not point to Tracer: {path}")

        for raw in sys.path:
            if not raw:
                continue
            path = Path(raw).expanduser().resolve()
            if self._looks_like_tracer_dir(path):
                return path

        project_root = Path(__file__).resolve().parents[1]
        for path in (
            project_root / "materials" / "Tracer",
            project_root.parent / "materials" / "Tracer",
            project_root / "Tracer",
            project_root / "error_localization" / "Tracer",
            Path.cwd() / "materials" / "Tracer",
            Path.cwd().parent / "materials" / "Tracer",
        ):
            path = path.expanduser().resolve()
            if self._looks_like_tracer_dir(path):
                return path

        if self._modules_importable():
            return None

        raise FileNotFoundError(
            "Tracer modules were not found. Set --tracer-dir or TRACER_DIR, "
            "or add Tracer to PYTHONPATH."
        )

    def audit_script(self, source: str, script_goal: str) -> LocalizationResult:
        """Run Tracer on a generated script, returning a serializable result."""
        if not self.config.enabled:
            return LocalizationResult(
                mode=self.config.mode,
                script_goal=script_goal,
                skipped_reason="localization mode is off",
            )

        if self._runner is not None:
            return self._coerce_runner_result(self._runner(source, script_goal, self.config), script_goal)

        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return LocalizationResult(
                mode=self.config.mode,
                script_goal=script_goal,
                skipped_reason="OPENAI_API_KEY is not set for Tracer's LLMJudge",
            )

        try:
            tracer_dir = self.resolve_tracer_dir()
        except FileNotFoundError as exc:
            return LocalizationResult(
                mode=self.config.mode,
                script_goal=script_goal,
                skipped_reason=str(exc),
            )

        try:
            with _temporary_sys_path(tracer_dir):
                parse_source = importlib.import_module("parser").parse_source
                tracing_executor = importlib.import_module("executor").TracingExecutor
                llm_judge = importlib.import_module("judge").LLMJudge

                parsed = parse_source(source)
                judge_kwargs: dict[str, Any] = {
                    "api_key": api_key,
                    "script_goal": script_goal,
                }
                if self.config.model:
                    judge_kwargs["model"] = self.config.model
                judge = llm_judge(**judge_kwargs)
                executor = tracing_executor(
                    parsed,
                    judge=judge,
                    continue_on_error=self.config.continue_on_error,
                )
                raw_result = executor.execute()
        except Exception as exc:
            return LocalizationResult(
                mode=self.config.mode,
                script_goal=script_goal,
                error=f"{type(exc).__name__}: {exc}",
            )

        return LocalizationResult(
            mode=self.config.mode,
            script_goal=script_goal,
            ran=True,
            tracer_dir=str(tracer_dir or ""),
            findings=[
                LocalizationFinding.from_error_info(error)
                for error in getattr(raw_result, "errors", [])
            ],
        )

    def _coerce_runner_result(self, raw: Any, script_goal: str) -> LocalizationResult:
        if isinstance(raw, LocalizationResult):
            return raw

        findings: Iterable[Any]
        if isinstance(raw, Mapping):
            findings = raw.get("findings", [])
            return LocalizationResult(
                mode=str(raw.get("mode", self.config.mode)),
                script_goal=str(raw.get("script_goal", script_goal)),
                findings=[_coerce_finding(item) for item in findings],
                ran=bool(raw.get("ran", True)),
                skipped_reason=str(raw.get("skipped_reason", "")),
                tracer_dir=str(raw.get("tracer_dir", "")),
                error=str(raw.get("error", "")),
            )

        if hasattr(raw, "errors"):
            findings = getattr(raw, "errors")
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            findings = raw
        else:
            findings = []

        return LocalizationResult(
            mode=self.config.mode,
            script_goal=script_goal,
            findings=[_coerce_finding(item) for item in findings],
            ran=True,
        )

    @classmethod
    def _looks_like_tracer_dir(cls, path: Path) -> bool:
        return path.is_dir() and all((path / filename).exists() for filename in cls._REQUIRED_FILES)

    @classmethod
    def _modules_importable(cls) -> bool:
        return all(importlib.util.find_spec(name) is not None for name in cls._REQUIRED_MODULES)


def add_error_localization_args(parser: argparse.ArgumentParser) -> None:
    """Add shared CLI flags for optional Tracer integration."""
    parser.add_argument("--localization", choices=LOCALIZATION_MODES, default="off")
    parser.add_argument("--tracer-dir", default=None)
    parser.add_argument("--tracer-model", default="gpt-4o-mini")
    parser.add_argument("--tracer-openai-key", default=None)


def config_from_args(args: argparse.Namespace) -> ErrorLocalizationConfig:
    return ErrorLocalizationConfig(
        mode=args.localization,
        tracer_dir=args.tracer_dir,
        api_key=args.tracer_openai_key,
        model=args.tracer_model,
        continue_on_error=True,
    )


def build_turn_audit_script(
    *,
    game: str,
    turn: int,
    goal: str,
    observation: Mapping[str, Any],
    plan: Plan | Mapping[str, Any],
    action: GameAction | Mapping[str, Any],
    agent_id: str = "Agent",
    feedback: Mapping[str, Any] | None = None,
    legal_actions: Sequence[str] | None = None,
    planner_trace: Mapping[str, Any] | None = None,
) -> str:
    """Build a pure ToyAgent-style script from observed turn data."""
    payload = {
        "game": game,
        "turn": turn,
        "goal": goal,
        "agent_id": agent_id,
        "observation": sanitize_observation(observation, agent_id=agent_id),
        "plan": _plan_to_dict(plan),
        "action": _action_to_dict(action),
        "feedback": sanitize_observation(feedback or {}, agent_id=agent_id) if feedback else None,
        "legal_actions": list(legal_actions or []),
        "planner_trace": _jsonable(planner_trace or {}),
    }
    state_json = json.dumps(payload, sort_keys=True, default=str)
    state_literal = repr(state_json)

    return f'''# Auto-generated turn audit for Tracer.
# Game: {game}
# Turn: {turn}
# Goal: {goal}

import json


state = json.loads({state_literal})


def prepare_turn_packet(state):
    """Build the compact public packet used by the later audit steps."""
    observation = state["observation"]
    return {{
        "goal": state["goal"],
        "agent_id": state["agent_id"],
        "phase": observation.get("phase", ""),
        "alive_players": observation.get("alive_players", []),
        "recent_public_log": observation.get("public_log", []),
        "plan": state["plan"],
        "action": state["action"],
        "feedback": state.get("feedback"),
        "legal_actions": state.get("legal_actions", []),
    }}


def inspect_plan(packet):
    """Validate basic consistency between the proposed plan, action, and legal actions."""
    legal_actions = packet.get("legal_actions", [])
    action = packet["action"]
    payload = action.get("payload", {{}})
    plan = packet["plan"]
    issues = []
    if plan.get("action_type", "") not in legal_actions:
        issues.append("plan action_type is not legal for this turn")
    if action.get("action_type", "") != plan.get("action_type", ""):
        issues.append("planned action_type differs from submitted action")
    if plan.get("parameters", {{}}) != payload:
        issues.append("planned parameters differ from submitted action payload")
    if not str(plan.get("intent", "")).strip():
        issues.append("plan has no intent")
    if not str(plan.get("reasoning", "")).strip():
        issues.append("plan has no public rationale")
    packet["plan_check"] = {{
        "intent": plan.get("intent", ""),
        "action_type": plan.get("action_type", ""),
        "parameters": plan.get("parameters", {{}}),
        "reasoning": plan.get("reasoning", ""),
        "phase": packet.get("phase", ""),
        "issues": issues,
        "ok": not issues,
    }}
    return packet


def inspect_action(packet):
    """Validate basic legality and payload shape for the selected action."""
    action = packet["action"]
    payload = action.get("payload", {{}})
    target = payload.get("target", "")
    legal_actions = packet.get("legal_actions", [])
    alive_players = packet.get("alive_players", [])
    issues = []
    if action.get("action_type", "") not in legal_actions:
        issues.append("submitted action_type is not legal for this turn")
    if "message" in payload and not str(payload.get("message", "")).strip():
        issues.append("speech action has an empty message")
    if target and (target not in alive_players or target == packet["agent_id"]):
        issues.append("target is not a living non-self player")
    packet["action_check"] = {{
        "action_type": action.get("action_type", ""),
        "payload": payload,
        "is_legal_action_type": action.get("action_type", "") in legal_actions,
        "target": target,
        "target_is_alive_other_player": bool(target) and target in alive_players and target != packet["agent_id"],
        "message_non_empty": bool(str(payload.get("message", "")).strip()) if "message" in payload else True,
        "phase": packet.get("phase", ""),
        "issues": issues,
        "ok": not issues,
    }}
    return packet


def inspect_feedback(packet):
    """Summarize whether the environment accepted the submitted action."""
    feedback = packet.get("feedback") or {{}}
    issues = []
    if feedback.get("kind", "") == "illegal_move":
        issues.append("environment rejected the action as illegal")
    packet["feedback_check"] = {{
        "kind": feedback.get("kind", ""),
        "content": feedback.get("content", ""),
        "reward": feedback.get("reward", 0.0),
        "terminal": feedback.get("terminal", False),
        "issues": issues,
        "ok": not issues,
    }}
    return packet


packet = prepare_turn_packet(state)
packet = inspect_plan(packet)
packet = inspect_action(packet)
if packet.get("feedback") is not None:
    packet = inspect_feedback(packet)
print("final:", json.dumps({{
    "plan_check": packet.get("plan_check", {{}}),
    "action_check": packet.get("action_check", {{}}),
    "feedback_check": packet.get("feedback_check", {{}}),
}}, sort_keys=True))
'''


def localization_goal(game: str, agent_goal: str) -> str:
    return (
        f"Audit one {game} turn for the agent goal: {agent_goal}. "
        "A correct turn should use only the observed state, choose a legal action, "
        "and keep the agent on track for the win condition."
    )


def sanitize_observation(value: Mapping[str, Any], *, agent_id: str = "Agent") -> dict[str, Any]:
    """Remove private role facts that should not be sent to Tracer."""
    clean = _jsonable(value)
    if not isinstance(clean, dict):
        return {}

    facts = clean.get("facts")
    if isinstance(facts, dict):
        clean["facts"] = {
            key: fact_value
            for key, fact_value in facts.items()
            if not (str(key).startswith("role_") and str(key) != f"role_{agent_id}")
        }

    for key in list(clean):
        lowered = str(key).lower()
        if lowered in {"secret", "roles", "role_assignments"}:
            clean.pop(key, None)
    return clean


def _coerce_finding(value: Any) -> LocalizationFinding:
    if isinstance(value, LocalizationFinding):
        return value
    if isinstance(value, Mapping):
        return LocalizationFinding(
            lineno=int(value.get("lineno", 0) or 0),
            code=str(value.get("code", "")),
            error_type=str(value.get("error_type", "")),
            error_message=str(value.get("error_message", "")),
            traceback=value.get("traceback"),
        )
    return LocalizationFinding.from_error_info(value)


def _plan_to_dict(plan: Plan | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(plan, Mapping):
        return _jsonable(plan)
    return {
        "intent": plan.intent,
        "action_type": plan.action_type,
        "parameters": _jsonable(plan.parameters),
        "reasoning": plan.reasoning,
        "supporting_worlds": list(plan.supporting_worlds),
        "intervention_notes": list(plan.intervention_notes),
    }


def _action_to_dict(action: GameAction | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(action, Mapping):
        return _jsonable(action)
    return {
        "action_type": action.action_type,
        "payload": _jsonable(action.payload),
        "agent_id": action.agent_id,
    }


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    try:
        json.dumps(value)
        return copy.deepcopy(value)
    except TypeError:
        return str(value)


class _temporary_sys_path:
    def __init__(self, path: Path | None) -> None:
        self.path = str(path) if path else ""
        self._original: list[str] = []

    def __enter__(self) -> None:
        self._original = list(sys.path)
        if self.path and self.path not in sys.path:
            sys.path.insert(0, self.path)

    def __exit__(self, exc_type, exc, traceback) -> None:
        sys.path[:] = self._original

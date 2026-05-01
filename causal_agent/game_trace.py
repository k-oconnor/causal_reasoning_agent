"""Live game sessions with safe, public-facing decision traces."""

from __future__ import annotations

import copy
import json
import math
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from causal_agent.acting import ActionError, Actor, GameAction
from causal_agent.feedback import FeedbackProcessor
from causal_agent.llm import BaseLLM, MockLLM
from causal_agent.memory import MemoryEntry, MemoryStore
from causal_agent.planning import Plan, Planner
from games.game_2048 import Game2048Env
from games.mastermind import MastermindEnv


DEFAULT_MASTERMIND_COLORS = ("red", "blue", "green", "yellow", "orange", "purple")

_MOCK_2048_RESPONSES = [
    '{"intent": "merge while preserving space", "action_type": "slide", '
    '"parameters": {"direction": "left"}, "public_rationale": "Move tiles toward an edge."}',
    '{"intent": "stack tiles upward", "action_type": "slide", '
    '"parameters": {"direction": "up"}, "public_rationale": "Keep the board compact."}',
    '{"intent": "seek immediate merges", "action_type": "slide", '
    '"parameters": {"direction": "right"}, "public_rationale": "Try the opposite merge lane."}',
    '{"intent": "rebalance columns", "action_type": "slide", '
    '"parameters": {"direction": "down"}, "public_rationale": "Open space for future tiles."}',
]

_MOCK_MASTERMIND_RESPONSES = [
    '{"intent": "test a broad color set", "action_type": "guess", '
    '"parameters": {"code": ["red", "blue", "green", "yellow"]}, '
    '"public_rationale": "Start with four distinct colors to split the candidate set."}',
    '{"intent": "probe the remaining colors", "action_type": "guess", '
    '"parameters": {"code": ["orange", "purple", "red", "blue"]}, '
    '"public_rationale": "Combine new colors with known probes."}',
    '{"intent": "try a plausible candidate", "action_type": "guess", '
    '"parameters": {"code": ["green", "yellow", "orange", "purple"]}, '
    '"public_rationale": "Use feedback to narrow the code."}',
]


@dataclass(frozen=True)
class GameRunConfig:
    """Configuration for one live dashboard session."""

    game: str = "2048"
    seed: int = 7
    max_turns: int = 100
    size: int = 4
    mastermind_colors: tuple[str, ...] = DEFAULT_MASTERMIND_COLORS
    mastermind_code_length: int = 4
    mastermind_max_attempts: int = 10
    mastermind_duplicates_allowed: bool = True
    mastermind_secret: tuple[str, ...] | None = None
    simulate_before_plan: bool = False
    max_tool_calls: int = 8
    log_dir: str | None = None
    log_filename: str | None = None
    episode: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "GameRunConfig":
        data = dict(data or {})
        colors = data.get("mastermind_colors", data.get("colors", DEFAULT_MASTERMIND_COLORS))
        if isinstance(colors, str):
            colors = tuple(part.strip() for part in colors.split(",") if part.strip())
        else:
            colors = tuple(str(color) for color in colors)

        secret = data.get("mastermind_secret", data.get("secret"))
        if isinstance(secret, str):
            secret = tuple(part.strip() for part in secret.split(",") if part.strip())
        elif secret is not None:
            secret = tuple(str(color) for color in secret)

        return cls(
            game=_normalise_game(data.get("game", "2048")),
            seed=int(data.get("seed", 7)),
            max_turns=int(data.get("max_turns", data.get("maxTurns", 100))),
            size=int(data.get("size", 4)),
            mastermind_colors=colors or DEFAULT_MASTERMIND_COLORS,
            mastermind_code_length=int(data.get("mastermind_code_length", data.get("code_length", 4))),
            mastermind_max_attempts=int(data.get("mastermind_max_attempts", data.get("max_attempts", 10))),
            mastermind_duplicates_allowed=bool(
                data.get("mastermind_duplicates_allowed", data.get("duplicates_allowed", True))
            ),
            mastermind_secret=secret,
            simulate_before_plan=bool(data.get("simulate_before_plan", False)),
            max_tool_calls=int(data.get("max_tool_calls", 8)),
            log_dir=data.get("log_dir"),
            log_filename=data.get("log_filename"),
            episode=int(data.get("episode", 0)),
        )


@dataclass
class TurnTrace:
    """One completed decision turn for the dashboard timeline."""

    turn: int
    game: str
    observation: str
    state_before: dict[str, Any]
    legal_options: list[dict[str, Any]]
    planner_trace: dict[str, Any]
    action: dict[str, Any] | None
    action_analysis: dict[str, Any]
    feedback: dict[str, Any]
    state_after: dict[str, Any]
    terminal: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "game": self.game,
            "observation": self.observation,
            "state_before": copy.deepcopy(self.state_before),
            "legal_options": copy.deepcopy(self.legal_options),
            "planner_trace": copy.deepcopy(self.planner_trace),
            "action": copy.deepcopy(self.action),
            "action_analysis": copy.deepcopy(self.action_analysis),
            "feedback": copy.deepcopy(self.feedback),
            "state_after": copy.deepcopy(self.state_after),
            "terminal": self.terminal,
        }


class GameThoughtSession:
    """Run 2048 or Mastermind one turn at a time and expose safe traces."""

    def __init__(
        self,
        config: GameRunConfig | None = None,
        llm: BaseLLM | None = None,
        *,
        agent_id: str = "Agent",
        model_label: str | None = None,
    ) -> None:
        self.config = config or GameRunConfig()
        self.game = _normalise_game(self.config.game)
        self.agent_id = agent_id
        self.env = self._build_env()
        self.llm = llm or MockLLM(mock_responses_for_game(self.game))
        self.model_label = model_label or repr(self.llm)
        self.actor = Actor()
        self.feedback_processor = FeedbackProcessor()
        self.memory = MemoryStore(max_short_term=80)
        self.kripke = self.env.initial_kripke(agent_id)
        self.planner = Planner(
            self.llm,
            simulate_before_plan=self.config.simulate_before_plan,
            system=self.env.system_prompt(),
            tools=self.env.tools(agent_id),
            preview=self.env.preview,
            max_tool_calls=self.config.max_tool_calls,
        )
        self.turn = 0
        self.history: list[TurnTrace] = []
        self.log_path = self._prepare_log_path()

    def snapshot(self) -> dict[str, Any]:
        """Return the current safe UI state."""
        return {
            "game": self.game,
            "seed": self.config.seed,
            "max_turns": self.config.max_turns,
            "turn": self.turn,
            "terminal": self.env.is_terminal,
            "stopped": self.turn >= self.config.max_turns,
            "model": self.model_label,
            "latest_act": self.history[-1].action if self.history else None,
            "latest_trace": self.history[-1].to_dict() if self.history else None,
            "log_path": str(self.log_path) if self.log_path else "",
            "state": self._safe_state(),
            "history": [trace.to_dict() for trace in self.history],
        }

    def update_max_turns(self, max_turns: int) -> None:
        """Update the turn cap for the existing session."""
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1.")
        self.config = replace(self.config, max_turns=max_turns)

    def resume_from_records(self, records: Sequence[dict[str, Any]]) -> None:
        """Replay logged actions to restore a session without calling the LLM."""
        for record in records:
            action = _action_from_log_record(record, self.game, self.agent_id)
            if action is None:
                continue

            turn = int(record.get("turn", self.turn))
            obs = self.env.observe(self.agent_id)
            state_before = self._safe_state(obs)
            legal_options = copy.deepcopy(record.get("legal_options") or self._legal_options())
            action_analysis = copy.deepcopy(record.get("action_analysis") or {})
            if not action_analysis:
                action_analysis = self._action_analysis(action)

            feedback = self.env.step(self.agent_id, action)
            state_after = self._safe_state()
            if "score_delta" not in action_analysis and "candidate_count_after" not in action_analysis:
                action_analysis.update(self._after_action_analysis(state_before, state_after, action))

            planner_trace = copy.deepcopy(record.get("planner_trace") or {
                "decision": {
                    "intent": record.get("intent", ""),
                    "public_rationale": record.get("rationale", ""),
                },
                "tool_calls": [],
                "preview_notes": [],
                "intervention_notes": [],
                "parse_errors": [],
            })
            trace = TurnTrace(
                turn=turn,
                game=self.game,
                observation=str(record.get("observation", obs.get("content", ""))),
                state_before=state_before,
                legal_options=legal_options,
                planner_trace=planner_trace,
                action=_action_to_dict(action),
                action_analysis=action_analysis,
                feedback=_feedback_from_log_record(record, feedback),
                state_after=state_after,
                terminal=bool(record.get("terminal", self.env.is_terminal)),
            )
            self.history.append(trace)
            self.turn = max(self.turn, turn + 1)

            facts = obs.get("facts", {})
            if facts:
                self.kripke = self.kripke.update_with_facts(facts)
            feedback_facts = feedback.get("facts", {})
            if feedback_facts:
                self.kripke = self.kripke.update_with_facts(feedback_facts)
            self.memory.add(MemoryEntry(
                turn=turn,
                kind="resumed",
                source="log",
                content=str(record.get("feedback", feedback.get("content", ""))),
                metadata={"action": _action_to_dict(action), "state": state_after},
            ))

    def step(self) -> dict[str, Any] | None:
        """Advance one agent decision and return its trace."""
        if self.env.is_terminal or self.turn >= self.config.max_turns:
            return None

        obs = self.env.observe(self.agent_id)
        if obs.get("terminal"):
            return None

        state_before = self._safe_state(obs)
        legal_options = self._legal_options()
        action_specs = self.env.action_specs(self.agent_id)
        if not action_specs:
            return None

        event = self.feedback_processor.process(obs, self.turn)
        self.memory.add(MemoryEntry(
            turn=self.turn,
            kind=event.kind.value,
            source=event.source,
            content=event.content,
            metadata={
                "facts": event.facts,
                "state": state_before,
                "legal_options": legal_options,
            },
        ))
        if event.facts:
            self.kripke = self.kripke.update_with_facts(event.facts)
        self.memory.snapshot_kripke(self.turn, self.kripke)

        plan = self.planner.plan(
            kripke=self.kripke,
            memory=self.memory,
            goal=self._goal(),
            agent_id=self.agent_id,
            action_specs=action_specs,
        )
        action, actor_error = self._act(plan, action_specs)
        action_analysis = self._action_analysis(action)
        feedback = self.env.step(self.agent_id, action)
        self.memory.add(MemoryEntry(
            turn=self.turn,
            kind="action",
            source=self.agent_id,
            content=str(action),
            metadata={"actor_error": actor_error} if actor_error else {},
        ))

        state_after = self._safe_state()
        action_analysis.update(self._after_action_analysis(state_before, state_after, action))
        planner_trace = self.planner.last_trace
        if actor_error:
            planner_trace["actor_error"] = actor_error

        trace = TurnTrace(
            turn=self.turn,
            game=self.game,
            observation=str(obs.get("content", "")),
            state_before=state_before,
            legal_options=legal_options,
            planner_trace=planner_trace,
            action=_action_to_dict(action),
            action_analysis=action_analysis,
            feedback={
                "kind": str(feedback.get("kind", "")),
                "content": str(feedback.get("content", "")),
                "reward": float(feedback.get("reward", 0.0)),
                "terminal": bool(feedback.get("terminal", False)),
            },
            state_after=state_after,
            terminal=self.env.is_terminal,
        )
        self.history.append(trace)
        self._append_jsonl(trace)
        self.turn += 1
        return trace.to_dict()

    def _build_env(self):
        if self.game == "2048":
            return Game2048Env(
                size=self.config.size,
                seed=self.config.seed,
                agent_id=self.agent_id,
            )
        if self.game == "mastermind":
            return MastermindEnv(
                colors=self.config.mastermind_colors,
                code_length=self.config.mastermind_code_length,
                max_attempts=self.config.mastermind_max_attempts,
                duplicates_allowed=self.config.mastermind_duplicates_allowed,
                seed=self.config.seed,
                secret=self.config.mastermind_secret,
                agent_id=self.agent_id,
            )
        raise ValueError(f"Unsupported game: {self.config.game!r}")

    def _goal(self) -> str:
        if self.game == "2048":
            return (
                "Play 2048 well: maximize score, preserve empty cells, build larger "
                "tiles, and avoid terminal boards."
            )
        return (
            "Solve Mastermind: infer the hidden code from exact and partial feedback "
            "while using as few guesses as possible."
        )

    def _act(self, plan: Plan, action_specs) -> tuple[GameAction, str]:
        try:
            return self.actor.act(plan, action_specs, self.agent_id), ""
        except ActionError as exc:
            fallback_spec = action_specs[0]
            fallback = Plan(
                intent="fallback after invalid action",
                action_type=fallback_spec.action_type,
                parameters=fallback_spec.fallback_payload(),
                reasoning="Actor rejected the planned action; using the first legal example.",
            )
            return self.actor.act(fallback, action_specs, self.agent_id), str(exc)

    def _safe_state(self, obs: dict[str, Any] | None = None) -> dict[str, Any]:
        obs = obs or self.env.observe(self.agent_id)
        if self.game == "2048":
            board = obs.get("board", self.env.board)
            return {
                "board": copy.deepcopy(board),
                "score": int(obs.get("score", self.env.score)),
                "max_tile": max((value for row in board for value in row), default=0),
                "legal_directions": list(obs.get("legal_directions", [])),
                "terminal": bool(obs.get("terminal", self.env.is_terminal)),
            }

        history = copy.deepcopy(obs.get("history", self.env.history))
        state = {
            "colors": list(self.config.mastermind_colors),
            "code_length": self.config.mastermind_code_length,
            "max_attempts": self.config.mastermind_max_attempts,
            "attempts_remaining": int(obs.get("attempts_remaining", 0)),
            "duplicates_allowed": self.config.mastermind_duplicates_allowed,
            "history": history,
            "candidate_count": _mastermind_candidate_count(
                self.config.mastermind_colors,
                self.config.mastermind_code_length,
                self.config.mastermind_duplicates_allowed,
                history,
            ),
            "solved": bool(obs.get("facts", {}).get("solved", False)),
            "terminal": bool(obs.get("terminal", self.env.is_terminal)),
        }
        if state["terminal"]:
            state["secret"] = self.env.secret
        return state

    def _legal_options(self) -> list[dict[str, Any]]:
        if self.game == "2048":
            options = []
            for direction in self.env.observe(self.agent_id).get("legal_directions", []):
                preview = self.env.preview(
                    self.agent_id,
                    GameAction("slide", {"direction": direction}, self.agent_id),
                ) or {"direction": direction}
                options.append(preview)
            return options

        spec = self.env.action_specs(self.agent_id)[0]
        candidate_count = _mastermind_candidate_count(
            self.config.mastermind_colors,
            self.config.mastermind_code_length,
            self.config.mastermind_duplicates_allowed,
            self.env.history,
        )
        return [
            {
                "action_type": spec.action_type,
                "example": copy.deepcopy(example),
                "candidate_count": candidate_count,
            }
            for example in spec.examples
        ]

    def _action_analysis(self, action: GameAction) -> dict[str, Any]:
        if self.game == "2048":
            preview = self.env.preview(self.agent_id, action) or {}
            return {"preview": preview}

        guess = action.payload.get("code", [])
        return {
            "candidate_count_before": _mastermind_candidate_count(
                self.config.mastermind_colors,
                self.config.mastermind_code_length,
                self.config.mastermind_duplicates_allowed,
                self.env.history,
            ),
            "chosen_guess_info": _mastermind_expected_information(
                self.config.mastermind_colors,
                self.config.mastermind_code_length,
                self.config.mastermind_duplicates_allowed,
                self.env.history,
                guess,
            ),
        }

    def _after_action_analysis(
        self,
        state_before: dict[str, Any],
        state_after: dict[str, Any],
        action: GameAction,
    ) -> dict[str, Any]:
        if self.game == "2048":
            return {
                "score_delta": state_after.get("score", 0) - state_before.get("score", 0),
                "empty_cells_after": sum(
                    1 for row in state_after.get("board", []) for value in row if value == 0
                ),
            }
        return {"candidate_count_after": state_after.get("candidate_count", 0)}

    def _prepare_log_path(self) -> Path | None:
        if not self.config.log_dir:
            return None

        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        filename = self.config.log_filename or (
            f"episode_{self.config.episode:04d}_llm_seed_{self.config.seed}.jsonl"
        )
        path = log_dir / filename
        if path.exists() and path.stat().st_size > 0:
            path = _unique_log_path(path)
        path.write_text("")
        return path

    def _append_jsonl(self, trace: TurnTrace) -> None:
        if self.log_path is None:
            return

        with self.log_path.open("a") as handle:
            handle.write(json.dumps(self._jsonl_record(trace), default=str) + "\n")

    def _jsonl_record(self, trace: TurnTrace) -> dict[str, Any]:
        record: dict[str, Any] = {
            "episode": self.config.episode,
            "turn": trace.turn,
            "seed": self.config.seed,
            "policy": "llm",
            "game": self.game,
            "model": self.model_label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "observation": trace.observation,
            "legal_options": trace.legal_options,
            "action": trace.action,
            "feedback": trace.feedback["content"],
            "feedback_event": trace.feedback,
            "intent": trace.planner_trace.get("decision", {}).get("intent", ""),
            "rationale": trace.planner_trace.get("decision", {}).get("public_rationale", ""),
            "planner_trace": trace.planner_trace,
            "action_analysis": trace.action_analysis,
            "terminal": trace.terminal,
        }

        if self.game == "2048":
            record.update({
                "board_before": trace.state_before.get("board", []),
                "legal_directions": trace.state_before.get("legal_directions", []),
                "action_direction": (
                    trace.action.get("payload", {}).get("direction")
                    if trace.action else ""
                ),
                "board_after": trace.state_after.get("board", []),
                "score": trace.state_after.get("score", 0),
                "max_tile": trace.state_after.get("max_tile", 0),
            })
        else:
            latest_history = trace.state_after.get("history", [])
            latest_feedback = latest_history[-1] if latest_history else {}
            record.update({
                "colors": list(self.config.mastermind_colors),
                "code_length": self.config.mastermind_code_length,
                "max_attempts": self.config.mastermind_max_attempts,
                "duplicates_allowed": self.config.mastermind_duplicates_allowed,
                "secret": self.env.secret,
                "guess": (
                    trace.action.get("payload", {}).get("code", [])
                    if trace.action else []
                ),
                "exact": latest_feedback.get("exact", 0),
                "partial": latest_feedback.get("partial", 0),
                "remaining_candidates_before": trace.state_before.get("candidate_count", 0),
                "remaining_candidates_after": trace.state_after.get("candidate_count", 0),
                "solved": bool(trace.state_after.get("solved", False)),
            })

        return record


def mock_responses_for_game(game: str) -> list[str]:
    if _normalise_game(game) == "mastermind":
        return list(_MOCK_MASTERMIND_RESPONSES)
    return list(_MOCK_2048_RESPONSES)


def _normalise_game(raw: Any) -> str:
    game = str(raw or "2048").lower().replace("_", "-")
    if game in {"2048", "game-2048"}:
        return "2048"
    if game in {"mastermind", "master-mind"}:
        return "mastermind"
    raise ValueError(f"Unsupported game: {raw!r}")


def _action_to_dict(action: GameAction) -> dict[str, Any]:
    return {
        "action_type": action.action_type,
        "payload": copy.deepcopy(action.payload),
        "agent_id": action.agent_id,
    }


def _action_from_log_record(
    record: dict[str, Any],
    game: str,
    agent_id: str,
) -> GameAction | None:
    action = record.get("action")
    if isinstance(action, dict):
        action_type = str(action.get("action_type") or ("guess" if game == "mastermind" else "slide"))
        payload = copy.deepcopy(action.get("payload") or {})
        return GameAction(action_type, payload, str(action.get("agent_id", agent_id)))

    if game == "2048":
        direction = record.get("action_direction") or record.get("direction")
        if direction is None and isinstance(action, str):
            direction = action
        if direction:
            return GameAction("slide", {"direction": str(direction)}, agent_id)
        return None

    guess = record.get("guess")
    if guess is None and isinstance(action, list):
        guess = action
    if guess is not None:
        return GameAction("guess", {"code": list(guess)}, agent_id)
    return None


def _feedback_from_log_record(record: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    event = copy.deepcopy(record.get("feedback_event") or {})
    if not event:
        event = {
            "kind": str(fallback.get("kind", "")),
            "content": str(record.get("feedback", fallback.get("content", ""))),
            "reward": float(fallback.get("reward", 0.0)),
            "terminal": bool(record.get("terminal", fallback.get("terminal", False))),
        }
    event.setdefault("kind", str(fallback.get("kind", "")))
    event.setdefault("content", str(record.get("feedback", fallback.get("content", ""))))
    event.setdefault("reward", float(fallback.get("reward", 0.0)))
    event.setdefault("terminal", bool(record.get("terminal", fallback.get("terminal", False))))
    return event


def _unique_log_path(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{stamp}_{counter}{path.suffix}")
        counter += 1
    return candidate


def _mastermind_candidate_count(
    colors: Sequence[str],
    code_length: int,
    duplicates_allowed: bool,
    history: Sequence[dict[str, Any]],
) -> int:
    return len(_mastermind_candidates(colors, code_length, duplicates_allowed, history))


def _mastermind_candidates(
    colors: Sequence[str],
    code_length: int,
    duplicates_allowed: bool,
    history: Sequence[dict[str, Any]],
) -> list[tuple[str, ...]]:
    from causal_agent.mastermind_tools import generate_all_codes, score_guess

    candidates = generate_all_codes(colors, code_length, duplicates_allowed)
    for record in history:
        guess = tuple(str(symbol) for symbol in record.get("guess", []))
        feedback = (int(record.get("exact", 0)), int(record.get("partial", 0)))
        candidates = [
            code for code in candidates
            if score_guess(guess, code) == feedback
        ]
    return candidates


def _mastermind_expected_information(
    colors: Sequence[str],
    code_length: int,
    duplicates_allowed: bool,
    history: Sequence[dict[str, Any]],
    guess: Sequence[str],
) -> dict[str, Any]:
    from causal_agent.mastermind_tools import score_guess

    guess_tuple = tuple(str(symbol) for symbol in guess)
    candidates = _mastermind_candidates(colors, code_length, duplicates_allowed, history)
    if not candidates or len(guess_tuple) != code_length:
        return {
            "guess": list(guess_tuple),
            "candidate_count": len(candidates),
            "expected_information_bits": 0.0,
            "expected_remaining": 0.0,
            "is_candidate": False,
        }

    partitions: dict[tuple[int, int], int] = defaultdict(int)
    for code in candidates:
        partitions[score_guess(guess_tuple, code)] += 1

    total = len(candidates)
    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in partitions.values()
    )
    expected_remaining = sum((count / total) * count for count in partitions.values())
    largest_partition = max(partitions.values()) if partitions else 0
    sorted_partitions = sorted(partitions.items(), key=lambda item: item[1], reverse=True)

    return {
        "guess": list(guess_tuple),
        "candidate_count": total,
        "expected_information_bits": round(entropy, 4),
        "expected_remaining": round(expected_remaining, 3),
        "largest_partition": largest_partition,
        "is_candidate": guess_tuple in candidates,
        "top_partitions": [
            {"exact": exact, "partial": partial, "count": count}
            for (exact, partial), count in sorted_partitions[:8]
        ],
    }

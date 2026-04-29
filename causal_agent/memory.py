"""
causal_agent/memory.py

Short-term and long-term memory stores, plus lightweight Kripke snapshots.

Short-term  – a fixed-size deque of recent MemoryEntry objects (in-episode).
              Always available for the planner's context window.

Long-term   – an unbounded list of entries persisted across episodes.
              Retrieval is recency-based by default; swap in a vector store
              by subclassing MemoryStore and overriding retrieve().

Kripke snapshots – timestamped summaries of the epistemic model, so the
                   agent can reason about how its beliefs evolved.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from causal_agent.kripke import KripkeModel


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    """One recorded event in the agent's history."""
    turn: int
    kind: str          # mirrors FeedbackKind string values, or "plan", "action"
    source: str        # player name, "env", "self", etc.
    content: str       # human-readable description
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[t={self.turn} | {self.kind} | {self.source}] {self.content}"


@dataclass
class KripkeSnapshot:
    """
    Lightweight snapshot of a KripkeModel state at a given turn.

    Stores the world count and the certain/uncertain fact summary rather than
    the full model, keeping memory overhead low while still allowing the
    planner to reason about belief evolution over time.
    """
    turn: int
    world_count: int
    certain_facts: dict[str, Any]
    uncertain_props: list[str]
    raw_summary: str          # the full .summary() string for LLM prompts

    def __str__(self) -> str:
        return (
            f"[t={self.turn}] worlds={self.world_count} "
            f"certain={self.certain_facts} "
            f"uncertain={self.uncertain_props}"
        )


# ---------------------------------------------------------------------------
# MemoryStore
# ---------------------------------------------------------------------------

class MemoryStore:
    """
    Two-tier memory: a bounded short-term deque and an unbounded long-term list.

    Parameters
    ----------
    max_short_term : maximum number of entries kept in the rolling short-term window.
    """

    def __init__(self, max_short_term: int = 50) -> None:
        self._short_term: deque[MemoryEntry] = deque(maxlen=max_short_term)
        self._long_term: list[MemoryEntry] = []
        self._kripke_snapshots: list[KripkeSnapshot] = []

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add(self, entry: MemoryEntry) -> None:
        """Append to both short-term (rolling) and long-term (persistent) stores."""
        self._short_term.append(entry)
        self._long_term.append(entry)

    def snapshot_kripke(self, turn: int, model: "KripkeModel") -> None:
        """Persist an epistemic checkpoint at this turn."""
        snapshot = KripkeSnapshot(
            turn=turn,
            world_count=len(model.worlds),
            certain_facts=model.certain_facts(),
            uncertain_props=sorted(model.uncertain_props()),
            raw_summary=model.summary(),
        )
        self._kripke_snapshots.append(snapshot)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def retrieve_recent(self, k: int = 10) -> list[MemoryEntry]:
        """Return the k most recent entries from the short-term window."""
        entries = list(self._short_term)
        return entries[-k:]

    def retrieve(self, query: str = "", k: int = 10) -> list[MemoryEntry]:
        """
        Retrieve up to k relevant entries.

        Default implementation is recency-based.  Override this method (or
        subclass MemoryStore) to plug in vector-based semantic retrieval.
        """
        return self.retrieve_recent(k)

    def last_kripke_snapshot(self) -> KripkeSnapshot | None:
        """Return the most recent Kripke checkpoint, or None if none exists."""
        return self._kripke_snapshots[-1] if self._kripke_snapshots else None

    def kripke_history(self) -> list[KripkeSnapshot]:
        return list(self._kripke_snapshots)

    # ------------------------------------------------------------------
    # Context window formatting
    # ------------------------------------------------------------------

    def short_term_context(self, k: int = 20) -> str:
        """
        Format recent memory as a plain-text block for inclusion in an LLM prompt.
        Ordered oldest → newest so the model sees a natural timeline.
        """
        entries = self.retrieve_recent(k)
        if not entries:
            return "(no short-term memory)"
        return "\n".join(str(e) for e in entries)

    def kripke_context(self) -> str:
        """Format the latest Kripke snapshot for LLM prompt inclusion."""
        snap = self.last_kripke_snapshot()
        if snap is None:
            return "(no epistemic snapshot)"
        return snap.raw_summary

    # ------------------------------------------------------------------
    # Summarisation (requires an LLM)
    # ------------------------------------------------------------------

    def summarise_episode(self, llm: Any, prompt_template: str = "") -> str:
        """
        Ask an LLM to compress the full long-term log into a concise summary.

        Parameters
        ----------
        llm             : any BaseLLM instance.
        prompt_template : optional override for the summarisation instruction.
                          Use {log} as the placeholder for the episode text.
                          Defaults to a generic compress-and-distil instruction.
        """
        if not self._long_term:
            return "(empty episode)"

        episode_log = "\n".join(str(e) for e in self._long_term)

        if prompt_template:
            prompt = prompt_template.format(log=episode_log)
        else:
            prompt = (
                "You are compressing an agent's episode log into long-term memory.\n"
                "Distil the key decisions, tool calls, discoveries, outcomes, and "
                "belief changes into 3-5 concise sentences. Focus on what would be "
                "most useful to know at the start of the next attempt.\n\n"
                f"Episode log:\n{episode_log}"
            )

        return llm.complete(prompt)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "short_term": [
                {"turn": e.turn, "kind": e.kind, "source": e.source,
                 "content": e.content, "metadata": e.metadata}
                for e in self._short_term
            ],
            "long_term_count": len(self._long_term),
            "kripke_snapshots": [
                {"turn": s.turn, "world_count": s.world_count,
                 "certain_facts": s.certain_facts}
                for s in self._kripke_snapshots
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def __repr__(self) -> str:
        return (
            f"MemoryStore(short_term={len(self._short_term)}, "
            f"long_term={len(self._long_term)}, "
            f"snapshots={len(self._kripke_snapshots)})"
        )

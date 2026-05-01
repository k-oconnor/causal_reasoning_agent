"""
causal_agent/kripke.py

Symbolic state space and Kripke model for epistemic reasoning.

A KripkeModel holds:
  - worlds   : the set of game-state hypotheses the agent cannot yet rule out.
  - accessibility : for each *other* agent, a mapping world_id -> {accessible world_ids},
                    representing what we believe that agent currently considers possible.

Interventions (counterfactuals) are operations on this geometry:
  - update_with_facts   : public announcement — eliminate worlds that contradict new facts.
  - simulate_intervention: hypothetical-only version; does not mutate.
  - restrict_for_agent  : model a private update for one other agent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


Facts = dict[str, Any]


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class World:
    """
    A complete, consistent assignment of truth values to all game propositions.

    facts is stored as a frozenset of (prop, value) pairs so World is hashable
    and can live in sets.
    """
    id: str
    _facts: frozenset = field(compare=False, repr=False)

    @classmethod
    def from_dict(cls, world_id: str, facts: Facts) -> "World":
        return cls(id=world_id, _facts=frozenset(facts.items()))

    def get(self, prop: str, default: Any = None) -> Any:
        for k, v in self._facts:
            if k == prop:
                return v
        return default

    def to_dict(self) -> Facts:
        return dict(self._facts)

    def matches(self, constraints: Facts) -> bool:
        """
        True iff every constraint is satisfied.

        A world is only eliminated by a constraint if the proposition
        is actually present in this world AND its value contradicts.
        Props absent from the world are not used for elimination — this
        lets global facts (phase, turn) coexist with role-only worlds.
        """
        _MISSING = object()
        for k, v in constraints.items():
            stored = self.get(k, _MISSING)
            if stored is not _MISSING and not _constraint_matches(stored, v):
                return False
        return True

    def __repr__(self) -> str:
        return f"World({self.id}, {dict(self._facts)})"


# ---------------------------------------------------------------------------
# KripkeModel
# ---------------------------------------------------------------------------

@dataclass
class KripkeModel:
    """
    Epistemic model from our agent's point of view.

    worlds        – states the agent considers possible (the indistinguishable set).
    accessibility – agent_name -> {from_world_id -> set(reachable_world_ids)}.
                    Encodes what we believe each *other* player currently knows.
    """
    worlds: list[World]
    accessibility: dict[str, dict[str, set[str]]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def world_ids(self) -> set[str]:
        return {w.id for w in self.worlds}

    def world_by_id(self, wid: str) -> World | None:
        for w in self.worlds:
            if w.id == wid:
                return w
        return None

    # ------------------------------------------------------------------
    # Epistemic queries
    # ------------------------------------------------------------------

    def certain_facts(self) -> Facts:
        """
        Return facts whose value is identical across every candidate world
        — i.e. what we know for certain right now.
        """
        if not self.worlds:
            return {}
        base = self.worlds[0].to_dict()
        return {
            prop: val
            for prop, val in base.items()
            if all(w.get(prop) == val for w in self.worlds[1:])
        }

    def uncertain_props(self) -> set[str]:
        """Props that differ across at least two candidate worlds."""
        if len(self.worlds) < 2:
            return set()
        certain = self.certain_facts()
        all_props: set[str] = set()
        for w in self.worlds:
            all_props |= w.to_dict().keys()
        return all_props - certain.keys()

    def accessible_worlds(self, agent: str, from_world_id: str) -> set[str]:
        """World ids that `agent` considers possible from `from_world_id`."""
        return self.accessibility.get(agent, {}).get(from_world_id, set())

    def believes(
        self, agent: str, from_world_id: str, prop: str, value: Any
    ) -> bool:
        """
        True iff prop=value holds in *every* world accessible to `agent`
        from `from_world_id` — i.e. `agent` believes it.
        """
        acc_ids = self.accessible_worlds(agent, from_world_id)
        acc_worlds = [w for w in self.worlds if w.id in acc_ids]
        if not acc_worlds:
            return False
        return all(w.get(prop) == value for w in acc_worlds)

    # ------------------------------------------------------------------
    # Interventions / updates
    # ------------------------------------------------------------------

    def update_with_facts(self, new_facts: Facts) -> "KripkeModel":
        """
        Public announcement update.

        Eliminates all worlds inconsistent with new_facts, then prunes
        accessibility edges that point to eliminated worlds.
        """
        surviving = [w for w in self.worlds if w.matches(new_facts)]
        surviving_ids = {w.id for w in surviving}

        new_access: dict[str, dict[str, set[str]]] = {}
        for agent, relations in self.accessibility.items():
            new_access[agent] = {
                wid: (acc & surviving_ids)
                for wid, acc in relations.items()
                if wid in surviving_ids
            }

        return KripkeModel(worlds=surviving, accessibility=new_access)

    def simulate_intervention(self, hypothetical_facts: Facts) -> "KripkeModel":
        """
        Counterfactual: return the model *as if* hypothetical_facts were true,
        without committing to them.  Used by the planner to evaluate moves.
        """
        return self.update_with_facts(hypothetical_facts)

    def restrict_for_agent(
        self, agent: str, from_world_id: str, revealed_facts: Facts
    ) -> "KripkeModel":
        """
        Model a *private* update for `agent` at `from_world_id`:
        remove worlds from their accessible set that contradict revealed_facts.
        Used to reason about what others will believe after a speech act.
        """
        new_access = {a: dict(r) for a, r in self.accessibility.items()}
        if agent in new_access and from_world_id in new_access[agent]:
            new_access[agent][from_world_id] = {
                wid
                for wid in new_access[agent][from_world_id]
                if (w := self.world_by_id(wid)) is not None and w.matches(revealed_facts)
            }
        return KripkeModel(worlds=self.worlds, accessibility=new_access)

    # ------------------------------------------------------------------
    # Summary for LLM prompts
    # ------------------------------------------------------------------

    def summary(self, max_worlds: int = 8) -> str:
        """
        Compact human-readable summary suitable for embedding in an LLM prompt.
        """
        certain = self.certain_facts()
        uncertain = self.uncertain_props()

        lines = [
            f"[KripkeModel] {len(self.worlds)} candidate world(s).",
            f"  Certain facts  : {certain if certain else '(none)'}",
            f"  Uncertain props: {sorted(uncertain) if uncertain else '(none)'}",
        ]

        shown = self.worlds[:max_worlds]
        if shown:
            lines.append("  Candidate worlds (showing up to 8):")
            for w in shown:
                uncertain_vals = {
                    k: v for k, v in w.to_dict().items() if k in uncertain
                }
                lines.append(f"    {w.id}: {uncertain_vals}")
            if len(self.worlds) > max_worlds:
                lines.append(f"    ... and {len(self.worlds) - max_worlds} more.")

        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.worlds)

    def __repr__(self) -> str:
        return f"KripkeModel(worlds={len(self.worlds)}, agents={list(self.accessibility)})"


def _constraint_matches(stored: Any, constraint: Any) -> bool:
    if isinstance(constraint, Mapping) and "$in" in constraint:
        allowed = {_normalise_value(value) for value in constraint["$in"]}
        return _normalise_value(stored) in allowed
    return stored == constraint


def _normalise_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_normalise_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_normalise_value(item) for item in value)
    return value

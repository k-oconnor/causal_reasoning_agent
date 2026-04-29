"""
causal_agent/planning.py

Kripke-grounded planner.

The Planner's job is to reason over:
  1. The current KripkeModel  — what worlds are still possible?
  2. Short-term memory        — what has happened recently?
  3. The agent's goal         — what outcome are we optimising for?
  4. Valid actions            — what moves are currently legal?

It then asks the LLM to produce a Plan (structured intent), optionally
after running one or more *intervention simulations* on the Kripke frame
to evaluate hypothetical moves before committing.

Intervention simulation
-----------------------
Before calling the LLM, evaluate_intervention() computes:
    "If I assert hypothetical_facts, how many worlds survive and what
     becomes certain / uncertain?"
This is pure symbolic computation — no LLM call — giving the planner
an explicit epistemic cost/benefit for each candidate move.
The resulting summaries are embedded in the prompt so the LLM can
reason about them in language.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from causal_agent.kripke import KripkeModel
from causal_agent.memory import MemoryStore
from causal_agent.llm import BaseLLM

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------

@dataclass
class Plan:
    """
    Structured intent produced by the Planner.

    Attributes
    ----------
    intent           : high-level goal for this step (natural language).
    action_type      : which action category to take (e.g. "speak", "vote").
    parameters       : action-specific payload (message text, target player…).
    reasoning        : chain-of-thought explanation from the LLM.
    supporting_worlds: world ids from the KripkeModel that support this plan.
    intervention_notes: summaries of any counterfactual simulations run.
    """
    intent: str
    action_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    supporting_worlds: list[str] = field(default_factory=list)
    intervention_notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Plan(intent={self.intent!r}, "
            f"action_type={self.action_type!r}, "
            f"params={self.parameters})"
        )


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    """
    Produces Plans by grounding LLM reasoning in the KripkeModel.

    Parameters
    ----------
    llm            : any BaseLLM backend.
    simulate_before_plan : if True, run intervention simulations for each
                           valid action and include the results in the prompt.
    """

    def __init__(self, llm: BaseLLM, simulate_before_plan: bool = True) -> None:
        self._llm = llm
        self._simulate = simulate_before_plan

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(
        self,
        kripke: KripkeModel,
        memory: MemoryStore,
        goal: str,
        agent_id: str,
        valid_actions: list[str],
    ) -> Plan:
        """
        Produce a Plan given the current epistemic state and memory.

        Steps
        -----
        1. Optionally simulate each valid action as an intervention.
        2. Build a prompt from kripke summary, memory, and simulations.
        3. Call the LLM.
        4. Parse the response into a Plan.
        """
        intervention_notes: list[str] = []

        if self._simulate and valid_actions:
            for action in valid_actions:
                note = self.evaluate_intervention(
                    kripke, {"last_action_type": action}, agent_id
                )
                intervention_notes.append(f"[{action}]: {note}")

        prompt = self._build_prompt(
            kripke=kripke,
            memory=memory,
            goal=goal,
            agent_id=agent_id,
            valid_actions=valid_actions,
            intervention_notes=intervention_notes,
        )

        from causal_agent.prompts import REACTIVE_SYSTEM
        raw = self._llm.complete(prompt, system=REACTIVE_SYSTEM)
        plan = self._parse_response(raw, valid_actions)
        plan.intervention_notes = intervention_notes

        # Attach worlds consistent with the chosen action type as support
        plan.supporting_worlds = [
            w.id for w in kripke.worlds
            if w.matches({"last_action_type": plan.action_type})
        ] or [w.id for w in kripke.worlds[:3]]

        return plan

    def evaluate_intervention(
        self,
        kripke: KripkeModel,
        hypothetical_facts: dict[str, Any],
        agent_id: str,
    ) -> str:
        """
        Symbolically evaluate the epistemic effect of asserting hypothetical_facts.

        Returns a short human-readable summary suitable for embedding in a prompt.
        This is pure Kripke computation — no LLM call.
        """
        before = len(kripke.worlds)
        after_model = kripke.simulate_intervention(hypothetical_facts)
        after = len(after_model.worlds)
        new_certain = after_model.certain_facts()
        eliminated = before - after

        lines = [
            f"Asserting {hypothetical_facts}:",
            f"  worlds {before} → {after} ({eliminated} eliminated)",
            f"  newly certain: {new_certain if new_certain else '(none)'}",
        ]
        return " | ".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        kripke: KripkeModel,
        memory: MemoryStore,
        goal: str,
        agent_id: str,
        valid_actions: list[str],
        intervention_notes: list[str],
    ) -> str:
        sections: list[str] = []

        sections.append(f"=== AGENT: {agent_id} | GOAL: {goal} ===")

        sections.append("--- EPISTEMIC STATE ---")
        sections.append(kripke.summary())

        sections.append("--- RECENT MEMORY ---")
        sections.append(memory.short_term_context(k=15))

        if intervention_notes:
            sections.append("--- INTERVENTION SIMULATIONS ---")
            sections.append(
                "For each valid action, here is the epistemic effect of asserting it:"
            )
            sections.extend(intervention_notes)

        sections.append("--- VALID ACTIONS ---")
        sections.append(", ".join(valid_actions) if valid_actions else "(none)")

        sections.append(
            "--- YOUR TASK ---\n"
            "Output a JSON object with keys: intent, action_type, parameters, reasoning.\n"
            "Choose the action_type from the valid actions list."
        )

        return "\n\n".join(sections)

    def _parse_response(self, raw: str, valid_actions: list[str]) -> Plan:
        """
        Parse LLM JSON output into a Plan, with graceful fallback.
        """
        cleaned = raw.strip()

        # Strip markdown fences if the model added them despite instructions.
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Last-resort: pull out anything that looks like JSON.
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        action_type = str(data.get("action_type", ""))
        if action_type not in valid_actions and valid_actions:
            action_type = valid_actions[0]

        return Plan(
            intent=str(data.get("intent", "unknown")),
            action_type=action_type,
            parameters=data.get("parameters", {}),
            reasoning=str(data.get("reasoning", raw)),
        )

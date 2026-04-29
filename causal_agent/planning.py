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
from typing import Any, Callable, Mapping, Sequence, TYPE_CHECKING

from causal_agent.actions import (
    ActionSchemaError,
    ActionSpec,
    action_spec_by_type,
    action_type_names,
    coerce_action_specs,
    format_action_specs_for_prompt,
    structured_plan_schema,
)
from causal_agent.kripke import KripkeModel
from causal_agent.memory import MemoryStore
from causal_agent.llm import BaseLLM
from causal_agent.prompts import REACTIVE_SYSTEM
from causal_agent.tool_loop import run_tool_loop
from causal_agent.tools import ToolRegistry

if TYPE_CHECKING:
    from causal_agent.acting import GameAction


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
    reasoning        : brief public rationale from the LLM.
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

    SYSTEM_PROMPT = REACTIVE_SYSTEM

    def __init__(
        self,
        llm: BaseLLM,
        simulate_before_plan: bool = True,
        max_parse_retries: int = 1,
        system: str | None = None,
        tools: ToolRegistry | None = None,
        preview: Callable[[str, "GameAction"], dict | None] | None = None,
        max_tool_calls: int = 8,
    ) -> None:
        self._llm = llm
        self._simulate = simulate_before_plan
        self._max_parse_retries = max_parse_retries
        self._system = system or self.SYSTEM_PROMPT
        self._tools = tools
        self._preview = preview
        self._max_tool_calls = max_tool_calls

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(
        self,
        kripke: KripkeModel,
        memory: MemoryStore,
        goal: str,
        agent_id: str,
        valid_actions: list[str] | None = None,
        action_specs: Sequence[ActionSpec | str] | None = None,
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
        specs = coerce_action_specs(action_specs or valid_actions or [])
        action_types = action_type_names(specs)

        if not specs:
            raise ValueError("Planner.plan() requires at least one legal action spec.")

        intervention_notes: list[str] = []
        preview_notes = self._preview_notes(agent_id, specs)

        if self._simulate and action_types:
            for action in action_types:
                note = self.evaluate_intervention(
                    kripke, {"last_action_type": action}, agent_id
                )
                intervention_notes.append(f"[{action}]: {note}")

        prompt = self._build_prompt(
            kripke=kripke,
            memory=memory,
            goal=goal,
            agent_id=agent_id,
            action_specs=specs,
            intervention_notes=intervention_notes,
            preview_notes=preview_notes,
        )

        plan_schema = structured_plan_schema(specs)
        last_error = ""
        plan: Plan | None = None
        active_tools = self._active_tools(kripke)

        for attempt in range(self._max_parse_retries + 1):
            retry_prompt = prompt
            if last_error:
                retry_prompt = (
                    f"{prompt}\n\n"
                    f"Your previous response was invalid: {last_error}\n"
                    "Return a corrected JSON object using the same action schemas."
                )
            try:
                if active_tools:
                    try:
                        raw = self._complete_with_tools(retry_prompt, active_tools)
                    except NotImplementedError:
                        active_tools = None
                        raw = self._llm.complete_structured(
                            retry_prompt,
                            schema=plan_schema,
                            system=self._system,
                        )
                else:
                    raw = self._llm.complete_structured(
                        retry_prompt,
                        schema=plan_schema,
                        system=self._system,
                    )
                plan = self._parse_response(raw, specs)
                break
            except (ActionSchemaError, PlanParseError, ValueError) as exc:
                last_error = str(exc)

        if plan is None:
            plan = self._fallback_plan(specs, last_error)

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
        action_specs: Sequence[ActionSpec],
        intervention_notes: list[str],
        preview_notes: list[str] | None = None,
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

        if preview_notes:
            sections.append("--- ACTION PREVIEWS ---")
            sections.append(
                "Read-only consequences for candidate action payloads. "
                "Use these to compare immediate outcomes before committing."
            )
            sections.extend(preview_notes)

        sections.append("--- LEGAL ACTION SCHEMAS ---")
        sections.append(format_action_specs_for_prompt(action_specs))

        sections.append(
            "--- YOUR TASK ---\n"
            "Output a JSON object with keys: intent, action_type, parameters, public_rationale.\n"
            "Choose action_type from the legal action schemas and make parameters match that schema."
        )

        return "\n\n".join(sections)

    def _active_tools(self, kripke: KripkeModel) -> ToolRegistry | None:
        registry = self._tools
        if registry is not None and getattr(registry, "use_kripke_tools", False):
            from causal_agent.kripke_tools import KripkeToolset

            KripkeToolset(lambda: kripke).register_all(registry)
        return registry if registry and len(registry) > 0 else None

    def _complete_with_tools(self, prompt: str, registry: ToolRegistry) -> str:
        result = run_tool_loop(
            llm=self._llm,
            registry=registry,
            messages=[{"role": "user", "content": prompt}],
            system=self._system,
            max_iterations=self._max_tool_calls,
        )
        return result.content

    def _preview_notes(
        self,
        agent_id: str,
        action_specs: Sequence[ActionSpec],
    ) -> list[str]:
        if self._preview is None:
            return []

        from causal_agent.acting import GameAction

        notes: list[str] = []
        seen: set[str] = set()

        for spec in action_specs:
            examples = spec.examples or [spec.fallback_payload()]
            for example in examples:
                payload: dict[str, Any] = dict(example)
                try:
                    payload = spec.validate_payload(example)
                    key = json.dumps(
                        {"action_type": spec.action_type, "payload": payload},
                        sort_keys=True,
                        default=str,
                    )
                    if key in seen:
                        continue
                    seen.add(key)

                    action = GameAction(
                        action_type=spec.action_type,
                        payload=payload,
                        agent_id=agent_id,
                    )
                    result = self._preview(agent_id, action)
                except Exception as exc:
                    result = {"error": str(exc)}

                if result is None:
                    continue

                notes.append(
                    f"[{spec.action_type} {json.dumps(payload, sort_keys=True, default=str)}]: "
                    f"{json.dumps(result, sort_keys=True, default=str)}"
                )

        return notes

    def _parse_response(
        self,
        raw: str | Mapping[str, Any],
        action_specs: Sequence[ActionSpec | str],
    ) -> Plan:
        """
        Parse and validate LLM output into a Plan.
        """
        data = self._coerce_response_dict(raw)
        by_type = action_spec_by_type(action_specs)
        action_type = str(data.get("action_type", ""))

        if action_type not in by_type:
            raise PlanParseError(
                f"LLM chose unknown action_type {action_type!r}; "
                f"expected one of {list(by_type)}."
            )

        parameters = data.get("parameters", {})
        if not isinstance(parameters, Mapping):
            raise PlanParseError("LLM parameters must be a JSON object.")

        validated_parameters = by_type[action_type].validate_payload(parameters)
        public_rationale = data.get("public_rationale", data.get("reasoning", ""))

        return Plan(
            intent=str(data.get("intent", "unknown")),
            action_type=action_type,
            parameters=validated_parameters,
            reasoning=str(public_rationale),
        )

    def _coerce_response_dict(self, raw: str | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(raw, Mapping):
            return dict(raw)

        cleaned = raw.strip()
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise PlanParseError(f"LLM did not return JSON: {raw!r}")
            data = json.loads(match.group())

        if not isinstance(data, dict):
            raise PlanParseError("LLM plan response must be a JSON object.")
        return data

    def _fallback_plan(
        self,
        action_specs: Sequence[ActionSpec | str],
        reason: str,
    ) -> Plan:
        specs = coerce_action_specs(action_specs)
        spec = specs[0]
        return Plan(
            intent="fallback legal action",
            action_type=spec.action_type,
            parameters=spec.fallback_payload(),
            reasoning=f"Fell back after invalid structured output: {reason}",
        )


class PlanParseError(ValueError):
    """Raised when the planner cannot parse a valid structured plan."""

from __future__ import annotations

import unittest

from pydantic import Field, create_model

from causal_agent.actions import (
    ActionSchemaError,
    ActionSpec,
    _ForbidExtraConfig,
    string_enum,
    structured_plan_schema,
)
from causal_agent.acting import ActionError, Actor
from causal_agent.kripke import KripkeModel, World
from causal_agent.llm import MockLLM
from causal_agent.memory import MemoryStore
from causal_agent.planning import Plan, Planner


SlidePayload = create_model(
    "SlidePayload",
    __config__=_ForbidExtraConfig,
    direction=(
        string_enum("TestDirection", ["left", "right"]),
        Field(..., description="One legal direction."),
    ),
)


class ActionSchemaTests(unittest.TestCase):
    def test_action_spec_validates_payload(self) -> None:
        spec = ActionSpec(
            action_type="slide",
            description="Slide in a legal direction.",
            payload_model=SlidePayload,
            examples=[{"direction": "left"}],
        )

        self.assertEqual(spec.validate_payload({"direction": "left"}), {"direction": "left"})
        with self.assertRaises(ActionSchemaError):
            spec.validate_payload({"direction": "up"})

    def test_structured_plan_schema_contains_action_enum(self) -> None:
        spec = ActionSpec("slide", "Slide.", SlidePayload)
        schema = structured_plan_schema([spec])

        self.assertEqual(schema["properties"]["action_type"]["enum"], ["slide"])
        self.assertIn("parameters", schema["required"])

    def test_actor_rejects_invalid_payload(self) -> None:
        spec = ActionSpec("slide", "Slide.", SlidePayload)
        plan = Plan(intent="move", action_type="slide", parameters={"direction": "up"})

        with self.assertRaises(ActionError):
            Actor().act(plan, [spec], "Agent")


class PlannerStructuredOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = ActionSpec(
            action_type="slide",
            description="Slide in a legal direction.",
            payload_model=SlidePayload,
            examples=[{"direction": "left"}],
        )
        self.kripke = KripkeModel(worlds=[World.from_dict("actual", {})])
        self.memory = MemoryStore()

    def test_planner_falls_back_on_malformed_json(self) -> None:
        planner = Planner(
            MockLLM(["not json"]),
            simulate_before_plan=False,
            max_parse_retries=0,
        )

        plan = planner.plan(
            kripke=self.kripke,
            memory=self.memory,
            goal="move",
            agent_id="Agent",
            action_specs=[self.spec],
        )

        self.assertEqual(plan.action_type, "slide")
        self.assertEqual(plan.parameters, {"direction": "left"})

    def test_planner_falls_back_on_unknown_action(self) -> None:
        planner = Planner(
            MockLLM([
                '{"intent": "bad", "action_type": "jump", '
                '"parameters": {}, "public_rationale": "invalid"}'
            ]),
            simulate_before_plan=False,
            max_parse_retries=0,
        )

        plan = planner.plan(
            kripke=self.kripke,
            memory=self.memory,
            goal="move",
            agent_id="Agent",
            action_specs=[self.spec],
        )

        self.assertEqual(plan.action_type, "slide")
        self.assertEqual(plan.parameters, {"direction": "left"})

    def test_planner_falls_back_on_invalid_payload(self) -> None:
        planner = Planner(
            MockLLM([
                '{"intent": "bad", "action_type": "slide", '
                '"parameters": {"direction": "up"}, "public_rationale": "invalid"}'
            ]),
            simulate_before_plan=False,
            max_parse_retries=0,
        )

        plan = planner.plan(
            kripke=self.kripke,
            memory=self.memory,
            goal="move",
            agent_id="Agent",
            action_specs=[self.spec],
        )

        self.assertEqual(plan.parameters, {"direction": "left"})


if __name__ == "__main__":
    unittest.main()

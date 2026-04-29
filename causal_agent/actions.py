"""
causal_agent/actions.py

Shared action schema primitives.

Games declare legal actions as ActionSpec objects. The planner uses those
specs to ask the LLM for a structured decision, and the actor validates the
selected payload before submitting a GameAction to the environment.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence, Type

from pydantic import BaseModel, ValidationError


if hasattr(BaseModel, "model_validate"):
    from pydantic import ConfigDict

    _ForbidExtraConfig = ConfigDict(extra="forbid", use_enum_values=True)
else:
    class _ForbidExtraConfig:
        extra = "forbid"
        use_enum_values = True


class ActionSchemaError(ValueError):
    """Raised when an action payload does not match its declared schema."""


class EmptyPayload(BaseModel):
    """Payload model for actions that do not require parameters."""

    if hasattr(BaseModel, "model_validate"):
        model_config = _ForbidExtraConfig
    else:
        class Config(_ForbidExtraConfig):
            pass


PayloadModel = Type[BaseModel]


def model_json_schema(model: PayloadModel) -> dict[str, Any]:
    """Return a JSON Schema for a Pydantic v1 or v2 model."""

    if hasattr(model, "model_json_schema"):
        return model.model_json_schema()  # type: ignore[attr-defined]
    return model.schema()


def validate_model(model: PayloadModel, data: Mapping[str, Any]) -> BaseModel:
    """Validate data against a Pydantic v1 or v2 model."""

    if hasattr(model, "model_validate"):
        return model.model_validate(data)  # type: ignore[attr-defined]
    return model.parse_obj(data)


def dump_model(instance: BaseModel) -> dict[str, Any]:
    """Dump a Pydantic v1 or v2 model to a plain dict."""

    if hasattr(instance, "model_dump"):
        return instance.model_dump()  # type: ignore[attr-defined]
    return instance.dict()


@dataclass(frozen=True)
class ActionSpec:
    """
    Contract for one game action.

    action_type
        Stable action name submitted to the environment.
    description
        Short natural-language hint for the planner.
    payload_model
        Pydantic model validating the action payload.
    examples
        Optional valid payload examples, used for prompts and safe fallbacks.
    """

    action_type: str
    description: str
    payload_model: PayloadModel = EmptyPayload
    examples: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.action_type:
            raise ValueError("ActionSpec.action_type must be non-empty.")
        if not issubclass(self.payload_model, BaseModel):
            raise TypeError("ActionSpec.payload_model must be a Pydantic BaseModel.")

    def payload_schema(self) -> dict[str, Any]:
        return model_json_schema(self.payload_model)

    def validate_payload(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        try:
            validated = validate_model(self.payload_model, dict(payload or {}))
        except ValidationError as exc:
            raise ActionSchemaError(
                f"Payload for action {self.action_type!r} failed validation: {exc}"
            ) from exc
        return dump_model(validated)

    def fallback_payload(self) -> dict[str, Any]:
        if self.examples:
            return self.validate_payload(self.examples[0])
        return self.validate_payload({})

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "description": self.description,
            "payload_schema": self.payload_schema(),
            "examples": self.examples,
        }


def coerce_action_specs(actions: Sequence[ActionSpec | str]) -> list[ActionSpec]:
    """Accept either modern ActionSpec objects or legacy action strings."""

    specs: list[ActionSpec] = []
    for action in actions:
        if isinstance(action, ActionSpec):
            specs.append(action)
        else:
            specs.append(ActionSpec(str(action), "Legacy action with no payload schema."))
    return specs


def action_spec_by_type(actions: Sequence[ActionSpec | str]) -> dict[str, ActionSpec]:
    specs = coerce_action_specs(actions)
    by_type: dict[str, ActionSpec] = {}
    for spec in specs:
        if spec.action_type in by_type:
            raise ValueError(f"Duplicate action_type in action specs: {spec.action_type!r}")
        by_type[spec.action_type] = spec
    return by_type


def action_type_names(actions: Sequence[ActionSpec | str]) -> list[str]:
    return [spec.action_type for spec in coerce_action_specs(actions)]


def structured_plan_schema(action_specs: Sequence[ActionSpec | str]) -> dict[str, Any]:
    """
    JSON Schema for the planner's top-level response.

    Payload-specific validation is still performed locally by ActionSpec. This
    keeps the provider-facing schema simple and portable across OpenAI,
    Anthropic, Gemini, and weaker JSON-mode backends.
    """

    action_types = action_type_names(action_specs)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["intent", "action_type", "parameters", "public_rationale"],
        "properties": {
            "intent": {
                "type": "string",
                "description": "Short high-level goal for this turn.",
            },
            "action_type": {
                "type": "string",
                "enum": action_types,
                "description": "One action_type from the current legal action specs.",
            },
            "parameters": {
                "type": "object",
                "additionalProperties": True,
                "description": (
                    "Payload for the chosen action_type. It must match that "
                    "action's payload_schema from the prompt."
                ),
            },
            "public_rationale": {
                "type": "string",
                "description": "Brief explanation safe to log; do not include hidden chain of thought.",
            },
        },
    }


def format_action_specs_for_prompt(action_specs: Sequence[ActionSpec | str]) -> str:
    specs = [spec.to_prompt_dict() for spec in coerce_action_specs(action_specs)]
    return json.dumps(specs, indent=2, sort_keys=True)


def string_enum(name: str, values: Sequence[str]) -> type[Enum]:
    """Create a Pydantic-friendly string Enum from runtime values."""

    if not values:
        raise ValueError("Cannot create enum from an empty value list.")

    members: dict[str, str] = {}
    for index, raw_value in enumerate(values):
        value = str(raw_value)
        member = re.sub(r"\W+", "_", value).strip("_").upper()
        if not member or member[0].isdigit():
            member = f"VALUE_{index}"
        while member in members:
            member = f"{member}_{index}"
        members[member] = value
    return Enum(name, members, type=str)


__all__ = [
    "ActionSchemaError",
    "ActionSpec",
    "EmptyPayload",
    "PayloadModel",
    "_ForbidExtraConfig",
    "action_spec_by_type",
    "action_type_names",
    "coerce_action_specs",
    "dump_model",
    "format_action_specs_for_prompt",
    "model_json_schema",
    "string_enum",
    "structured_plan_schema",
    "validate_model",
]

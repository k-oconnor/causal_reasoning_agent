from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    if not is_dataclass(value) or isinstance(value, type):
        raise TypeError(f"Expected a dataclass instance, got {type(value).__name__}.")
    return asdict(value)

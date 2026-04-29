from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any


class TraceLogger:
    """JSONL writer for one evaluation episode."""

    def __init__(self, log_dir: Path | None, filename: str) -> None:
        self.log_dir = log_dir
        self.filename = filename
        self._file = None

    def __enter__(self) -> "TraceLogger":
        if self.log_dir is not None:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._file = (self.log_dir / self.filename).open("w")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._file is not None:
            self._file.close()

    def write(self, record: dict[str, Any]) -> None:
        if self._file is not None:
            self._file.write(json.dumps(record) + "\n")


def write_summary(log_dir: Path | None, policy: str, summary: dict[str, Any]) -> Path | None:
    if log_dir is None:
        return None
    log_dir.mkdir(parents=True, exist_ok=True)
    summary_path = log_dir / f"summary_{policy}.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary_path


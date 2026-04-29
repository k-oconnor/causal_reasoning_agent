"""
causal_agent/file_tools.py

File I/O as LLM-callable tools, scoped to a single workspace directory.

The agent can write scripts, manifests, and any other artifacts directly
to disk.  All paths are resolved relative to the workspace root — the agent
cannot escape it.  Every write is logged.

Tools registered
----------------
  save_file(filename, content)   – write (or overwrite) a file.
  read_file(filename)            – read a previously written file back.
  list_files()                   – list all files in the workspace.

Usage
-----
    from causal_agent.file_tools import FileTools

    ft = FileTools(workspace="agent_workspace")
    ft.register_all(registry)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from causal_agent.tools import ToolDefinition, ToolRegistry

log = logging.getLogger("causal_agent.file_tools")


class FileTools:
    """
    File I/O tools scoped to a workspace directory.

    Parameters
    ----------
    workspace : Path or str pointing to the directory the agent may write to.
                Created automatically if it does not exist.
    """

    def __init__(self, workspace: str | Path = "agent_workspace") -> None:
        self._root = Path(workspace).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        log.info("FileTools workspace: %s", self._root)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_all(self, registry: ToolRegistry) -> None:
        registry.register(self._defn_save(),  self._save)
        registry.register(self._defn_read(),  self._read)
        registry.register(self._defn_list(),  self._list)

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def _defn_save(self) -> ToolDefinition:
        return ToolDefinition(
            name="save_file",
            description=(
                "Write content to a file in the agent workspace. "
                "Use this to save flight scripts, rocket manifests, analysis "
                "notes, or any artifact the operator will need. "
                "The filename should be descriptive and versioned where relevant "
                "(e.g. 'flight_attempt_1.py', 'manifest_attempt_2.md'). "
                "Overwrites silently if the file already exists. "
                "Returns the absolute path of the saved file."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": (
                            "Filename only (no directory separators). "
                            "Use .py for scripts, .md for manifests/notes."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "Full text content to write.",
                    },
                },
                "required": ["filename", "content"],
            },
        )

    def _defn_read(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description=(
                "Read the content of a file previously saved to the agent workspace. "
                "Useful for reviewing a prior script before revising it."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename to read (must exist in the workspace).",
                    },
                },
                "required": ["filename"],
            },
        )

    def _defn_list(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_files",
            description=(
                "List all files currently in the agent workspace. "
                "Call this at the start of a new attempt to see what was "
                "produced in previous attempts."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    # ------------------------------------------------------------------
    # Callables
    # ------------------------------------------------------------------

    def _save(self, filename: str, content: str) -> str:
        path = self._safe_path(filename)
        if path is None:
            return f"Error: '{filename}' is not a valid filename (no path separators allowed)."
        path.write_text(content, encoding="utf-8")
        log.info("save_file: wrote %d chars to %s", len(content), path)
        return f"Saved to {path}"

    def _read(self, filename: str) -> str:
        path = self._safe_path(filename)
        if path is None:
            return f"Error: '{filename}' is not a valid filename."
        if not path.exists():
            return f"Error: '{filename}' does not exist in the workspace."
        content = path.read_text(encoding="utf-8")
        log.info("read_file: read %d chars from %s", len(content), path)
        return content

    def _list(self) -> str:
        files = sorted(f.name for f in self._root.iterdir() if f.is_file() and f.name != ".gitkeep")
        if not files:
            return "(workspace is empty)"
        lines = [f"Workspace: {self._root}"]
        for name in files:
            size = (self._root / name).stat().st_size
            lines.append(f"  {name}  ({size:,} bytes)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _safe_path(self, filename: str) -> Path | None:
        """Resolve filename inside the workspace root; reject any path traversal."""
        # Strip any directory component — only bare filenames allowed
        name = Path(filename).name
        if not name or name != filename.replace("\\", "/").split("/")[-1]:
            return None
        # Extra guard: resolved path must still be inside the workspace
        resolved = (self._root / name).resolve()
        if not str(resolved).startswith(str(self._root)):
            return None
        return resolved

"""
causal_agent/human_interface.py

Human-in-the-loop communication as tool-callable actions.

The agent calls these tools the same way it calls web_search or kripke_*:
via the ToolRegistry during the planning or execution phases.  This keeps
human communication visible in the tool call log and decoupled from the
rest of the framework.

Three tools are registered:
  human_notify(message)          – send a message, don't wait.
  human_ask(question)            – send a message, block for a typed response.
  human_confirm(message)         – send a message, wait for yes / no.

Backends
--------
CliBackend    (default) – prints to stdout, reads from stdin.
SilentBackend           – logs only, returns preset responses.  Use in tests
                          or automated pipelines where no human is present.

Usage
-----
    from causal_agent.human_interface import HumanInterface

    hi = HumanInterface()                    # CLI by default
    hi.register_all(registry)

    # For tests / CI:
    hi = HumanInterface(backend="silent", silent_response="yes")
    hi.register_all(registry)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Literal

from causal_agent.tools import ToolDefinition, ToolRegistry

log = logging.getLogger("causal_agent.human_interface")


# ---------------------------------------------------------------------------
# Backend ABC
# ---------------------------------------------------------------------------

class _Backend(ABC):
    @abstractmethod
    def notify(self, message: str) -> None: ...

    @abstractmethod
    def ask(self, question: str) -> str: ...

    @abstractmethod
    def confirm(self, message: str) -> bool: ...


# ---------------------------------------------------------------------------
# CLI backend
# ---------------------------------------------------------------------------

class CliBackend(_Backend):
    """Prints to stdout and reads from stdin."""

    _BORDER = "─" * 60

    def notify(self, message: str) -> None:
        print(f"\n{self._BORDER}")
        print(f"[AGENT] {message}")
        print(self._BORDER)
        log.info("human_notify: %s", message)

    def ask(self, question: str) -> str:
        print(f"\n{self._BORDER}")
        print(f"[AGENT] {question}")
        print(self._BORDER)
        log.info("human_ask: %s", question)
        try:
            response = input("Your response: ").strip()
        except EOFError:
            response = ""
        log.info("human_ask response: %r", response)
        return response

    def confirm(self, message: str) -> bool:
        print(f"\n{self._BORDER}")
        print(f"[AGENT] {message}")
        print(self._BORDER)
        log.info("human_confirm: %s", message)
        while True:
            try:
                raw = input("Confirm? [yes/no]: ").strip().lower()
            except EOFError:
                raw = "no"
            if raw in ("yes", "y"):
                log.info("human_confirm response: yes")
                return True
            if raw in ("no", "n"):
                log.info("human_confirm response: no")
                return False
            print("Please type 'yes' or 'no'.")


# ---------------------------------------------------------------------------
# Silent backend (tests / automation)
# ---------------------------------------------------------------------------

class SilentBackend(_Backend):
    """
    Logs messages but does not block.

    Parameters
    ----------
    silent_response : default string returned by ask().
    silent_confirm  : default bool returned by confirm().
    """

    def __init__(
        self,
        silent_response: str = "ok",
        silent_confirm: bool = True,
    ) -> None:
        self._response = silent_response
        self._confirm = silent_confirm

    def notify(self, message: str) -> None:
        log.info("[silent] human_notify: %s", message)

    def ask(self, question: str) -> str:
        log.info("[silent] human_ask: %s >> %r", question, self._response)
        return self._response

    def confirm(self, message: str) -> bool:
        log.info("[silent] human_confirm: %s >> %s", message, self._confirm)
        return self._confirm


# ---------------------------------------------------------------------------
# HumanInterface
# ---------------------------------------------------------------------------

class HumanInterface:
    """
    Wraps a communication backend and registers human tools into a ToolRegistry.

    Parameters
    ----------
    backend         : "cli" (default) or "silent", or a custom _Backend instance.
    silent_response : used when backend="silent"; default reply for ask().
    silent_confirm  : used when backend="silent"; default reply for confirm().
    """

    def __init__(
        self,
        backend: Literal["cli", "silent", "web"] | _Backend = "cli",
        silent_response: str = "ok",
        silent_confirm: bool = True,
        web_port: int = 8765,
    ) -> None:
        if isinstance(backend, str):
            if backend == "cli":
                self._backend: _Backend = CliBackend()
            elif backend == "silent":
                self._backend = SilentBackend(silent_response, silent_confirm)
            elif backend == "web":
                from causal_agent.ui_server import AgentUIServer, WebBackend
                server = AgentUIServer(port=web_port)
                server.start()
                self._backend = WebBackend(server)
                self._server = server
                import webbrowser, threading
                threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{web_port}")).start()
            else:
                raise ValueError(f"Unknown backend {backend!r}. Use 'cli', 'silent', or 'web'.")
        else:
            self._backend = backend
        # Expose server if WebBackend was passed directly
        if not hasattr(self, "_server") and hasattr(self._backend, "_server"):
            self._server = self._backend._server

    def register_all(self, registry: ToolRegistry) -> None:
        """Register human interface tools into `registry`.

        Always registers: human_notify, human_ask, human_confirm.
        When the backend supports operator instructions (WebBackend):
        also registers check_operator_instructions.
        """
        registry.register(self._defn_notify(),  self._notify)
        registry.register(self._defn_ask(),     self._ask)
        registry.register(self._defn_confirm(), self._confirm)
        if hasattr(self._backend, "get_pending_instructions"):
            registry.register(self._defn_check_instructions(), self._check_instructions)

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def _defn_notify(self) -> ToolDefinition:
        return ToolDefinition(
            name="human_notify",
            description=(
                "Send an informational message to the human operator. "
                "Use this to report status, present an artifact (e.g. a rocket "
                "manifest), or instruct the operator to perform a physical action "
                "(e.g. build the rocket, connect kRPC). Does not wait for a response."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to display to the operator.",
                    }
                },
                "required": ["message"],
            },
        )

    def _defn_ask(self) -> ToolDefinition:
        return ToolDefinition(
            name="human_ask",
            description=(
                "Ask the human operator a question and wait for a typed response. "
                "Use this when you need information only the operator can provide — "
                "e.g. confirmation that the rocket is built, a telemetry reading, "
                "or the result of a manual check. Returns the operator's response as a string."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the operator.",
                    }
                },
                "required": ["question"],
            },
        )

    def _defn_confirm(self) -> ToolDefinition:
        return ToolDefinition(
            name="human_confirm",
            description=(
                "Ask the human operator for a yes/no confirmation and wait for it. "
                "Use this before proceeding with an irreversible action or when "
                "the operator must physically verify something before the agent continues. "
                "Returns 'confirmed' or 'denied'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The confirmation request to present to the operator.",
                    }
                },
                "required": ["message"],
            },
        )

    def _defn_check_instructions(self) -> ToolDefinition:
        return ToolDefinition(
            name="check_operator_instructions",
            description=(
                "Check whether the human operator has sent any unsolicited instructions "
                "or corrections since the last time you checked. Returns a list of "
                "messages, or '(none)' if the queue is empty. Call this periodically "
                "to pick up operator guidance, corrections, or change requests without "
                "waiting to be asked a direct question."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    # ------------------------------------------------------------------
    # Callables (wired to the backend)
    # ------------------------------------------------------------------

    def _notify(self, message: str) -> str:
        self._backend.notify(message)
        return "Message delivered to operator."

    def _ask(self, question: str) -> str:
        return self._backend.ask(question)

    def _confirm(self, message: str) -> str:
        result = self._backend.confirm(message)
        return "confirmed" if result else "denied"

    def _check_instructions(self) -> str:
        msgs = self._backend.get_pending_instructions()
        if not msgs:
            return "(none)"
        return "\n".join(f"[{i+1}] {m}" for i, m in enumerate(msgs))

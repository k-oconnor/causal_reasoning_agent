"""
causal_agent/llm.py

LLM-agnostic adapter layer.

Every concrete backend implements BaseLLM.complete(prompt, system) -> str.
Swapping models is a one-line change in configuration; no other module
is aware of which backend is in use.

Provided adapters
-----------------
MockLLM       – deterministic/canned responses; no API key needed (tests, demos).
OpenAILLM     – OpenAI chat completions (gpt-4o, etc.).
AnthropicLLM  – Anthropic messages API (claude-3-5-sonnet, etc.).
GeminiLLM     – Google Gemini generative AI (gemini-2.0-flash, etc.).
DeepSeekLLM   – DeepSeek API via OpenAI-compatible interface (deepseek-chat, etc.).
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from itertools import cycle
from typing import Any, Iterator, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from causal_agent.tools import LLMResponse, ToolRegistry

log = logging.getLogger("causal_agent.llm")


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseLLM(ABC):
    """
    Minimal interface all LLM backends must satisfy.

    Parameters
    ----------
    prompt  : the user-turn content (already assembled by the caller).
    system  : optional system-prompt override; backends may ignore if unsupported.
    kwargs  : pass-through for backend-specific options (temperature, max_tokens…).
    """

    @abstractmethod
    def complete(self, prompt: str, system: str = "", **kwargs) -> str: ...

    # ------------------------------------------------------------------
    # Logging helpers (call these inside subclass implementations)
    # ------------------------------------------------------------------

    def _log_request(self, prompt_or_messages: object, system: str = "") -> None:
        if log.isEnabledFor(logging.DEBUG):
            text = str(prompt_or_messages)
            log.debug(
                "%r >> system=%r input=%.400s%s",
                self,
                system[:120] if system else "",
                text,
                "..." if len(text) > 400 else "",
            )

    def _log_response(self, content: str, kind: str = "complete") -> None:
        log.info("%r << [%s] %d chars", self, kind, len(content))
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                "%r << %.500s%s",
                self,
                content,
                "..." if len(content) > 500 else "",
            )

    def _log_tool_calls(self, tool_calls: list) -> None:
        names = [tc.name for tc in tool_calls]
        log.info("%r << [tool_calls] %s", self, names)
        if log.isEnabledFor(logging.DEBUG):
            for tc in tool_calls:
                log.debug("%r     call %s(%s)", self, tc.name, tc.arguments)

    def complete_with_tools(
        self,
        messages: list[dict],
        registry: "ToolRegistry",
        system: str = "",
        **kwargs,
    ) -> "LLMResponse":
        """
        Single-turn completion with tool-calling support.

        Returns an LLMResponse with either:
        - tool_calls populated  → caller should execute tools and loop.
        - content populated     → model is done; this is the final answer.

        Subclasses override this to use native function-calling APIs.
        The default raises NotImplementedError; use a backend that supports it.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement complete_with_tools(). "
            "Use OpenAILLM, DeepSeekLLM, AnthropicLLM, or GeminiLLM."
        )

    def complete_structured(
        self,
        prompt: str,
        schema: Mapping[str, Any],
        system: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Return a JSON object matching schema when the backend supports it.

        Base fallback uses prompt-level JSON instructions and local parsing.
        Concrete providers override this with native schema/JSON modes.
        """
        structured_prompt = (
            f"{prompt}\n\n"
            "Return a single JSON object matching this JSON Schema. "
            "Do not include markdown fences or extra text.\n"
            f"{json.dumps(schema, indent=2, sort_keys=True)}"
        )
        raw = self.complete(structured_prompt, system=system, **kwargs)
        return _extract_json_object(raw)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


# ---------------------------------------------------------------------------
# Mock — no network, no key
# ---------------------------------------------------------------------------

class MockLLM(BaseLLM):
    """
    Returns canned responses in round-robin order.

    Useful for unit tests and offline demos.  If no responses are supplied
    the backend echoes a fixed placeholder string.
    """

    _DEFAULTS = [
        '{"intent": "gather information", "action_type": "speak", '
        '"parameters": {"message": "I have no strong read yet — who do you all suspect?"}, '
        '"reasoning": "Early game, probing for reactions."}',

        '{"intent": "cast vote", "action_type": "vote", '
        '"parameters": {"target": "Alice"}, '
        '"reasoning": "Alice has been evasive — voting to eliminate."}',

        '{"intent": "eliminate threat", "action_type": "kill", '
        '"parameters": {"target": "Bob"}, '
        '"reasoning": "Bob is most likely to expose us."}',

        '{"intent": "deflect suspicion", "action_type": "speak", '
        '"parameters": {"message": "I am confident I am a villager — let\'s focus on the quiet players."}, '
        '"reasoning": "Need to shift attention away from myself."}',
    ]

    def __init__(self, responses: list[str] | None = None) -> None:
        self._cycle: Iterator[str] = (
            cycle(responses) if responses else cycle(self._DEFAULTS)
        )

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        self._log_request(prompt, system)
        result = next(self._cycle)
        self._log_response(result)
        return result

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        from causal_agent.tools import LLMResponse
        self._log_request(messages, system)
        content = next(self._cycle)
        self._log_response(content, kind="mock_final")
        return LLMResponse(content=content)


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAILLM(BaseLLM):
    """
    Thin wrapper around the openai SDK chat-completions endpoint.

    Parameters
    ----------
    model   : any OpenAI chat model slug, e.g. "gpt-4o".
    api_key : if None, the SDK reads OPENAI_API_KEY from the environment.
    kwargs  : forwarded to every client.chat.completions.create() call.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        **default_kwargs,
    ) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError("pip install openai") from exc

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._defaults = default_kwargs

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        self._log_request(prompt, system)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        params = {**self._defaults, **kwargs}
        resp = self._client.chat.completions.create(
            model=self._model, messages=messages, **params,
        )
        result = resp.choices[0].message.content or ""
        self._log_response(result)
        return result

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        from causal_agent.tools import LLMResponse, ToolCall
        self._log_request(messages, system)

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        params = {**self._defaults, **kwargs}
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            tools=registry.openai_schemas(),
            **params,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            tcs = [
                ToolCall(id=tc.id, name=tc.function.name,
                         arguments=json.loads(tc.function.arguments))
                for tc in msg.tool_calls
            ]
            self._log_tool_calls(tcs)
            return LLMResponse(tool_calls=tcs)
        result = msg.content or ""
        self._log_response(result)
        return LLMResponse(content=result)

    def complete_structured(
        self,
        prompt: str,
        schema: Mapping[str, Any],
        system: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        params = {**self._defaults, **kwargs}
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "game_plan",
                        "schema": dict(schema),
                        "strict": False,
                    },
                },
                **params,
            )
        except Exception as exc:
            if _supports_prompt_fallback(exc):
                return super().complete_structured(prompt, schema, system=system, **kwargs)
            raise
        return _extract_json_object(resp.choices[0].message.content or "")

    def __repr__(self) -> str:
        return f"OpenAILLM(model={self._model!r})"


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class AnthropicLLM(BaseLLM):
    """
    Thin wrapper around the anthropic SDK messages endpoint.

    Parameters
    ----------
    model      : any Anthropic model slug, e.g. "claude-3-5-sonnet-20241022".
    api_key    : if None, the SDK reads ANTHROPIC_API_KEY from the environment.
    max_tokens : default token budget per call (required by Anthropic API).
    kwargs     : forwarded to every messages.create() call.
    """

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        max_tokens: int = 1024,
        **default_kwargs,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("pip install anthropic") from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._defaults = default_kwargs

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        self._log_request(prompt, system)
        params: dict = {
            "model": self._model,
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "messages": [{"role": "user", "content": prompt}],
            **self._defaults,
            **kwargs,
        }
        if system:
            params["system"] = system

        resp = self._client.messages.create(**params)
        result = resp.content[0].text if resp.content else ""
        self._log_response(result)
        return result

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        from causal_agent.tools import LLMResponse, ToolCall
        self._log_request(messages, system)

        params: dict = {
            "model": self._model,
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "messages": messages,
            "tools": registry.anthropic_schemas(),
            **self._defaults,
            **kwargs,
        }
        if system:
            params["system"] = system

        resp = self._client.messages.create(**params)

        tool_calls = []
        text_content = None
        for block in resp.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
            elif block.type == "text":
                text_content = block.text

        if tool_calls:
            self._log_tool_calls(tool_calls)
            return LLMResponse(tool_calls=tool_calls)
        self._log_response(text_content or "")
        return LLMResponse(content=text_content or "")

    def complete_structured(
        self,
        prompt: str,
        schema: Mapping[str, Any],
        system: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        params: dict = {
            "model": self._model,
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": dict(schema),
                }
            },
            **self._defaults,
            **kwargs,
        }
        if system:
            params["system"] = system

        try:
            resp = self._client.messages.create(**params)
        except Exception as exc:
            if _supports_prompt_fallback(exc):
                return super().complete_structured(prompt, schema, system=system, **kwargs)
            raise
        return _extract_json_object(resp.content[0].text if resp.content else "")

    def __repr__(self) -> str:
        return f"AnthropicLLM(model={self._model!r})"


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

class GeminiLLM(BaseLLM):
    """
    Thin wrapper around the google-genai SDK (google-generativeai >= 0.7).

    Parameters
    ----------
    model   : any Gemini model slug, e.g. "gemini-2.0-flash" or "gemini-1.5-pro".
    api_key : if None, the SDK reads GOOGLE_API_KEY from the environment.
    kwargs  : forwarded to every generate_content() call (temperature, etc.).

    System prompt handling
    ----------------------
    Gemini supports system instructions via the `system_instruction` parameter
    on the GenerativeModel constructor.  When a non-empty system string is
    passed to complete(), a fresh model instance is created with that
    instruction so per-call overrides work without storing state.
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: str | None = None,
        **default_kwargs,
    ) -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError("pip install google-generativeai") from exc

        self._genai = genai
        if api_key:
            genai.configure(api_key=api_key)
        self._model_name = model
        self._defaults = default_kwargs
        # Default model instance (no system instruction).
        self._model = genai.GenerativeModel(model_name=model)

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        self._log_request(prompt, system)
        if system:
            model = self._genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=system,
            )
        else:
            model = self._model

        params = {**self._defaults, **kwargs}
        config = self._genai.types.GenerationConfig(**params) if params else None

        resp = model.generate_content(prompt, generation_config=config)
        result = resp.text if resp.text else ""
        self._log_response(result)
        return result

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        from causal_agent.tools import LLMResponse, ToolCall

        tools = [{"function_declarations": registry.gemini_schemas()}]
        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system or None,
            tools=tools,
        )

        # Convert OpenAI-style message dicts to Gemini Content objects.
        gemini_history = []
        last_user_parts = None
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg.get("content") or ""
            gemini_history.append({"role": role, "parts": [content]})

        # Gemini uses a chat session for multi-turn; send the last user turn.
        if gemini_history and gemini_history[-1]["role"] == "user":
            last_user_parts = gemini_history[-1]["parts"]
            history = gemini_history[:-1]
        else:
            last_user_parts = [""]
            history = gemini_history

        chat = model.start_chat(history=history)
        params = {**self._defaults, **kwargs}
        config = self._genai.types.GenerationConfig(**params) if params else None
        resp = chat.send_message(last_user_parts, generation_config=config)

        tool_calls = []
        for part in resp.parts:
            fc = getattr(part, "function_call", None)
            if fc:
                tool_calls.append(ToolCall(
                    id=fc.name,   # Gemini has no call ID; use name as surrogate
                    name=fc.name,
                    arguments=dict(fc.args),
                ))

        if tool_calls:
            self._log_tool_calls(tool_calls)
            return LLMResponse(tool_calls=tool_calls)
        result = resp.text if resp.text else ""
        self._log_response(result)
        return LLMResponse(content=result)

    def complete_structured(
        self,
        prompt: str,
        schema: Mapping[str, Any],
        system: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        if system:
            model = self._genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=system,
            )
        else:
            model = self._model

        params = {**self._defaults, **kwargs}
        try:
            config = self._genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=dict(schema),
                **params,
            )
            resp = model.generate_content(prompt, generation_config=config)
        except Exception as exc:
            if _supports_prompt_fallback(exc):
                return super().complete_structured(prompt, schema, system=system, **kwargs)
            raise
        return _extract_json_object(resp.text if resp.text else "")

    def __repr__(self) -> str:
        return f"GeminiLLM(model={self._model_name!r})"


# ---------------------------------------------------------------------------
# DeepSeek — OpenAI-compatible endpoint
# ---------------------------------------------------------------------------

class DeepSeekLLM(BaseLLM):
    """
    Thin wrapper around the DeepSeek API using the OpenAI-compatible interface.

    DeepSeek exposes an OpenAI-compatible REST endpoint, so we reuse the
    openai SDK pointed at https://api.deepseek.com/v1.

    Parameters
    ----------
    model   : DeepSeek model slug, e.g. "deepseek-chat" or "deepseek-reasoner".
    api_key : if None, reads DEEPSEEK_API_KEY from the environment.
    kwargs  : forwarded to every chat.completions.create() call.
    """

    _BASE_URL = "https://api.deepseek.com/v1"

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: str | None = None,
        **default_kwargs,
    ) -> None:
        import os
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("pip install openai") from exc

        resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not resolved_key:
            raise ValueError(
                "DeepSeek API key not found. "
                "Pass api_key= or set DEEPSEEK_API_KEY in your environment."
            )

        self._client = OpenAI(api_key=resolved_key, base_url=self._BASE_URL)
        self._model = model
        self._defaults = default_kwargs

    def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        self._log_request(prompt, system)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        params = {"temperature": 0.7, "max_tokens": 1000, **self._defaults, **kwargs}
        resp = self._client.chat.completions.create(
            model=self._model, messages=messages, **params,
        )
        result = resp.choices[0].message.content or ""
        self._log_response(result)
        return result

    def complete_with_tools(self, messages, registry, system="", **kwargs):
        from causal_agent.tools import LLMResponse, ToolCall
        self._log_request(messages, system)

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        params = {"temperature": 0.7, "max_tokens": 1000, **self._defaults, **kwargs}
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            tools=registry.openai_schemas(),
            **params,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            tcs = [
                ToolCall(id=tc.id, name=tc.function.name,
                         arguments=json.loads(tc.function.arguments))
                for tc in msg.tool_calls
            ]
            self._log_tool_calls(tcs)
            return LLMResponse(tool_calls=tcs)
        result = msg.content or ""
        self._log_response(result)
        return LLMResponse(content=result)

    def complete_structured(
        self,
        prompt: str,
        schema: Mapping[str, Any],
        system: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        schema_prompt = (
            f"{prompt}\n\n"
            "Return JSON matching this schema exactly:\n"
            f"{json.dumps(schema, indent=2, sort_keys=True)}"
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": schema_prompt})

        params = {
            "temperature": 0.7,
            "max_tokens": 1000,
            **self._defaults,
            **kwargs,
        }
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"},
                **params,
            )
        except Exception as exc:
            if _supports_prompt_fallback(exc):
                return super().complete_structured(prompt, schema, system=system, **kwargs)
            raise
        return _extract_json_object(resp.choices[0].message.content or "")

    def __repr__(self) -> str:
        return f"DeepSeekLLM(model={self._model!r})"


# ---------------------------------------------------------------------------
# Structured-output helpers
# ---------------------------------------------------------------------------

def _extract_json_object(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError(f"LLM did not return a JSON object: {raw!r}")
        data = json.loads(match.group())

    if not isinstance(data, dict):
        raise ValueError(f"LLM structured output must be a JSON object: {data!r}")
    return data


def _supports_prompt_fallback(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = [
        "response_format",
        "json_schema",
        "output_config",
        "response_schema",
        "unexpected keyword",
        "unsupported",
        "not supported",
    ]
    return any(marker in message for marker in markers)

"""
causal_agent/research_tools.py

Callable implementations for external research tools.

Provides ready-to-register (ToolDefinition, callable) pairs for:
  - web_search  : Tavily search API — returns ranked results with extracted content.
  - fetch_page  : Jina Reader — fetches any URL as clean markdown (no API key needed).

Usage
-----
    from causal_agent.research_tools import ResearchTools

    rt = ResearchTools(tavily_api_key=os.getenv("TAVILY_API_KEY"))
    rt.register_all(registry)
"""

from __future__ import annotations

import os
from typing import Any

from causal_agent.tools import ToolDefinition, ToolRegistry


class ResearchTools:
    """
    Produces web research tools backed by Tavily and Jina Reader.

    Parameters
    ----------
    tavily_api_key : Tavily API key. Falls back to TAVILY_API_KEY env var.
    max_results    : Max search results returned per query (default 5).
    """

    JINA_BASE = "https://r.jina.ai/"

    def __init__(
        self,
        tavily_api_key: str | None = None,
        max_results: int = 5,
    ) -> None:
        self._api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Tavily API key not found. "
                "Pass tavily_api_key= or set TAVILY_API_KEY in your environment."
            )
        self._max_results = max_results
        self._client = None  # lazy init

    def register_all(self, registry: ToolRegistry) -> None:
        """Register web_search and fetch_page into `registry`."""
        registry.register(self._defn_web_search(), self._web_search)
        registry.register(self._defn_fetch_page(), self._fetch_page)

    # ------------------------------------------------------------------
    # Tool: web_search
    # ------------------------------------------------------------------

    def _defn_web_search(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description=(
                "Search the web for current information. Returns a ranked list of "
                "results with titles, URLs, and extracted content. Use this to find "
                "documentation, part statistics, forum discussions, tutorials, or any "
                "information you need to ground your plan in real data."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific for better results.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": f"Number of results to return (default {self._max_results}, max 10).",
                    },
                },
                "required": ["query"],
            },
        )

    def _web_search(self, query: str, max_results: int | None = None) -> str:
        client = self._get_client()
        n = min(max_results or self._max_results, 10)

        try:
            response = client.search(
                query=query,
                max_results=n,
                include_answer=True,
                include_raw_content=False,
            )
        except Exception as exc:
            return f"Search failed: {exc}"

        lines: list[str] = []

        if response.get("answer"):
            lines.append(f"Summary: {response['answer']}\n")

        results = response.get("results", [])
        if not results:
            return "No results found."

        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', 'Untitled')}")
            lines.append(f"    URL: {r.get('url', '')}")
            content = r.get("content", "").strip()
            if content:
                # Trim long content to keep context window manageable.
                if len(content) > 600:
                    content = content[:600] + "…"
                lines.append(f"    {content}")
            lines.append("")

        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Tool: fetch_page
    # ------------------------------------------------------------------

    def _defn_fetch_page(self) -> ToolDefinition:
        return ToolDefinition(
            name="fetch_page",
            description=(
                "Fetch the full content of a specific URL as clean markdown text. "
                "Use this when web_search returns a promising URL and you need the "
                "complete page — e.g. a KSP wiki part page, a forum post, or API docs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Truncate response to this many characters (default 4000).",
                    },
                },
                "required": ["url"],
            },
        )

    def _fetch_page(self, url: str, max_chars: int = 4000) -> str:
        import requests  # stdlib-ish; always available after pip install

        jina_url = self.JINA_BASE + url
        try:
            resp = requests.get(
                jina_url,
                headers={"Accept": "text/markdown"},
                timeout=15,
            )
            resp.raise_for_status()
            text = resp.text.strip()
        except Exception as exc:
            return f"Failed to fetch '{url}': {exc}"

        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[… truncated at {max_chars} chars]"

        return text

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_client(self):
        if self._client is None:
            try:
                from tavily import TavilyClient
            except ImportError as exc:
                raise ImportError("pip install tavily-python") from exc
            self._client = TavilyClient(api_key=self._api_key)
        return self._client

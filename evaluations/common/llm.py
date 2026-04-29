from __future__ import annotations

import argparse
from typing import Sequence

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from causal_agent import AnthropicLLM, DeepSeekLLM, GeminiLLM, MockLLM, OpenAILLM


def add_llm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", choices=["mock", "openai", "anthropic", "gemini", "deepseek"], default="mock")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--openai-key", default=None)
    parser.add_argument("--openai-model", default="gpt-4o")
    parser.add_argument("--anthropic-key", default=None)
    parser.add_argument("--anthropic-model", default="claude-3-5-sonnet-20241022")
    parser.add_argument("--gemini-key", default=None)
    parser.add_argument("--gemini-model", default="gemini-2.0-flash")
    parser.add_argument("--deepseek-key", default=None)
    parser.add_argument("--deepseek-model", default="deepseek-chat")


def build_llm(args: argparse.Namespace, mock_responses: Sequence[str]):
    if args.model == "openai":
        return OpenAILLM(model=args.openai_model, api_key=args.openai_key, temperature=args.temperature)
    if args.model == "anthropic":
        return AnthropicLLM(
            model=args.anthropic_model,
            api_key=args.anthropic_key,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
    if args.model == "gemini":
        return GeminiLLM(model=args.gemini_model, api_key=args.gemini_key, temperature=args.temperature)
    if args.model == "deepseek":
        return DeepSeekLLM(model=args.deepseek_model, api_key=args.deepseek_key, temperature=args.temperature)
    return MockLLM(list(mock_responses))


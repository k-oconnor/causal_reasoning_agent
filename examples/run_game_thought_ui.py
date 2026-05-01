"""
Run the local live dashboard for 2048 and Mastermind decision traces.

Usage:
    python -m examples.run_game_thought_ui --model deepseek --port 8766
    python -m examples.run_game_thought_ui --model mock --port 8766
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from causal_agent import DeepSeekLLM, MockLLM  # noqa: E402
from causal_agent.game_trace import GameRunConfig, mock_responses_for_game  # noqa: E402
from causal_agent.game_ui_server import create_game_ui_app  # noqa: E402

try:  # noqa: E402
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the game reasoning dashboard.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--game", choices=["2048", "mastermind"], default="2048")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-turns", type=int, default=100)
    parser.add_argument("--mastermind-max-attempts", type=int, default=10)
    parser.add_argument("--mastermind-code-length", type=int, default=4)
    parser.add_argument("--mastermind-num-colors", type=int, default=6)
    parser.add_argument(
        "--mastermind-duplicates-allowed",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--model", choices=["deepseek", "mock"], default="deepseek")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--deepseek-key", default=None)
    parser.add_argument("--deepseek-model", default="deepseek-v4-flash")
    parser.add_argument(
        "--log-dir",
        default=None,
        help=(
            "Directory for per-move JSONL traces. Defaults to "
            "logs/evaluations/<game>/ui/<model>."
        ),
    )
    parser.add_argument("--episode", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    import uvicorn

    args = parse_args()
    default_config = GameRunConfig(
        game=args.game,
        seed=args.seed,
        max_turns=args.max_turns,
        mastermind_colors=(
            "red",
            "blue",
            "green",
            "yellow",
            "orange",
            "purple",
            "pink",
            "brown",
            "black",
            "white",
        )[: args.mastermind_num_colors],
        mastermind_code_length=args.mastermind_code_length,
        mastermind_max_attempts=args.mastermind_max_attempts,
        mastermind_duplicates_allowed=args.mastermind_duplicates_allowed,
        episode=args.episode,
    )

    def llm_factory(config: GameRunConfig):
        if args.model == "mock":
            return MockLLM(mock_responses_for_game(config.game))
        return DeepSeekLLM(
            model=args.deepseek_model,
            api_key=args.deepseek_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )

    def log_dir_factory(config: GameRunConfig) -> str:
        if args.log_dir:
            return args.log_dir
        return str(Path("logs") / "evaluations" / config.game / "ui" / args.model)

    app = create_game_ui_app(
        llm_factory=llm_factory,
        default_config=default_config,
        log_dir_factory=log_dir_factory,
    )
    url = f"http://{args.host}:{args.port}"
    print(f"Game reasoning UI ready at {url}")
    if args.open_browser:
        webbrowser.open(url)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

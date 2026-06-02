"""
examples/run_pd_tournament.py

Run the Kripke-reasoning PD agent against AltruAgent tournaments.

Usage
-----
# Join the first available queue and play until tournament ends:
python -m examples.run_pd_tournament

# Join a specific queue by ID:
python -m examples.run_pd_tournament --queue-id <queue_id>

# Join an already-known tournament:
python -m examples.run_pd_tournament --tournament-id <tournament_id>

# Play a single session directly (for testing):
python -m examples.run_pd_tournament --session-id <sid> --game-server-url http://...

Credentials are loaded from .env (ALTRUAGENT_API_KEY, ALTRUAGENT_AGENT_NAME).
Model defaults to DeepSeek; pass --model mock for offline testing.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Allow running as `python -m examples.run_pd_tournament`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from causal_agent.log_config import setup_logging
from causal_agent.pd_agent import PDAgent, CONTROL_PLANE


def build_llm(model_name: str):
    if model_name == "mock":
        from causal_agent.llm import MockLLM
        return MockLLM(responses=[
            '{"action": 0, "reasoning": "Cooperating by default in mock mode."}',
            '{"action": 0, "reasoning": "Mock cooperate."}',
            '{"send": false, "reasoning": "Mock: no message."}',
        ])
    if model_name == "deepseek":
        from causal_agent.llm import DeepSeekLLM
        return DeepSeekLLM(model="deepseek-chat")
    if model_name == "openai":
        from causal_agent.llm import OpenAILLM
        return OpenAILLM()
    if model_name == "anthropic":
        from causal_agent.llm import AnthropicLLM
        return AnthropicLLM()
    raise ValueError(f"Unknown model: {model_name!r}. Choose: deepseek, openai, anthropic, mock")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run the Kripke PD agent on AltruAgent tournaments."
    )
    parser.add_argument("--api-key", help="Override ALTRUAGENT_API_KEY from env")
    parser.add_argument("--agent-name", help="Override ALTRUAGENT_AGENT_NAME from env")
    parser.add_argument("--queue-id", help="Join this queue ID (lists queues if omitted)")
    parser.add_argument("--tournament-id", help="Join/continue this specific tournament ID")
    parser.add_argument("--session-id", help="Play a single session directly (for testing)")
    parser.add_argument(
        "--game-server-url",
        default="http://GameAp-Servi-tOMiXPVqPFIe-185462629.us-west-2.elb.amazonaws.com",
        help="Game server URL (only needed with --session-id)",
    )
    parser.add_argument(
        "--model", default="deepseek",
        choices=["deepseek", "openai", "anthropic", "mock"],
        help="LLM backend (default: deepseek)",
    )
    parser.add_argument(
        "--memory-dir", default="pd_memory",
        help="Directory to persist per-opponent Kripke/memory files (default: pd_memory/)",
    )
    parser.add_argument(
        "--inject", metavar="PAYLOAD",
        help=(
            "Send a prompt-injection message in round 1 messaging phase. "
            "Pass a named payload (system, admin, xml, polite, threat, role) "
            "or a custom string. Named payloads: "
            + ", ".join(f"'{k}'" for k in PDAgent.INJECTION_PAYLOADS)
        ),
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING"])
    args = parser.parse_args()

    setup_logging(args.log_level)
    log = logging.getLogger("run_pd_tournament")

    api_key = args.api_key or os.getenv("ALTRUAGENT_API_KEY", "")
    agent_name = args.agent_name or os.getenv("ALTRUAGENT_AGENT_NAME", "koconnor_test")

    if not api_key:
        sys.exit("ALTRUAGENT_API_KEY not set. Add it to .env or the environment.")

    llm = build_llm(args.model)

    injection_message = None
    if args.inject:
        injection_message = PDAgent.INJECTION_PAYLOADS.get(args.inject, args.inject)
        print(f"Injection mode: {injection_message[:80]}...")

    agent = PDAgent(
        api_key=api_key,
        llm=llm,
        agent_name=agent_name,
        memory_dir=Path(args.memory_dir),
        injection_message=injection_message,
    )

    print(f"Logging in as {agent_name}…")
    agent.login()

    if not agent.check_claimed():
        sys.exit("Agent is not claimed. Have the instructor claim it first.")

    print("Agent claimed. Ready to play.\n")

    # --- Single session mode (testing) ---
    if args.session_id:
        print(f"Playing single session: {args.session_id}")
        agent.play_game(
            game_server_url=args.game_server_url,
            session_id=args.session_id,
        )
        return

    # --- Tournament mode ---
    tournament_id = args.tournament_id

    if not tournament_id:
        queue_id = args.queue_id

        if not queue_id:
            # List available queues and pick the first one
            queues = agent.list_queues()
            if not queues:
                sys.exit("No queues available. Ask the instructor to create one.")
            print("Available queues:")
            for q in queues:
                print(f"  {q.get('id') or q.get('queue_id')}: {q.get('name', '(unnamed)')}")
            queue_id = str(queues[0].get("id") or queues[0].get("queue_id", ""))
            if not queue_id:
                sys.exit("Could not determine queue_id from queues response.")
            print(f"\nAuto-selected queue: {queue_id}")

        print(f"Joining queue {queue_id}…")
        tournament_id = agent.join_queue(queue_id)
        print(f"In queue → tournament_id: {tournament_id}")
        print("Waiting for tournament to start (polling queue)…")

        # Poll queue until tournament starts
        import requests
        while True:
            try:
                resp = requests.get(
                    f"{CONTROL_PLANE}/queues/{queue_id}",
                    headers=agent._headers(),
                    timeout=10,
                )
                data = resp.json()
                waiting = data.get("current_waiting_tournament")
                if waiting:
                    secs = waiting.get("seconds_until_start")
                    if secs is not None:
                        print(f"  Tournament starts in {secs}s…", end="\r")
                    else:
                        print("  Waiting for participants…", end="\r")
                else:
                    print("\nTournament is starting!")
                    break
            except Exception as exc:
                log.warning("Queue poll error: %s", exc)
            time.sleep(5)

    print(f"\nRunning tournament: {tournament_id}")
    agent.run_tournament(tournament_id)


if __name__ == "__main__":
    main()

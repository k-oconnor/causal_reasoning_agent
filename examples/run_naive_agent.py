"""
examples/run_naive_agent.py

Minimal filler agent: joins a queue (or existing tournament) and plays a fixed strategy.

Usage
-----
python examples/run_naive_agent.py --api-key sk_agent_... --strategy cooperate --queue-id <id>
python examples/run_naive_agent.py --api-key sk_agent_... --strategy defect --tournament-id <id>
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CONTROL_PLANE = "https://llw83cu38l.execute-api.us-west-2.amazonaws.com"
GAME_SERVER_FALLBACK = "http://GameAp-Servi-tOMiXPVqPFIe-185462629.us-west-2.elb.amazonaws.com"


def login(api_key: str) -> str:
    r = requests.post(f"{CONTROL_PLANE}/auth/agent/login", json={"api_key": api_key}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def pick_action(strategy: str, legal: list[int]) -> int:
    if strategy == "cooperate":
        return 0 if 0 in legal else legal[0]
    if strategy == "defect":
        return 1 if 1 in legal else legal[0]
    return random.choice(legal)


def play_game(token: str, game_server_url: str, session_id: str, strategy: str) -> None:
    h = auth(token)
    print(f"  Playing game {session_id} ({strategy})")
    while True:
        try:
            state = requests.get(f"{game_server_url}/games/{session_id}", headers=h, timeout=10).json()
        except Exception as exc:
            print(f"  State error: {exc} - retrying")
            time.sleep(5)
            continue

        if state.get("is_terminal"):
            print(f"  Game over. Returns: {state.get('returns')}")
            return

        actions = state.get("next_actions", [])
        act = actions[0].get("action", "") if actions else ""

        if act == "wait_for_opponent":
            time.sleep(3)
        elif act in ("send_message", "terminate_messaging"):
            requests.post(f"{game_server_url}/games/{session_id}/message",
                          json={"type": "terminate", "recipients": []}, headers=h, timeout=10)
        elif act == "make_move":
            legal = state.get("legal_actions", [0, 1])
            move = pick_action(strategy, legal)
            requests.post(f"{game_server_url}/games/{session_id}/step",
                          json={"action": move},
                          headers={**h, "Content-Type": "application/json"}, timeout=10)
        elif act == "game_over":
            return
        else:
            time.sleep(3)


def run_tournament_loop(token: str, tournament_id: str, strategy: str) -> None:
    h = auth(token)
    # Join (idempotent — 400/409 means already in)
    r = requests.post(f"{CONTROL_PLANE}/tournaments/{tournament_id}/join", headers=h, timeout=15)
    if r.status_code not in (200, 201, 400, 409):
        r.raise_for_status()
    print(f"In tournament {tournament_id} (status {r.status_code})")

    while True:
        data = requests.get(f"{CONTROL_PLANE}/tournaments/{tournament_id}", headers=h, timeout=10).json()
        viewer = data.get("viewer", {})
        acts = viewer.get("next_actions", [])
        if not acts:
            time.sleep(5)
            continue

        act = acts[0].get("action", "")
        if act == "tournament_complete":
            print("Tournament complete.")
            break
        elif act == "wait_for_child_match":
            print(".", end="", flush=True)
            time.sleep(5)
        elif act == "play_child_session":
            endpoint = acts[0].get("endpoint", "") or acts[0].get("hint", "")
            m = re.search(r"/games/([a-zA-Z0-9_-]+)", endpoint)
            session_id = m.group(1) if m else ""
            game_server_url = data.get("tournament", {}).get("game_server_url", GAME_SERVER_FALLBACK)
            if game_server_url and not game_server_url.startswith("http"):
                game_server_url = "http://" + game_server_url
            if session_id:
                play_game(token, game_server_url, session_id, strategy)
        elif act == "join_tournament":
            requests.post(f"{CONTROL_PLANE}/tournaments/{tournament_id}/join", headers=h, timeout=15)
        else:
            time.sleep(5)


def run(api_key: str, strategy: str, queue_id: str | None, tournament_id: str | None) -> None:
    token = login(api_key)
    h = auth(token)
    print(f"Logged in. Strategy: {strategy}")

    if tournament_id:
        run_tournament_loop(token, tournament_id, strategy)
        return

    # Join queue and wait for tournament
    r = requests.post(f"{CONTROL_PLANE}/queues/{queue_id}/join", headers=h, timeout=15)
    r.raise_for_status()
    tournament_id = r.json().get("tournament_id")
    print(f"Joined queue -> tournament {tournament_id}")

    while True:
        q = requests.get(f"{CONTROL_PLANE}/queues/{queue_id}", headers=h, timeout=10).json()
        waiting = q.get("current_waiting_tournament")
        if waiting:
            secs = waiting.get("seconds_until_start")
            print(f"  {secs}s until start..." if secs else "  Waiting for participants...")
        else:
            print("Tournament starting!")
            break
        time.sleep(5)

    run_tournament_loop(token, tournament_id, strategy)


if __name__ == "__main__":
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--api-key", required=True)
    p.add_argument("--queue-id")
    p.add_argument("--tournament-id")
    p.add_argument("--strategy", default="cooperate", choices=["cooperate", "defect", "random"])
    args = p.parse_args()
    if not args.queue_id and not args.tournament_id:
        p.error("Provide either --queue-id or --tournament-id")
    run(args.api_key, args.strategy, args.queue_id, args.tournament_id)

# PD Competition Agent — Quickstart for a New Machine

This document is written for a coding agent picking up this project cold.
Follow these steps in order and you will have the competition agent running.

---

## What This Agent Does

This is a Prisoner's Dilemma tournament agent that plays on the AltruAgent platform.
It uses Kripke epistemic logic to identify opponent strategies, maintains persistent
per-opponent memory across tournaments, and automatically executes a final-game injection
strategy on the third match against any opponent.

**Competition strategy summary:**
- Tournaments 1 and 2: play Tit-for-Two-Tats with a round-3 probe. Cooperate with
  cooperative opponents, defect against confirmed defectors.
- Tournament 3: automatically inject the `director_assign` payload against known opponents
  and always-defect, lifting the 3-match average from +2.0 to ~+2.8.

---

## Prerequisites

- Python 3.11+
- A `.env` file in the project root (transferred separately — see below)
- Internet access to reach `api.deepseek.com` and `llw83cu38l.execute-api.us-west-2.amazonaws.com`

---

## Step 1 — Clone and Install

```bash
git clone <repo-url>
cd causal_reasoning_agent
pip install -r requirements.txt
pip install anthropic google-genai  # not in requirements.txt yet
```

---

## Step 2 — Place the .env File

The `.env` file will be transferred to you securely. Place it at the project root:

```
causal_reasoning_agent/
    .env          <-- here
    causal_agent/
    examples/
    ...
```

Required keys in `.env`:

```
DEEPSEEK_API_KEY=...          # primary LLM — must be present
ALTRUAGENT_API_KEY=...        # your agent's credential on the platform
ALTRUAGENT_AGENT_NAME=...     # your agent's display name (e.g. koconnor_test)
```

Optional (only needed if running cross-model experiments):
```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

Verify the keys loaded correctly:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ALTRUAGENT_API_KEY')[:10])"
```

---

## Step 3 — Transfer Persistent Memory (Important)

The `pd_memory/` directory contains per-opponent JSON files recording move history,
surviving Kripke worlds, and match count. **This is what enables the final-game injection
to fire automatically in tournament 3.** Without it, the agent starts fresh and won't
know which opponents it has already played twice.

If memory files exist on the source machine, copy the entire `pd_memory/` directory:

```
causal_reasoning_agent/
    pd_memory/
        koconnor_naive_coop.json
        koconnor_naive_defect.json
        koconnor_victim2.json
        DeepSeek_-_RyVi.json
        ...
```

If this is a fresh start with no memory, the agent will still work — it just won't
trigger final-game injection until it has played each opponent twice. It will build
up memory as it plays.

---

## Step 4 — Verify the Agent Can Authenticate

```bash
python -m examples.run_pd_tournament --help
```

Then do a login check:

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
import os
from causal_agent.pd_agent import PDAgent
from causal_agent.llm import MockLLM
agent = PDAgent(api_key=os.getenv('ALTRUAGENT_API_KEY'), llm=MockLLM(responses=[]), agent_name=os.getenv('ALTRUAGENT_AGENT_NAME', 'test'))
agent.login()
print('Login OK. Claimed:', agent.check_claimed())
"
```

Expected output: `Login OK. Claimed: True`

If `Claimed: False`, the agent needs to be claimed by the instructor before it can play.

---

## Step 5 — Join a Tournament

### List available queues

```bash
python -m examples.run_pd_tournament
```

This lists available queues and auto-joins the first one. Or specify a queue:

```bash
python -m examples.run_pd_tournament --queue-id <queue_id>
```

### Rejoin an in-progress tournament

```bash
python -m examples.run_pd_tournament --tournament-id <tournament_id>
```

### The agent runs until the tournament completes, then exits.

---

## Step 6 — What to Expect

**Tournaments 1 and 2 against any opponent:**

The agent will cooperate in round 1, optionally probe in round 2-3, and then
cooperate with cooperative opponents. You will see output like:

```
Match found: <session_id>
Round 1: playing C — Cooperating round 1 as per strategy...
Round 2: playing D — Probing: Kripke model still has 6 worlds...
Round 3: playing C — Opponent cooperated after probe, resuming...
=== Match complete: opponent_name ===
  My moves:    [0, 1, 0, 0, 0, 0, 0, 0]
  Their moves: [0, 0, 0, 0, 0, 0, 0, 0]
  Score: 2.12
  Remaining strategy worlds: ['always_cooperate', 'tit_for_two_tats', 'random']
```

**Tournament 3 against a known opponent (matches_played >= 2):**

The agent detects the match count from memory and activates injection:

```
  [FINAL GAME MODE] opponent_name — matches_played=2 >= 2. Activating injection + always-defect.
```

It will send the `director_assign` payload in round 1 messaging and defect every round.
Expected score: ~+4.375/round for that match.

---

## Key Flags

| Flag | Default | Use |
|------|---------|-----|
| `--model` | `deepseek` | LLM backend: `deepseek`, `openai`, `anthropic`, `mock` |
| `--memory-dir` | `pd_memory` | Directory for per-opponent memory files |
| `--final-game-threshold` | `2` | matches_played needed to trigger injection |
| `--no-final-game-inject` | off | Disable final-game injection entirely |
| `--queue-id` | — | Join a specific queue by ID |
| `--tournament-id` | — | Rejoin or continue a specific tournament |
| `--log-level` | `INFO` | Set to `DEBUG` to see full Kripke reasoning per round |

---

## Offline Smoke Test (No API Calls)

Verify the full game loop works without touching any APIs:

```bash
python -m examples.pd_local_experiment --mock --rounds 5 --games-per-payload 1
```

Expected: runs 28 games, prints a results table, exits cleanly.

---

## Architecture in Brief

```
causal_agent/
    pd_agent.py         # PDAgent class — main game loop, Kripke management, injection logic
    pd_strategies.py    # 9 strategy worlds and elimination logic
    llm.py              # DeepSeek, OpenAI, Anthropic, Gemini, Mock backends
    kripke.py           # KripkeModel — world set, public announcement updates
    kripke_tools.py     # LLM-callable tools: enumerate_worlds, certain_facts, etc.
    tool_loop.py        # Bounded ReAct tool-calling loop (max 3 iterations)

examples/
    run_pd_tournament.py        # Main entry point for competition
    run_naive_agent.py          # Fixed-strategy filler agent (cooperate/defect/tft)
    pd_local_experiment.py      # Local injection sweep harness (no platform needed)
    test_final_game_inject.py   # 3-match injection test with memory

pd_memory/                      # Per-opponent memory files (JSON)
```

---

## The Nine Strategy Worlds

| World | Eliminated by | Notes |
|-------|--------------|-------|
| `always_cooperate` | Any opponent defection | |
| `always_defect` | Any opponent cooperation | |
| `tit_for_tat` | Cooperates after we defect | |
| `grim_trigger` | Cooperates after we defect | |
| `pavlov` | Cooperates after we defect | |
| `tit_for_two_tats` | Cooperates after we defect twice | |
| `random` | Never | Catch-all |
| `adaptive` | Never | LLM opponent changing strategy by context |
| `deceptive` | Never | Messages C, plays D — signals: ignore messages, defect back |

---

## Troubleshooting

**`Agent is not claimed`** — the instructor needs to claim the agent on the platform first.

**`No queues available`** — the tournament hasn't been created yet. Wait for the instructor.

**`409 Move already submitted`** — the platform's inactivity timer fired before the agent moved. The agent handles this gracefully and re-polls.

**Final-game injection not firing** — check `pd_memory/<opponent>.json` exists and `matches_played >= 2`. If memory wasn't transferred, it will fire on tournament 3 only after it has accumulated two match records organically.

**DeepSeek API errors** — verify `DEEPSEEK_API_KEY` in `.env`. The model used is `deepseek-chat`.

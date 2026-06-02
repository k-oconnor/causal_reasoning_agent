"""
causal_agent/pd_tournament_strategy.py

Tournament-level strategy analysis for repeated PD.

Uses leaderboard statistics (wins, losses, draws, avg payoff) to:
  1. Infer likely opponent strategy before a match starts.
  2. Narrow the initial Kripke worlds based on that prior.
  3. Recommend strategic targeting (who to defect against this tournament).

Score signatures in an 8-round match:
  AlwaysDefect vs Cooperator  : D gets +5/round (WIN),  C gets -1/round (LOSS)
  AlwaysDefect vs AlwaysDefect: both get 0/round (DRAW, 0.0)
  Cooperator   vs Cooperator  : both get +2/round (DRAW, 2.0)
  TfT          vs Cooperator  : both get +2/round (DRAW, 2.0)
  TfT          vs AlwaysDefect: TfT -1 round 1 then 0 (near-LOSS, ≈ -0.125)
  Grim         vs Cooperator  : both +2/round (DRAW, 2.0)
  Grim         vs AlwaysDefect: Grim -1 then 0 (near-LOSS)

So in a round-robin:
  - AlwaysDefect  → many WINS if cooperators present; DRAW (0.0) vs other defectors
  - AlwaysCooperate → many LOSSES vs defectors; DRAW (2.0) vs cooperators
  - TfT/Grim      → mostly DRAWs at 2.0 (vs cooperators) or near-losses vs defectors
  - Pavlov        → similar to TfT in cooperative field
"""

from __future__ import annotations

from causal_agent.pd_strategies import STRATEGIES


# ---------------------------------------------------------------------------
# Strategy inference
# ---------------------------------------------------------------------------

MIN_GAMES_FOR_INFERENCE = 16  # need at least ~2 full matches


def infer_worlds_from_stats(
    wins: int,
    losses: int,
    draws: int,
    avg_score: float,
    total_games: int,
) -> list[str]:
    """
    Return the subset of strategy worlds still plausible given tournament stats.

    Falls back to all worlds when data is insufficient.
    """
    if total_games < MIN_GAMES_FOR_INFERENCE:
        return list(STRATEGIES.keys())

    total_matches = wins + losses + draws
    if total_matches == 0:
        return list(STRATEGIES.keys())

    win_rate  = wins   / total_matches
    loss_rate = losses / total_matches
    draw_rate = draws  / total_matches

    # Exploiter signature: wins lots, high avg
    # AlwaysDefect or aggressive random
    if win_rate >= 0.35 and avg_score >= 2.5:
        return ["always_defect", "random"]

    # Pushover signature: loses a lot, low or negative avg
    # AlwaysCooperate or very forgiving TfT2
    if loss_rate >= 0.35 and avg_score <= 0.8:
        return ["always_cooperate", "tit_for_two_tats", "random"]

    # Cooperative reciprocator: mostly draws near +2
    # TfT, Grim, Pavlov, AlwaysCooperate all look like this against cooperative field
    if draw_rate >= 0.55 and 1.5 <= avg_score <= 2.5:
        return ["always_cooperate", "tit_for_tat", "grim_trigger", "pavlov", "tit_for_two_tats", "random"]

    # Mutual-defection draws at ~0
    if draw_rate >= 0.55 and avg_score <= 0.3:
        return ["always_defect", "random"]

    # Mixed / unclear
    return list(STRATEGIES.keys())


def describe_inferred_strategy(worlds: list[str]) -> str:
    """Human-readable label for a narrowed world set."""
    if worlds == ["always_defect", "random"]:
        return "likely exploiter / always-defect"
    if set(worlds) <= {"always_cooperate", "tit_for_two_tats", "random"}:
        return "likely always-cooperate or very forgiving"
    if set(worlds) <= {"always_cooperate", "tit_for_tat", "grim_trigger", "pavlov", "tit_for_two_tats", "random"}:
        return "likely cooperative reciprocator (TfT-family)"
    return "strategy unclear"


# ---------------------------------------------------------------------------
# Targeting recommendations
# ---------------------------------------------------------------------------

def targeting_advice(
    my_name: str,
    my_avg: float,
    participants: list[dict],
) -> str:
    """
    Recommend who to target for defection and who to cooperate with,
    based on current standings.

    participants: list of dicts with keys name, avg_score, wins, losses, draws, total_games
    """
    if not participants:
        return "No leaderboard data available."

    sorted_p = sorted(participants, key=lambda x: x["avg_score"], reverse=True)
    my_rank = next((i + 1 for i, p in enumerate(sorted_p) if p["name"] == my_name), None)

    lines = [f"Tournament analysis (you: {my_name}, rank #{my_rank}, avg={my_avg:.3f}):"]
    lines.append("")
    lines.append("Recommended strategy per opponent:")

    for p in sorted_p:
        name = p["name"]
        if name == my_name:
            continue
        avg = p["avg_score"]
        wins = p.get("wins", 0) or 0
        losses = p.get("losses", 0) or 0
        draws = p.get("draws", 0) or 0
        total_games = p.get("total_games", 0) or 0
        worlds = infer_worlds_from_stats(wins, losses, draws, avg, total_games)
        desc = describe_inferred_strategy(worlds)

        # Strategic recommendation
        if "always_defect" in worlds and len(worlds) <= 2:
            rec = "DEFECT — likely exploiter; cooperation gives you -1/round"
        elif set(worlds) <= {"always_cooperate", "tit_for_two_tats", "random"} and avg < 0.8:
            rec = "COOPERATE — they cooperate; mutual +2/round"
        elif avg > my_avg + 0.5:
            rec = "CONSIDER DEFECT — they lead you; D gives +5 and hurts their avg"
        elif avg < my_avg - 0.5:
            rec = "COOPERATE — you lead them; safe +2 without risk"
        else:
            rec = "COOPERATE — similar standing; mutual cooperation best long-term"

        lines.append(
            f"  {name}: avg={avg:.2f}, W={wins} L={losses} D={draws} | "
            f"{desc} | {rec}"
        )

    return "\n".join(lines)

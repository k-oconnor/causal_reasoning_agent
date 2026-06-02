"""
causal_agent/pd_strategies.py

Opponent strategy definitions for repeated prisoner's dilemma.

Each strategy predicts the OPPONENT's next move given the history of completed
rounds from our agent's point of view:
  my_history   – our moves in completed rounds (list[int], 0=cooperate, 1=defect)
  their_history – opponent's moves in completed rounds (list[int])

Returns 0 (cooperate), 1 (defect), or None (ambiguous — do not eliminate this world).

Called BEFORE the current round: histories contain all completed rounds so far.
"""

from __future__ import annotations
from typing import Callable, Optional


def _always_cooperate(my: list[int], them: list[int]) -> Optional[int]:
    return 0


def _always_defect(my: list[int], them: list[int]) -> Optional[int]:
    return 1


def _tit_for_tat(my: list[int], them: list[int]) -> Optional[int]:
    # Cooperate on round 1, then mirror OUR last move.
    # (TfT players copy whatever we did to them last round.)
    return 0 if not my else my[-1]


def _grim_trigger(my: list[int], them: list[int]) -> Optional[int]:
    # Cooperate until we defect even once, then defect forever.
    return 1 if any(m == 1 for m in my) else 0


def _pavlov(my: list[int], them: list[int]) -> Optional[int]:
    # Win-stay, lose-shift from the opponent's perspective.
    # "Win" = received R(+2) or T(+5) last round → repeat last move.
    # "Lose" = received S(-1) or P(0) last round → switch.
    #
    # Payoff table for the opponent:
    #   them=C, us=C → R=+2 (win → stay → C)
    #   them=D, us=C → T=+5 (win → stay → D)
    #   them=C, us=D → S=-1 (lose → shift → D)
    #   them=D, us=D → P=0  (lose → shift → C)
    if not them:
        return 0  # cooperate on round 1
    t, m = them[-1], my[-1]
    if t == 0 and m == 0:
        return 0  # C,C → win → stay C
    if t == 1 and m == 0:
        return 1  # D,C → win → stay D
    if t == 0 and m == 1:
        return 1  # C,D → lose → shift to D
    return 0      # D,D → lose → shift to C


def _tit_for_two_tats(my: list[int], them: list[int]) -> Optional[int]:
    # Only retaliates after we defect TWICE in a row.
    if len(my) < 2:
        return 0
    return 1 if my[-1] == 1 and my[-2] == 1 else 0


def _random(my: list[int], them: list[int]) -> Optional[int]:
    # Unpredictable — never eliminated from the Kripke model.
    return None


STRATEGIES: dict[str, Callable[[list[int], list[int]], Optional[int]]] = {
    "always_cooperate":   _always_cooperate,
    "always_defect":      _always_defect,
    "tit_for_tat":        _tit_for_tat,
    "grim_trigger":       _grim_trigger,
    "pavlov":             _pavlov,
    "tit_for_two_tats":   _tit_for_two_tats,
    "random":             _random,
}

STRATEGY_DESCRIPTIONS: dict[str, str] = {
    "always_cooperate":  "Always cooperates. Never defects regardless of history.",
    "always_defect":     "Always defects. Pure defector — best response is to defect back.",
    "tit_for_tat":       "Cooperates on round 1, then mirrors our last action. Punishes defection exactly once.",
    "grim_trigger":      "Cooperates until we defect even once, then defects forever. Very punitive.",
    "pavlov":            "Win-stay, lose-shift. Rewards mutual cooperation; recovers from mutual defection.",
    "tit_for_two_tats":  "Only retaliates after we defect TWICE in a row. More forgiving than TfT.",
    "random":            "Moves appear random or follow an unidentified pattern. Cannot be eliminated.",
}


def predict_move(strategy: str, my_history: list[int], their_history: list[int]) -> Optional[int]:
    fn = STRATEGIES.get(strategy)
    if fn is None:
        return None
    return fn(my_history, their_history)


def eliminate_inconsistent(
    remaining: list[str],
    my_history: list[int],
    their_history: list[int],
) -> list[str]:
    """
    Remove strategies whose prediction for the latest round contradicts the
    observed opponent move.  Histories must already include the round being
    evaluated (i.e. call this AFTER appending the observed move).

    We predict using the N-1 history and check against the Nth observed move.
    """
    if not their_history:
        return remaining
    observed = their_history[-1]
    prior_my = my_history[:-1]    # history before the round we're checking
    prior_them = their_history[:-1]

    surviving = []
    for strategy in remaining:
        predicted = predict_move(strategy, prior_my, prior_them)
        if predicted is None or predicted == observed:
            surviving.append(strategy)
    return surviving

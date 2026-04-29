"""
games/werewolf/env.py

Minimal Werewolf game environment.

Setup
-----
N players (one is the AI agent, the rest are rule-based NPCs).
Roles are assigned at construction: one werewolf (possibly the AI agent),
the rest villagers.

Phases
------
DAY_DISCUSS  – each player speaks once in turn order.
DAY_VOTE     – each player votes to eliminate one other player.
NIGHT        – if the AI agent is the werewolf, they pick a target to kill.
               Otherwise the werewolf NPC picks randomly.

Win conditions
--------------
Village wins : all werewolves are eliminated.
Werewolf wins: werewolves >= surviving villagers.

Kripke model (initial_kripke)
------------------------------
Propositions: role_<player> ∈ {"werewolf", "villager"} for each player.
Our agent knows their own role; for each other player we create one world
per possible role they could occupy (consistent with global role counts).
Accessibility for other agents is derived from what they have been told —
villagers only know their own role, so their accessible worlds are all
assignments consistent with that.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, create_model

from causal_agent.actions import ActionSpec, _ForbidExtraConfig, string_enum
from games.base import GameEnvironment
from causal_agent.kripke import KripkeModel, World
from causal_agent.acting import GameAction


# ---------------------------------------------------------------------------
# Game phases
# ---------------------------------------------------------------------------

class Phase(str, Enum):
    DAY_DISCUSS = "day_discuss"
    DAY_VOTE    = "day_vote"
    NIGHT       = "night"
    ENDED       = "ended"


class SpeakPayload(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Public message to say during the discussion phase.",
    )

    class Config:
        extra = "forbid"


# ---------------------------------------------------------------------------
# NPC behaviour
# ---------------------------------------------------------------------------

def _npc_speak(player: str, others: list[str], rng: random.Random) -> str:
    templates = [
        f"I haven't decided who to suspect yet.",
        f"I think {rng.choice(others)} seems a bit off.",
        f"I'm not sure, but we should vote carefully.",
        f"Trust me, I'm a villager.",
        f"Someone here is lying — I can feel it.",
    ]
    return rng.choice(templates)


def _npc_vote(
    player: str,
    alive: list[str],
    role: str,
    rng: random.Random,
) -> str:
    candidates = [p for p in alive if p != player]
    if not candidates:
        return player
    if role == "werewolf":
        return rng.choice(candidates)
    return rng.choice(candidates)


# ---------------------------------------------------------------------------
# WerewolfEnv
# ---------------------------------------------------------------------------

@dataclass
class _PlayerState:
    name: str
    role: str
    alive: bool = True
    voted_for: str = ""
    spoke_this_phase: bool = False


class WerewolfEnv(GameEnvironment):
    """
    Parameters
    ----------
    players       : ordered list of all player names; agent must be in this list.
    agent_id      : which player the AI agent controls.
    n_werewolves  : how many werewolves to assign (default 1).
    seed          : RNG seed for reproducibility.
    """

    def __init__(
        self,
        players: list[str],
        agent_id: str,
        n_werewolves: int = 1,
        seed: int | None = None,
    ) -> None:
        assert agent_id in players, f"{agent_id!r} must be in players list."
        assert 1 <= n_werewolves < len(players)

        self._rng = random.Random(seed)
        self._agent_id = agent_id
        self._all_players = list(players)

        # Assign roles
        shuffled = list(players)
        self._rng.shuffle(shuffled)
        werewolves = set(shuffled[:n_werewolves])

        self._players: dict[str, _PlayerState] = {
            p: _PlayerState(name=p, role="werewolf" if p in werewolves else "villager")
            for p in players
        }
        self._n_werewolves = n_werewolves

        # Public game log (all players can read this)
        self._public_log: list[dict] = []
        self._phase: Phase = Phase.DAY_DISCUSS
        self._turn: int = 0
        self._speak_order: list[str] = list(players)
        self._speak_index: int = 0
        self._winner: str | None = None

        self._run_npc_speaks_if_needed()

    # ------------------------------------------------------------------
    # GameEnvironment interface
    # ------------------------------------------------------------------

    def observe(self, agent_id: str) -> dict:
        """
        Return what the agent can see right now.
        """
        state = self._players[agent_id]

        # Dead agents receive a terminal signal immediately.
        if not state.alive:
            winner = self._winner or "unknown"
            role = state.role
            won = (role == "werewolf" and winner == "werewolf") or \
                  (role == "villager" and winner == "village")
            return {
                "kind": "terminal",
                "source": "env",
                "content": (
                    f"You were eliminated. "
                    f"Winner: {winner}. You {'won' if won else 'lost'}."
                ),
                "facts": {},
                "terminal": True,
                "reward": 1.0 if won else -1.0,
                "alive_players": self._alive_players(),
            }

        alive_players = self._alive_players()

        obs: dict[str, Any] = {
            "kind": "observation",
            "source": "env",
            "content": (
                f"Phase={self._phase.value} | "
                f"Alive={alive_players} | "
                f"Your role={state.role}"
            ),
            "phase": self._phase.value,
            "alive_players": alive_players,
            "public_log": list(self._public_log[-10:]),   # last 10 events
            "facts": {
                # Only include propositions present in Kripke worlds.
                # Phase is certain/global state — omit to avoid eliminating worlds.
                f"role_{agent_id}": state.role,
            },
            "terminal": self._phase == Phase.ENDED,
            "reward": self._compute_reward(agent_id) if self._phase == Phase.ENDED else 0.0,
        }

        return obs

    def step(self, agent_id: str, action: GameAction) -> dict:
        """Apply the agent's action and advance the game state."""
        result: dict = {"kind": "observation", "source": "env", "content": "", "facts": {}}

        if self._phase == Phase.ENDED:
            result["content"] = "Game already ended."
            result["terminal"] = True
            return result

        if action.action_type == "speak":
            result = self._handle_speak(agent_id, action.payload.get("message", ""))
        elif action.action_type == "vote":
            result = self._handle_vote(agent_id, action.payload.get("target", ""))
        elif action.action_type == "kill":
            result = self._handle_kill(agent_id, action.payload.get("target", ""))
        else:
            result["content"] = f"Unknown action: {action.action_type}"

        self._check_win_condition()
        self._advance_phase_if_needed()
        result["terminal"] = self._phase == Phase.ENDED
        result["reward"] = self._compute_reward(agent_id) if result.get("terminal") else 0.0
        result.setdefault("facts", {})
        return result

    def action_specs(self, agent_id: str) -> list[ActionSpec]:
        if not self._players[agent_id].alive:
            return []
        if self._phase == Phase.DAY_DISCUSS:
            # The agent speaks when it is their turn in the speak order.
            if self._current_speaker() == agent_id:
                return [
                    ActionSpec(
                        action_type="speak",
                        description="Say one public discussion message.",
                        payload_model=SpeakPayload,
                        examples=[{
                            "message": (
                                "I do not have a strong read yet. "
                                "Who has said something inconsistent?"
                            )
                        }],
                    )
                ]
            return []
        if self._phase == Phase.DAY_VOTE:
            if not self._players[agent_id].voted_for:
                candidates = [p for p in self._alive_players() if p != agent_id]
                if not candidates:
                    return []
                return [
                    ActionSpec(
                        action_type="vote",
                        description="Vote to eliminate one living player other than yourself.",
                        payload_model=_target_payload_model("WerewolfVotePayload", candidates),
                        examples=[{"target": candidates[0]}],
                    )
                ]
            return []
        if self._phase == Phase.NIGHT:
            if self._players[agent_id].role == "werewolf":
                candidates = [p for p in self._alive_players() if p != agent_id]
                if not candidates:
                    return []
                return [
                    ActionSpec(
                        action_type="kill",
                        description="As werewolf, kill one living player other than yourself.",
                        payload_model=_target_payload_model("WerewolfKillPayload", candidates),
                        examples=[{"target": candidates[0]}],
                    )
                ]
            return []
        return []

    @property
    def is_terminal(self) -> bool:
        return self._phase == Phase.ENDED

    def initial_kripke(self, agent_id: str) -> KripkeModel:
        """
        Build the initial epistemic model for agent_id.

        The agent knows their own role.  For each other player, their role
        is uncertain — we create one world per consistent global assignment.

        With N players and K werewolves the number of worlds is C(N-1, K) if
        the agent is a villager, or C(N-1, K-1) if the agent is the werewolf.
        For small games this is tractable.
        """
        from itertools import combinations

        my_role = self._players[agent_id].role
        others = [p for p in self._all_players if p != agent_id]
        n_ww_among_others = (
            self._n_werewolves - 1 if my_role == "werewolf" else self._n_werewolves
        )

        worlds: list[World] = []
        for i, ww_subset in enumerate(combinations(others, n_ww_among_others)):
            ww_set = set(ww_subset)
            # Worlds encode only role assignments — uncertain propositions.
            # Global facts (phase, turn) are certain and not stored per-world.
            facts: dict[str, Any] = {f"role_{agent_id}": my_role}
            for p in others:
                facts[f"role_{p}"] = "werewolf" if p in ww_set else "villager"
            worlds.append(World.from_dict(f"w{i}", facts))

        # Accessibility: for each other agent, they know their own role.
        # Two worlds are accessible from each other for agent X iff they
        # agree on role_X.
        accessibility: dict[str, dict[str, set[str]]] = {}
        for agent in others:
            relations: dict[str, set[str]] = {}
            for w in worlds:
                my_role_in_w = w.get(f"role_{agent}")
                relations[w.id] = {
                    v.id for v in worlds if v.get(f"role_{agent}") == my_role_in_w
                }
            accessibility[agent] = relations

        return KripkeModel(worlds=worlds, accessibility=accessibility)

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def _current_speaker(self) -> str | None:
        alive = set(self._alive_players())
        while self._speak_index < len(self._speak_order):
            candidate = self._speak_order[self._speak_index]
            if candidate in alive:
                return candidate
            self._speak_index += 1
        return None

    def _run_npc_speaks_if_needed(self) -> None:
        """Advance NPC speakers until it's the agent's turn (or phase ends)."""
        while True:
            speaker = self._current_speaker()
            if speaker is None or speaker == self._agent_id:
                break
            msg = _npc_speak(speaker, self._alive_players_except(speaker), self._rng)
            self._public_log.append({
                "kind": "social", "source": speaker, "content": msg,
            })
            self._speak_index += 1

    def _advance_phase_if_needed(self) -> None:
        if self._phase == Phase.DAY_DISCUSS:
            if self._current_speaker() is None:
                self._transition_to_vote()
        elif self._phase == Phase.DAY_VOTE:
            alive = self._alive_players()
            if all(self._players[p].voted_for for p in alive):
                self._resolve_vote()
        elif self._phase == Phase.NIGHT:
            if self._players[self._agent_id].role != "werewolf":
                self._run_npc_night_kill()

    def _transition_to_vote(self) -> None:
        self._phase = Phase.DAY_VOTE
        self._public_log.append({
            "kind": "phase_change", "source": "env",
            "content": "Day discussion over — time to vote.",
        })
        self._run_npc_votes_if_needed()

    def _run_npc_votes_if_needed(self) -> None:
        for p in self._alive_players():
            if p == self._agent_id:
                continue
            if not self._players[p].voted_for:
                target = _npc_vote(p, self._alive_players(), self._players[p].role, self._rng)
                self._players[p].voted_for = target
                self._public_log.append({
                    "kind": "social", "source": p,
                    "content": f"{p} votes to eliminate {target}.",
                })

    def _resolve_vote(self) -> None:
        tally: dict[str, int] = {}
        for p in self._alive_players():
            v = self._players[p].voted_for
            tally[v] = tally.get(v, 0) + 1

        if not tally:
            return
        eliminated = max(tally, key=lambda x: (tally[x], self._rng.random()))
        self._players[eliminated].alive = False
        self._public_log.append({
            "kind": "observation", "source": "env",
            "content": f"{eliminated} was eliminated by vote. Role: {self._players[eliminated].role}.",
        })

        # Reset votes; transition to night if game continues.
        for p in self._players.values():
            p.voted_for = ""

        if not self.is_terminal:
            self._phase = Phase.NIGHT
            self._public_log.append({
                "kind": "phase_change", "source": "env",
                "content": "Night falls.",
            })
            # If the agent is a villager the werewolf NPC acts immediately,
            # so the agent never needs a "night" action and morning begins
            # on the next observe() call.
            if self._players[self._agent_id].role != "werewolf":
                self._run_npc_night_kill()

    def _run_npc_night_kill(self) -> None:
        """NPC werewolf acts at night when the agent is a villager."""
        ww = next(
            (p for p in self._alive_players() if self._players[p].role == "werewolf"),
            None,
        )
        if ww is None:
            return
        targets = [p for p in self._alive_players() if self._players[p].role != "werewolf"]
        if not targets:
            return
        target = self._rng.choice(targets)
        self._players[target].alive = False
        self._public_log.append({
            "kind": "observation", "source": "env",
            "content": f"{target} was killed in the night.",
        })
        self._check_win_condition()
        if not self.is_terminal:
            self._start_new_day()

    def _start_new_day(self) -> None:
        self._phase = Phase.DAY_DISCUSS
        self._speak_order = self._alive_players()
        self._speak_index = 0
        self._public_log.append({
            "kind": "phase_change", "source": "env",
            "content": "A new day begins.",
        })
        self._run_npc_speaks_if_needed()

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _handle_speak(self, agent_id: str, message: str) -> dict:
        self._public_log.append({
            "kind": "social", "source": agent_id, "content": message,
        })
        self._speak_index += 1
        self._run_npc_speaks_if_needed()
        return {
            "kind": "observation", "source": "env",
            "content": f"{agent_id} said: {message!r}",
            "facts": {},
        }

    def _handle_vote(self, agent_id: str, target: str) -> dict:
        candidates = [p for p in self._alive_players() if p != agent_id]
        if target not in candidates:
            # Graceful fallback: pick a random valid target so the game advances.
            target = self._rng.choice(candidates) if candidates else agent_id
        self._players[agent_id].voted_for = target
        self._public_log.append({
            "kind": "social", "source": agent_id,
            "content": f"{agent_id} votes to eliminate {target}.",
        })
        self._run_npc_votes_if_needed()
        return {
            "kind": "observation", "source": "env",
            "content": f"{agent_id} voted for {target}.",
            "facts": {f"voted_{agent_id}": target},
        }

    def _handle_kill(self, agent_id: str, target: str) -> dict:
        if self._players[agent_id].role != "werewolf":
            return {
                "kind": "illegal_move", "source": "env",
                "content": "Only werewolves can kill at night.",
                "facts": {},
            }
        candidates = [p for p in self._alive_players() if p != agent_id]
        if target not in candidates:
            target = self._rng.choice(candidates) if candidates else agent_id
        self._players[target].alive = False
        self._public_log.append({
            "kind": "observation", "source": "env",
            "content": f"{target} was killed in the night.",
        })
        self._check_win_condition()
        if not self.is_terminal:
            self._start_new_day()
        return {
            "kind": "observation", "source": "env",
            "content": f"You killed {target}.",
            "facts": {f"eliminated_{target}": True},
        }

    # ------------------------------------------------------------------
    # Win condition
    # ------------------------------------------------------------------

    def _check_win_condition(self) -> None:
        alive = self._alive_players()
        alive_ww = [p for p in alive if self._players[p].role == "werewolf"]
        alive_vl = [p for p in alive if self._players[p].role == "villager"]

        if not alive_ww:
            self._winner = "village"
            self._phase = Phase.ENDED
            self._public_log.append({
                "kind": "terminal", "source": "env",
                "content": "Village wins! All werewolves eliminated.",
            })
        elif len(alive_ww) >= len(alive_vl):
            self._winner = "werewolf"
            self._phase = Phase.ENDED
            self._public_log.append({
                "kind": "terminal", "source": "env",
                "content": "Werewolves win!",
            })

    def _compute_reward(self, agent_id: str) -> float:
        if self._winner is None:
            return 0.0
        role = self._players[agent_id].role
        if (role == "werewolf" and self._winner == "werewolf") or \
           (role == "villager" and self._winner == "village"):
            return 1.0
        return -1.0

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _alive_players(self) -> list[str]:
        return [p for p, s in self._players.items() if s.alive]

    def _alive_players_except(self, exclude: str) -> list[str]:
        return [p for p in self._alive_players() if p != exclude]

    def __repr__(self) -> str:
        return (
            f"WerewolfEnv(players={self._all_players}, "
            f"phase={self._phase.value}, "
            f"alive={self._alive_players()})"
        )


def _target_payload_model(name: str, candidates: list[str]) -> type[BaseModel]:
    target_type = string_enum(f"{name}Target", candidates)
    return create_model(
        name,
        __config__=_ForbidExtraConfig,
        target=(
            target_type,
            Field(..., description=f"One of: {', '.join(candidates)}."),
        ),
    )

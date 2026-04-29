# Game Environment Authoring Guide

This directory contains game adapters for the causal reasoning agent. A good
adapter does more than satisfy the abstract methods: it tells the planner what
kind of game it is, exposes useful tools, and gives cheap counterfactuals when
they are available.

## Required Interface

Every game must subclass `GameEnvironment` from `games/base.py` and implement:

- `observe(agent_id) -> dict`: return the current percept. Include `kind`,
  `source`, `content`, `facts`, `reward`, and `terminal` where possible.
- `step(agent_id, action) -> dict`: apply a `GameAction` and return feedback in
  the same raw shape used by `observe`.
- `action_specs(agent_id) -> list[ActionSpec]`: return legal structured actions
  for the current turn. Use payload schemas and examples that match what the env
  will accept.
- `valid_actions(agent_id) -> list[str]`: inherited compatibility helper; it
  should not need overriding if `action_specs` is correct.
- `is_terminal -> bool`: report whether the game has ended.
- `initial_kripke(agent_id) -> KripkeModel`: return a meaningful hidden-state
  model for hidden-information games, or rely on the default one-world model for
  fully observable games.

## Optional Hooks

Override these when they improve decision quality:

- `system_prompt() -> str`: use a game-specific prompt when a generic epistemic
  framing is misleading or too weak. Strategy games should name the core
  heuristics the model should use.
- `tools(agent_id) -> ToolRegistry | None`: register game-specific tools for
  simulation, scoring, candidate filtering, or search. Hidden-information games
  should call `ToolRegistry().enable_kripke_tools()` so the planner attaches live
  Kripke inspection tools.
- `preview(agent_id, action) -> dict | None`: return read-only consequences for
  cheap deterministic actions. Do not reveal hidden information that the agent
  would not know before acting.

## Decision Tree

- Hidden information? Build a non-trivial `initial_kripke` and enable Kripke
  tools through the registry.
- Deterministic and cheaply simulable? Implement `preview()` for candidate
  action examples.
- Decision quality benefits from lookahead or scoring? Register a game-specific
  toolset.
- Optimal strategy is not obvious to a generic LLM? Override `system_prompt()`
  with concise, concrete strategy guidance.
- Eval runner uses LLM policy? Use `evaluations.common.build_planner` so the
  prompt, tools, and preview hook are wired consistently.

## Worked Examples

### Werewolf

Werewolf is hidden-information and social. Its default prompt is the generic
reactive epistemic prompt, which fits the domain. Its `initial_kripke` creates
one world per possible role assignment, and `tools()` enables live Kripke tools.
It does not implement `preview()` because social and NPC consequences are not a
cheap deterministic one-step calculation.

### Mastermind

Mastermind is hidden-information plus cheap symbolic simulation. Its Kripke
model has one world per candidate code, and feedback facts shrink those worlds.
Its tools count candidates, enumerate candidates, simulate feedback filters, and
score guesses by expected information. It uses a custom prompt focused on
candidate partitions and entropy. It does not preview actual guesses because
that would reveal secret feedback before committing.

### 2048

2048 is fully observable and deterministic until the random tile spawn. Kripke
is decorative, so the custom prompt tells the model to focus on corner anchoring,
monotonic gradients, merge quality, and empty cells. `preview()` compares every
currently legal slide before the spawn, and the toolset adds simulation,
heuristic board scoring, empty-cell counts, and shallow expectimax.

## Eval Runner Registration

New game eval runners should live under `evaluations/<game>/eval.py` and reuse:

- `build_planner(env, llm, agent_id=...)` for LLM policies.
- `add_llm_args(parser)` and `build_llm(args, mock_responses)` for backend
  selection.
- `TraceLogger` and `write_summary` for JSONL traces and summaries.
- `plan_action_with_retry(...)` when bypassing `Orchestrator`, so malformed LLM
  actions are retried once and logged as illegal moves.

Keep runners small: create the env, build the policy or planner, loop over
episodes, log each turn, and summarize benchmark metrics.

## Checklist Before Merging A New Env

- `action_specs()` payload schemas exactly match what `step()` accepts.
- `ActionSpec.examples` cover important legal choices, especially for preview.
- `system_prompt()` is overridden if the generic Werewolf-style prompt is a bad
  frame for the game.
- `tools()` registers domain tools when explicit scoring, filtering, or search
  would help.
- `preview()` exists for cheap deterministic actions and does not leak hidden
  information.
- `initial_kripke()` is non-trivial only when there is hidden information to
  represent.
- The eval runner is registered under `evaluations/<game>/eval.py`.
- Smoke tests cover env construction, action validation, and at least one short
  eval path.

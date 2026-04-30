# Causal Reasoning Agent

An **LLM-agnostic agentic framework** for tasks that need deliberate planning, tool use, grounded iteration, and optional epistemic state (Kripke models). Model providers stay interchangeable; evals inject goals, tools, and reference docs.

The **planning phase** (`ResearchPlanner`) frames the agent as a scientist: hypothesise, instrument, execute with an operator, analyse logged evidence, post-mortem, and iterate. Domain-specific scripts (e.g. Kerbal Space Program via kRPC) sit beside classic demos (Werewolf, 2048, Mastermind).

## Team

- Mohammed Aksari  
- Helen Yuan  
- Kevin Nam  
- Kevin O'Connor  

---

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in keys you need

# Demos (games)
python -m examples.run_werewolf --model mock
python -m examples.run_werewolf --model openai
python -m examples.run_2048
python -m examples.run_mastermind

# KSP Mun orbit eval (scientific loop + workspace artifacts)
python -m examples.run_ksp_planning --model openai --log-file ksp_run.log --max-iter 60
# Default human feedback is CLI. Use --feedback file or --ui as needed.

# Benchmark-style evals
python -m evaluations.game_2048.eval --policy greedy --episodes 20
python -m evaluations.mastermind.eval --policy knuth --episodes 20
```

---

## Repository layout

```
causal_reasoning_agent/
├── causal_agent/
│   ├── kripke.py / kripke_tools.py   # symbolic worlds + optional LLM tools
│   ├── llm.py                        # Mock, OpenAI, Anthropic, Gemini, DeepSeek
│   ├── prompts.py                    # PLANNING_SYSTEM (scientific loop), REACTIVE_SYSTEM
│   ├── tools.py                      # ToolRegistry, ToolDefinition, dispatch
│   ├── research_tools.py             # web_search (Tavily), fetch_page (Jina)
│   ├── research_planner.py           # ReAct planning loop, plan_complete hook
│   ├── file_tools.py                 # save_file, read_file, list_files → agent_workspace/
│   ├── human_interface.py            # CLI / file / web / silent backends
│   ├── ui_server.py                  # FastAPI + WebSocket operator UI (optional)
│   ├── memory.py
│   ├── planning.py / acting.py / orchestration.py / feedback.py
│   └── log_config.py
├── skills/                           # Markdown reference (see Skills below)
├── agent_workspace/                  # sandbox for agent-written artifacts (.gitkeep)
├── artifacts/ksp_mun_eval/           # frozen DeepSeek / GPT run snapshots + narrative
├── ksp_eval/ksp_mun_orbit_agent_instructions.md
├── tools/dump_ksp_parts.py           # regenerate skills/ksp_parts.md from local KSP GameData
├── examples/run_ksp_planning.py      # KSP eval driver
├── examples/run_werewolf.py …
├── games/ …
├── evaluations/ …
├── .env.example
└── requirements.txt
```

---

## KSP Mun eval (high level)

1. **Goal** — text of `ksp_eval/ksp_mun_orbit_agent_instructions.md` plus a system addendum in `examples/run_ksp_planning.py`.  
2. **Tools** — research (`web_search`, `fetch_page`), files (`save_file`, `read_file`, `list_files`), human (`human_notify`, `human_ask`, `human_confirm`), plus `plan_complete` to stop the loop cleanly on confirmed mission success.  
3. **Artifacts per attempt** — `hypotheses_N.md`, `manifest_attempt_N.md` (required every attempt; use a **stub** if the rocket is unchanged — see addendum), `flight_attempt_N.py`, telemetry/burns/events logs written by the script, then `postmortem_N.md` after analysis.  
4. **Skills** — Technical docs (`krpc_*`, `orbital_mechanics`, `spacecraft_control`, `mission_planning`, `self_instrumentation`, `ksp_parts`) load into the prompt; methodology docs are copied to `agent_workspace/SKILL_*.md` for on-demand `read_file` to save context.  
5. **Archived runs** — `artifacts/ksp_mun_eval/` contains `deepseek_run_1/`, `gpt_run_1/`, `gpt_run_2/`, plus `README.md` and `PERFORMANCE_NARRATIVE.md`.

Regenerate part stats from **your** install:

```bash
python tools/dump_ksp_parts.py   # writes skills/ksp_parts.md
```

---

## Examples vs evaluations

`examples/` — short demos. `evaluations/` — multi-episode benchmarks with JSONL traces under `logs/evaluations/`.

---

## Supported LLM backends

| Flag | Class | Env var |
|---|---|---|
| `--model mock` | `MockLLM` | — |
| `--model openai` | `OpenAILLM` | `OPENAI_API_KEY` |
| `--model anthropic` | `AnthropicLLM` | `ANTHROPIC_API_KEY` |
| `--model gemini` | `GeminiLLM` | `GOOGLE_API_KEY` |
| `--model deepseek` | `DeepSeekLLM` | `DEEPSEEK_API_KEY` |

`OpenAILLM` maps `max_tokens` → `max_completion_tokens` for newer models (e.g. `gpt-5.x`). `ResearchPlanner` defaults to `max_tokens=16384` per completion.

All real backends implement `complete`, `complete_with_tools`, and optional `complete_structured`.

```python
class BaseLLM(ABC):
    def complete(self, prompt: str, system: str = "", **kwargs) -> str: ...
    def complete_with_tools(self, messages, registry, system: str = "", **kwargs) -> LLMResponse: ...
    def complete_structured(self, prompt: str, schema: dict, system: str = "", **kwargs) -> dict: ...
```

`LLMResponse` is either tool calls (loop continues) or string `content` (final answer).

---

## Architecture

**Planning phase** — `ResearchPlanner`: messages + `ToolRegistry` → `complete_with_tools` loop until final text or `plan_complete`. Logs tool calls to `MemoryStore` when provided.

**Reactive loop** — `Orchestrator` + `Planner` + `Actor` for turn-based games (unchanged).

Planning is **eval-agnostic**: only the injected system prompt, skills, and registry change.

```
goal + system + skills
        → ResearchPlanner.run()
            → LLM + tools (research, files, human, …)
            → messages grow each iteration (watch context size on long evals)
        → PlanningResult(plan, iterations, tool_calls, truncated?)
```

### Minimal wiring (conceptual)

```python
from pathlib import Path
from causal_agent import (
    setup_logging, OpenAILLM, ToolRegistry,
    ResearchTools, HumanInterface, FileTools,
    ResearchPlanner, MemoryStore, PLANNING_SYSTEM,
)

setup_logging("INFO", load_dotenv=True)
llm = OpenAILLM()  # or DeepSeekLLM(), etc.
registry = ToolRegistry()
ResearchTools().register_all(registry)

workspace = Path("agent_workspace")
FileTools(workspace=workspace).register_all(registry)
HumanInterface(backend="cli").register_all(registry)  # or "file", or backend="web"

planner = ResearchPlanner(
    llm=llm,
    registry=registry,
    system_prompt=PLANNING_SYSTEM + "\n\n## Your eval addendum…",
    skill_docs=skill_strings,
    memory=MemoryStore(),
    max_iterations=40,
    max_tokens=16384,
)
result = planner.run(goal="…")
print(result.plan)
```

---

## Tool system

| Area | Tools |
|---|---|
| Research | `web_search`, `fetch_page` |
| Workspace | `save_file`, `read_file`, `list_files` (paths confined to workspace root) |
| Human | `human_notify`, `human_ask`, `human_confirm`; optional `check_operator_instructions` with web UI |
| Planning | `plan_complete(summary)` — terminates loop on confirmed success |

**Epistemic tools (`KripkeToolset`)** — optional; register with a `lambda: model` getter if your eval builds a `KripkeModel`. Exposes `kripke_certain_facts`, `kripke_simulate_intervention`, etc. Not wired in `run_ksp_planning.py` by default.

**Human backends**

- `cli` — prompts on stderr; reads from `CON` / `/dev/tty` when possible (avoids polluted stdin).  
- `file` — writes `WAITING_FOR_OPERATOR.txt`, polls `OPERATOR_RESPONSE.txt` (with stability delay).  
- `web` — local FastAPI server + buffered WebSocket replay (`causal_agent/ui_server.py`).  
- `silent` — fixed replies for tests.

---

## Skills

`skills/*.md` supply reference material. For KSP runs, `examples/run_ksp_planning.load_skills()` injects **technical** docs into the first user message and writes **methodology** docs into `agent_workspace/SKILL_*.md` so the model can load them only when needed (smaller fixed prompt, smaller risk of context blow-ups).

Typical technical set: `krpc_basics`, `spacecraft_control`, `orbital_mechanics`, `mission_planning`, `krpc_expressions`, `self_instrumentation`, `ksp_parts`.  
On-demand in workspace: `SKILL_postmortem_writing.md`, `SKILL_data_analysis.md`, `SKILL_workspace_workflow.md`.

---

## Logging

```python
from causal_agent import setup_logging
setup_logging("INFO")
setup_logging("DEBUG", log_file="run.log")
```

Namespace: `causal_agent.*`.

---

## System prompts

| Constant | Role |
|---|---|
| `PLANNING_SYSTEM` | Scientist identity, mandatory loop (hypothesise → … → iterate), tool categories, termination rules |
| `REACTIVE_SYSTEM` | Turn-by-turn JSON plans for the reactive game loop |

Eval specifics belong in an **addendum** concatenated in the driver script, not in the base strings.

---

## Symbolic state and Kripke frames

Planning can be grounded in explicit possible-worlds structure (`kripke.py`): worlds, accessibility relations per agent, interventions as world/edge updates. `KripkeToolset` exposes queries to the LLM when registered. Optional for evals; the KSP driver does not register these tools unless you add them.

---

## The five pillars (reactive loop)

For **games**, orchestration ties observe → feedback → memory → Kripke → planning → acting → `env.step`. Use one shared `MemoryStore` across planning and execution if an eval has both phases. `memory.summarise_episode(llm)` can compress logs between episodes.

The **KSP eval** is mostly planning-phase only: memory still records tool calls if you pass `MemoryStore()`.

---

Together: **planning** prepares work through tools and workspace files; **games** use the reactive stack; everything stays **LLM-agnostic** at the seams.

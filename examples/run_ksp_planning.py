"""
examples/run_ksp_planning.py

Run the ResearchPlanner against the KSP Mun orbit eval spec.

Usage
-----
    python -m examples.run_ksp_planning                    # DeepSeek (default)
    python -m examples.run_ksp_planning --model openai
    python -m examples.run_ksp_planning --model anthropic
    python -m examples.run_ksp_planning --model gemini

    # Cap research iterations (useful for quick smoke tests):
    python -m examples.run_ksp_planning --max-iter 10

    # Save the final plan to a file:
    python -m examples.run_ksp_planning --output plan.md

    # Mirror all logging to a file:
    python -m examples.run_ksp_planning --log-file ksp_run.log

Output
------
The planner will research the mission (KSP wiki, dV maps, kRPC docs, etc.),
reason over the requirements, and produce a complete rocket manifest and
flight script. The final plan is printed to stdout (and optionally written
to --output).
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
EVAL_SPEC = ROOT / "ksp_eval" / "ksp_mun_orbit_agent_instructions.md"
SKILLS_DIR = ROOT / "skills"


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def load_skills() -> list[str]:
    """Load technical skills into the system prompt.

    Methodology/process skills are instead copied to agent_workspace/ with a
    SKILL_ prefix so the agent can read them on demand via read_file() without
    bloating the system prompt on every call.
    """
    if not SKILLS_DIR.exists():
        return []

    # These go directly into the system prompt (technical reference, high reuse).
    PROMPT_SKILLS = {
        "krpc_basics",
        "spacecraft_control",
        "orbital_mechanics",
        "mission_planning",
        "krpc_expressions",
        "ksp_parts",
        "self_instrumentation",
    }

    # These are copied to agent_workspace as SKILL_*.md — readable on demand.
    WORKSPACE_SKILLS = {
        "postmortem_writing",
        "data_analysis",
        "workspace_workflow",
    }

    docs = []
    ws_root = ROOT / "agent_workspace"
    ws_root.mkdir(exist_ok=True)

    for md in sorted(SKILLS_DIR.glob("*.md")):
        content = md.read_text(encoding="utf-8").strip()
        if not content:
            continue
        if md.stem in PROMPT_SKILLS:
            docs.append(f"### {md.stem}\n\n{content}")
        elif md.stem in WORKSPACE_SKILLS:
            dest = ws_root / f"SKILL_{md.name}"
            dest.write_text(content, encoding="utf-8")

    return docs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="KSP Mun orbit planning run")
    p.add_argument(
        "--model",
        default="deepseek",
        choices=["deepseek", "openai", "anthropic", "gemini", "mock"],
        help="LLM backend to use (default: deepseek)",
    )
    p.add_argument(
        "--max-iter",
        type=int,
        default=30,
        help="Max ReAct loop iterations (default: 30)",
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=16384,
        help="Max tokens per LLM completion (default: 16384)",
    )
    p.add_argument(
        "--output",
        type=str,
        default="",
        help="Write the final plan to this file (optional)",
    )
    p.add_argument(
        "--log-file",
        type=str,
        default="",
        help="Mirror log output to this file (optional)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
        help="Logging verbosity (default: INFO)",
    )
    p.add_argument(
        "--feedback",
        default="cli",
        choices=["file", "cli", "ui"],
        help="How to interact with the agent: cli (default), file, or ui",
    )
    p.add_argument(
        "--ui",
        action="store_true",
        default=False,
        help="Shorthand for --feedback ui",
    )
    p.add_argument(
        "--ui-port",
        type=int,
        default=8765,
        help="Port for the agent UI server (default: 8765)",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def build_llm(model: str):
    from causal_agent import (
        MockLLM, OpenAILLM, AnthropicLLM, GeminiLLM, DeepSeekLLM,
    )

    if model == "mock":
        return MockLLM()
    if model == "openai":
        return OpenAILLM(api_key=os.getenv("OPENAI_API_KEY"))
    if model == "anthropic":
        return AnthropicLLM(api_key=os.getenv("ANTHROPIC_API_KEY"))
    if model == "gemini":
        return GeminiLLM(api_key=os.getenv("GOOGLE_API_KEY"))
    if model == "deepseek":
        return DeepSeekLLM(api_key=os.getenv("DEEPSEEK_API_KEY"))
    raise ValueError(f"Unknown model: {model}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # --- Logging ---
    from causal_agent import setup_logging
    setup_logging(
        level=args.log_level,
        log_file=args.log_file or None,
        load_dotenv=True,
    )

    import logging
    log = logging.getLogger("ksp_planning")

    # --- Load eval spec ---
    eval_spec = load_text(EVAL_SPEC)
    if not eval_spec:
        log.error("Eval spec not found at %s", EVAL_SPEC)
        sys.exit(1)
    log.info("Loaded eval spec: %s (%d chars)", EVAL_SPEC.name, len(eval_spec))

    # --- Load skills (optional reference material) ---
    skills = load_skills()
    if skills:
        log.info("Loaded %d skill doc(s) from %s", len(skills), SKILLS_DIR)
    else:
        log.info("No skill docs found in %s — proceeding without them", SKILLS_DIR)

    # --- Build LLM ---
    log.info("Building LLM backend: %s", args.model)
    llm = build_llm(args.model)

    # --- Build tool registry ---
    from causal_agent import ToolRegistry, ResearchTools, HumanInterface, FileTools
    registry = ToolRegistry()

    rt = ResearchTools()
    rt.register_all(registry)
    log.info("Registered research tools: web_search, fetch_page")

    ft = FileTools(workspace=ROOT / "agent_workspace")
    ft.register_all(registry)
    log.info("Registered file tools: save_file, read_file, list_files  [workspace: agent_workspace/]")

    feedback_mode = "ui" if args.ui else args.feedback
    if feedback_mode == "ui":
        hi = HumanInterface(backend="web", web_port=args.ui_port)
        log.info("Agent UI started — open http://127.0.0.1:%d", args.ui_port)
    elif feedback_mode == "file":
        workspace_dir = str(ROOT / "agent_workspace")
        hi = HumanInterface(backend="file", file_workspace=workspace_dir)
        log.info("File feedback backend — reply to agent_workspace/OPERATOR_RESPONSE.txt")
    else:
        hi = HumanInterface(backend="cli")
        log.info("Using CLI backend for human interface")
    hi.register_all(registry)
    log.info("Registered human interface tools: human_notify, human_ask, human_confirm, plan_complete")

    # --- System prompt: base + KSP-specific addendum ---
    from causal_agent import PLANNING_SYSTEM
    ksp_addendum = """

## KSP domain context

You are a scientist whose goal is to achieve a stable Mun orbit in Kerbal
Space Program 1.x via a kRPC Python script. The operator is your only sensor —
they build the rocket, run the script, and report back observations.

The mission is complete when the operator confirms: periapsis >= 10 km,
apoapsis <= 500 km, body = Mun, sustained for one full orbit with no thrust.

### Installed game version and DLCs
- **KSP 1.12.5** (not KSP 2 — do not confuse them)
- **Making History** expansion installed — all MakingHistory parts are available
- **Breaking Ground** expansion installed — all Serenity parts are available

The ksp_parts skill in your reference material was generated directly from
this installation's GameData .cfg files. Parts marked `MakingHistory` or
`Serenity` ARE available to the operator in the VAB. Use them.

**Recommended Making History parts for this mission:**
- `LiquidEngineRE-J10` — RE-J10 "Wolfhound" — 375 kN vac, Isp ~380 s, 3.3 t
  (excellent high-efficiency upper stage or TMI/MOI engine)
- `LiquidEngineLV-T91` — LV-T91 "Cheetah" — 125 kN vac, Isp ~355 s, 1.0 t
  (lightweight vacuum engine, ideal for upper stage)
- `LiquidEngineLV-TX87` — LV-TX87 "Bobcat" — 400 kN vac, Isp ~340 s, 2.0 t
  (good mid-stage engine)
- `Size1p5_Tank_*` series — FL-TX220/440/900/1800 tanks (1.875 m diameter,
  between 1.25 m and 2.5 m — pair with the Cheetah or Wolfhound)

### Domain knowledge sources
- kRPC Python API: https://krpc.github.io/krpc/python/api/
- Skills library in your context window (read these before web_search)

Do NOT fetch the KSP wiki for part stats — search results mix up KSP1 and KSP2
values. The ksp_parts skill has the exact stats from this installation's files.

### What the reference material in your context contains
Your context window begins with a ## Reference Material section containing
skill documents on:
  - krpc_basics: connection, speed measurement (use orbit.speed, NOT flight.speed),
    streams, writing data files from flight scripts
  - spacecraft_control: throttle, staging, autopilot, burn execution with
    dual-condition stop (RDV + velocity fallback)
  - orbital_mechanics: vis-viva, circularisation dV, TMI sweep pattern,
    hyperbolic escape detection, SOI transitions
  - mission_planning: Hohmann transfers, Mun dV budget, sanity checks
  - krpc_expressions: events, streams, practical Mun mission patterns
  - self_instrumentation: mandatory telemetry/burns/events file templates,
    workspace path injection, robustness checklist
  - ksp_parts: complete parts list generated from this installation's .cfg files

Three additional skill files are in the workspace — read them when needed:
  - SKILL_postmortem_writing.md  — hypothesis doc + postmortem templates
  - SKILL_data_analysis.md       — how to parse telemetry/burns/events logs
  - SKILL_workspace_workflow.md  — file naming, session-start, state recovery

Read the context skills before searching the web. Read the workspace skills
when writing your first hypothesis doc or your first postmortem.

### Context budget — important
Your context window is finite. To avoid overflow:
- When reading telemetry files, read ONLY the current attempt's files.
- Do NOT read prior attempts' raw data unless the postmortem is missing.
- Read the latest postmortem (summary) rather than re-reading raw telemetry.
- Keep web_search calls focused — one search per specific question.

### Minimum required artifacts per attempt
Before each experiment these files must exist in the workspace:

- `hypotheses_N.md` — written BEFORE the experiment runs:
    * Material uncertainties at this stage of the investigation
    * Competing hypotheses for each uncertainty
    * Specific predicted sensor readings for each hypothesis
    * What this experiment is designed to test

- `manifest_attempt_N.md` — full stage table with exact KSP 1.x part names,
  per-stage ΔV and TWR, decoupler placement, SAS/RCS. Total ΔV >= 5,250 m/s.
  First-stage TWR >= 1.3 at Kerbin sea level.

  **Every attempt needs this file.** If the rocket is unchanged from attempt N−1,
  still call `save_file("manifest_attempt_N.md", ...)` with a short stub that
  states explicitly that the stack matches `manifest_attempt_(N-1).md` and lists
  only operator-facing deltas (e.g. paint, tweak). Do not skip numbers — gaps
  confuse reviewers and the operator.

- `flight_attempt_N.py` — complete, runnable kRPC Python script.

  **Self-reporting requirements (mandatory):**
  The script MUST write its own data to the workspace. Use the absolute
  path that list_files() prints for the workspace directory.

  Required output files the script must create:
  * `telemetry_attempt_N.txt` — one row every 5 s of game time:
    [T+{s}s] ALT={m} SURF_ALT={m} SPD={m/s} AP={m} PE={m} BODY={name}
    FUEL={pct}% PHASE={name} THROTTLE={0-1} STAGE={n}
  * `burns_attempt_N.txt` — one row every 0.25 s during any active burn:
    [T+{s}s] PHASE={name} THROTTLE={0-1} REMAINING_DV={m/s} AP={m} PE={m}
  * `events_attempt_N.txt` — one row per discrete event (staging, phase
    transition, node creation/removal, SOI change, script exception):
    [T+{s}s] EVENT={type} DETAIL={value}

  The script must write these files whether the flight succeeds or fails.
  Use try/finally so data is flushed even on exception.

After each failed experiment these files must also exist:

- `postmortem_N.md` — written AFTER reading and analysing telemetry,
  BEFORE the next attempt:
    * Computed quantities from the data (dV used per phase, burn durations,
      AP/PE at each phase transition, fuel remaining at staging)
    * Which predicted readings were confirmed, which were violated (cite
      exact values and timestamps)
    * Root cause stated as a falsifiable claim
    * Targeted fix and mechanistic reason it addresses the root cause
    * What the next experiment will specifically prove or disprove

### Per-experiment loop

1. save_file("hypotheses_N.md", ...)       ← before writing the script
2. save_file("manifest_attempt_N.md", ...)
3. save_file("flight_attempt_N.py", ...)   ← script writes its own data files
4. human_notify("Attempt N ready — files saved. Script will auto-write
   telemetry_attempt_N.txt, burns_attempt_N.txt, events_attempt_N.txt.")
5. human_ask(
     "Build to manifest_attempt_N.md, connect kRPC, run flight_attempt_N.py. "
     "When it finishes or crashes, type 'done: <one line on how it ended>'. "
     "I will read the data files myself."
   )
   ← BLOCKS until operator responds
6. read_file("telemetry_attempt_N.txt")
   read_file("burns_attempt_N.txt")
   read_file("events_attempt_N.txt")
   ← analyse the raw data yourself; do not skip this step
7. save_file("postmortem_N.md", ...)       ← written from data analysis
8. If SUCCESS confirmed by telemetry → call plan_complete.
   If FAILURE → increment N, go to step 1.

The operator's job is only to trigger the experiment and report completion.
All data collection and analysis is yours.

Do NOT call plan_complete until telemetry confirms PE >= 10 km, AP <= 500 km,
BODY = Mun, sustained for one full orbit period with THROTTLE = 0.
"""
    system_prompt = PLANNING_SYSTEM + ksp_addendum

    # --- Memory (optional but useful for multi-attempt runs) ---
    from causal_agent import MemoryStore
    memory = MemoryStore()

    # --- Planner ---
    from causal_agent import ResearchPlanner
    planner = ResearchPlanner(
        llm=llm,
        registry=registry,
        system_prompt=system_prompt,
        skill_docs=skills,
        memory=memory,
        max_iterations=args.max_iter,
        max_tokens=args.max_tokens,
        verbose=True,
    )

    # --- Goal: the full eval spec is the goal ---
    goal = eval_spec
    log.info("Starting planning run (max_iter=%d)...", args.max_iter)
    print("\n" + "=" * 72)
    print("  KSP MUN ORBIT — PLANNING PHASE")
    print("=" * 72 + "\n")

    result = planner.run(goal=goal)

    # Signal the UI that the session has finished.
    # The planner already forwarded any un-notified content to the UI internally.
    if args.ui and hasattr(hi, "_server"):
        hi._server.complete(result.summary())

    # --- Output ---
    print("\n" + "=" * 72)
    print(f"  PLANNING COMPLETE  |  {result.summary()}")
    print("=" * 72 + "\n")
    print(result.plan)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.plan, encoding="utf-8")
        log.info("Plan written to %s", out_path.resolve())

    if result.truncated:
        log.warning(
            "Planning was truncated at %d iterations. "
            "Increase --max-iter or check the log for the last tool call.",
            args.max_iter,
        )


if __name__ == "__main__":
    main()

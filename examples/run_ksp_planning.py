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
    """Load any .md files from the skills/ directory as reference material."""
    if not SKILLS_DIR.exists():
        return []
    docs = []
    for md in sorted(SKILLS_DIR.glob("*.md")):
        content = md.read_text(encoding="utf-8").strip()
        if content:
            docs.append(f"### {md.stem}\n\n{content}")
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
        default=4096,
        help="Max tokens per LLM completion (default: 4096)",
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
        "--ui",
        action="store_true",
        default=False,
        help="Open browser UI for agent communication (default: CLI)",
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

    if args.ui:
        hi = HumanInterface(backend="web", web_port=args.ui_port)
        log.info("Agent UI started — open http://localhost:%d", args.ui_port)
    else:
        hi = HumanInterface()
        log.info("Using CLI backend for human interface")
    hi.register_all(registry)
    log.info("Registered human interface tools: human_notify, human_ask, human_confirm, plan_complete")

    # --- System prompt: base + KSP-specific addendum ---
    from causal_agent import PLANNING_SYSTEM
    ksp_addendum = """

## Eval-specific constraints

You are planning a Kerbal Space Program mission. Your deliverables are:

1. **Rocket manifest** — a complete stage table with exact KSP part names, per-stage
   delta-v and TWR, decoupler placement, and SAS/RCS specification. Total dV must be
   >= 5,250 m/s. First-stage TWR must be >= 1.3.

2. **Flight script** — a complete, runnable Python kRPC script covering all four
   mission phases (launch + gravity turn, circularization, Trans-Mun Injection, Mun
   Orbit Insertion). Include the telemetry loop specified in the eval spec.

Consult the KSP wiki (https://wiki.kerbalspaceprogram.com) for exact part names,
thrust, Isp, and mass figures. Use the community dV map to verify your budget.
Do not invent part stats — look them up.

When you are ready to present the plan:
1. Call save_file("manifest_attempt_1.md", <manifest content>) to write the rocket manifest.
2. Call save_file("flight_attempt_1.py", <script content>) to write the flight script.
3. Call human_notify with a brief summary and the file paths so the operator knows where to find them.
4. Call human_confirm asking the operator to confirm they have the files and are ready to build.
5. Call plan_complete with a one-paragraph summary. This terminates the session immediately.

Use list_files() at the start to check for prior attempt files from earlier runs.
Do NOT keep researching or looping after step 5.
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

    # Notify the UI that the session is done
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

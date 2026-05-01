"""Local FastAPI dashboard for live 2048 and Mastermind decision traces."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import replace
from typing import Any, Optional

from causal_agent.game_trace import GameRunConfig, GameThoughtSession, mock_responses_for_game
from causal_agent.llm import BaseLLM, MockLLM


_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Game Reasoning UI</title>
<style>
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: #f4f5f2;
  color: #202124;
  font-size: 14px;
}
button, input, select {
  font: inherit;
}
button {
  border: 1px solid #aab1a2;
  background: #ffffff;
  color: #202124;
  border-radius: 6px;
  padding: 7px 10px;
  cursor: pointer;
}
button:hover { background: #eef2ea; }
button.primary {
  background: #1f6f5b;
  border-color: #1f6f5b;
  color: #fff;
}
button.warn {
  background: #b4553e;
  border-color: #b4553e;
  color: #fff;
}
input, select {
  border: 1px solid #b8beb1;
  border-radius: 6px;
  background: #fff;
  color: #202124;
  padding: 7px 8px;
  min-width: 78px;
}
label {
  display: grid;
  gap: 3px;
  color: #5c6258;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
}
header {
  border-bottom: 1px solid #d7dbd1;
  background: #fff;
  padding: 12px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
h1 {
  font-size: 17px;
  line-height: 1;
  margin: 0 8px 0 0;
}
.controls {
  display: flex;
  align-items: end;
  gap: 10px;
  flex-wrap: wrap;
}
.spacer { flex: 1; }
.badge {
  border: 1px solid #c9cdc4;
  background: #f7f8f5;
  color: #4d554b;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  white-space: nowrap;
}
main {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(360px, 1.05fr);
  gap: 16px;
  padding: 16px 18px;
}
.panel {
  border: 1px solid #d8dcd3;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  min-width: 0;
}
.panel h2 {
  margin: 0;
  padding: 12px 14px;
  border-bottom: 1px solid #e5e8e0;
  font-size: 13px;
  letter-spacing: .05em;
  text-transform: uppercase;
  color: #5c6258;
}
.panel-body { padding: 14px; }
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.stat {
  border: 1px solid #e1e4dc;
  border-radius: 6px;
  padding: 8px;
  min-height: 54px;
}
.stat span {
  display: block;
  color: #73796f;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.stat strong { font-size: 18px; }
.board {
  display: grid;
  grid-template-columns: repeat(4, minmax(58px, 1fr));
  gap: 8px;
  background: #9b9b88;
  border-radius: 8px;
  padding: 8px;
  max-width: 480px;
}
.tile {
  aspect-ratio: 1;
  border-radius: 6px;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 24px;
  color: #26302b;
  background: #cdcdbb;
}
.options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(142px, 1fr));
  gap: 8px;
  margin-top: 12px;
}
.option, .turn {
  border: 1px solid #e1e4dc;
  border-radius: 6px;
  padding: 10px;
  background: #fcfcfa;
}
.option-title {
  font-weight: 800;
  text-transform: uppercase;
  color: #245f55;
  margin-bottom: 6px;
}
.kv {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px;
  color: #5c6258;
  font-size: 12px;
  line-height: 1.45;
}
.kv strong { color: #202124; }
.palette, .guess {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}
.peg {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid rgba(0,0,0,.18);
}
.history-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #eceee9;
  padding: 9px 0;
}
.feedback-pegs {
  display: flex;
  gap: 4px;
}
.feedback-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #d7d8d2;
  border: 1px solid #b8beb1;
}
.feedback-dot.exact { background: #222; }
.feedback-dot.partial { background: #f2f2f2; }
#timeline {
  display: grid;
  gap: 10px;
  max-height: calc(100vh - 190px);
  overflow: auto;
}
.turn-head {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.turn-title {
  font-weight: 800;
  color: #202124;
}
.rationale {
  border-left: 3px solid #d58a3a;
  padding: 7px 9px;
  background: #fff8ef;
  border-radius: 0 6px 6px 0;
  margin: 8px 0;
  line-height: 1.45;
}
pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 8px 0 0;
  padding: 8px;
  border-radius: 6px;
  background: #f0f2ec;
  color: #363a34;
  font-size: 12px;
  line-height: 1.45;
}
details {
  margin-top: 8px;
}
summary {
  cursor: pointer;
  color: #245f55;
  font-weight: 700;
}
.empty {
  color: #7b8177;
  padding: 18px 4px;
}
@media (max-width: 900px) {
  main { grid-template-columns: 1fr; }
  #timeline { max-height: none; }
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
</head>
<body>
<header>
  <h1>Game Reasoning UI</h1>
  <div class="controls">
    <label>Game
      <select id="game" onchange="handleGameChange()">
        <option value="2048">2048</option>
        <option value="mastermind">Mastermind</option>
      </select>
    </label>
    <label>Seed <input id="seed" type="number" value="7"></label>
    <label>Turns <input id="max-turns" type="number" value="100" min="1"></label>
    <span class="controls" id="mastermind-controls">
      <label>Colors <input id="num-colors" type="number" value="6" min="2" max="10"></label>
      <label>Length <input id="code-length" type="number" value="4" min="1" max="6"></label>
      <label>Attempts <input id="max-attempts" type="number" value="10" min="1"></label>
      <label>Duplicates
        <select id="duplicates">
          <option value="true">Allowed</option>
          <option value="false">Off</option>
        </select>
      </label>
    </span>
    <button onclick="resetSession()">Reset</button>
    <button class="primary" onclick="stepSession()">Step</button>
    <button onclick="autoRun()">Auto-run</button>
    <button class="warn" onclick="pauseRun()">Pause</button>
  </div>
  <div class="spacer"></div>
  <div class="badge" id="model">No session</div>
</header>

<main>
  <section class="panel">
    <h2>Game State</h2>
    <div class="panel-body" id="game-state"></div>
  </section>
  <section class="panel">
    <h2>Decision Trace</h2>
    <div class="panel-body">
      <div id="current-act"></div>
      <div id="timeline"></div>
    </div>
  </section>
</main>

<script>
const DEFAULT_CONFIG = __DEFAULT_CONFIG__;
const COLORS = ["red","blue","green","yellow","orange","purple","pink","brown","black","white"];
const TILE_COLORS = {
  0: "#cdcdbb", 2: "#e8dfc8", 4: "#ead3a6", 8: "#e5a15e",
  16: "#dc7448", 32: "#c9513f", 64: "#a93b32", 128: "#d6be56",
  256: "#c7ad3e", 512: "#b79b2f", 1024: "#9e8628", 2048: "#7d6b22"
};
const PEG_COLORS = {
  red: "#d84a3a", blue: "#2c6bb2", green: "#2d8a5d", yellow: "#e3c33f",
  orange: "#e58a2f", purple: "#7d55b7", pink: "#d76aa0", brown: "#7a543b",
  black: "#222", white: "#f7f7f2"
};
let sessionId = null;
let current = null;
let autoRunning = false;
let isStepping = false;

function esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function pretty(v) { return JSON.stringify(v, null, 2); }
function selectedColors() {
  return COLORS.slice(0, Number(document.getElementById("num-colors").value || 6));
}
function payload() {
  const game = document.getElementById("game").value;
  return {
    game,
    seed: Number(document.getElementById("seed").value || 7),
    max_turns: Number(document.getElementById("max-turns").value || 100),
    colors: selectedColors(),
    code_length: Number(document.getElementById("code-length").value || 4),
    max_attempts: Number(document.getElementById("max-attempts").value || 10),
    duplicates_allowed: document.getElementById("duplicates").value === "true"
  };
}
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...opts
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
async function resetSession() {
  pauseRun();
  current = await api("/api/sessions", {method: "POST", body: JSON.stringify(payload())});
  sessionId = current.session_id;
  render();
}
async function stepSession() {
  if (isStepping) return current;
  isStepping = true;
  if (!sessionId) await resetSession();
  try {
    current = await api(`/api/sessions/${sessionId}/step`, {method: "POST"});
    render();
    if (current.terminal || current.stopped) pauseRun();
    return current;
  } finally {
    isStepping = false;
  }
}
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
async function autoRun() {
  if (autoRunning) return;
  autoRunning = true;
  while (autoRunning) {
    const state = await stepSession();
    if (!state || state.terminal || state.stopped) break;
    await sleep(900);
  }
  autoRunning = false;
}
function pauseRun() {
  autoRunning = false;
}
function toggleGameControls() {
  document.getElementById("mastermind-controls").style.display =
    document.getElementById("game").value === "mastermind" ? "flex" : "none";
}
async function handleGameChange() {
  toggleGameControls();
  await resetSession();
}
function applyDefaults() {
  if (!DEFAULT_CONFIG) return;
  document.getElementById("game").value = DEFAULT_CONFIG.game || "2048";
  document.getElementById("seed").value = DEFAULT_CONFIG.seed ?? 7;
  document.getElementById("max-turns").value = DEFAULT_CONFIG.max_turns ?? 100;
  document.getElementById("num-colors").value = (DEFAULT_CONFIG.colors || COLORS.slice(0, 6)).length;
  document.getElementById("code-length").value = DEFAULT_CONFIG.code_length ?? 4;
  document.getElementById("max-attempts").value = DEFAULT_CONFIG.max_attempts ?? 10;
  document.getElementById("duplicates").value = DEFAULT_CONFIG.duplicates_allowed === false ? "false" : "true";
}
function render() {
  if (!current) return;
  document.getElementById("model").textContent = current.model;
  if (current.game === "2048") render2048(current.state);
  else renderMastermind(current.state);
  renderCurrentAct();
  renderTimeline(current.history || []);
}
function renderStats(items) {
  return `<div class="stats">${items.map(([k,v]) =>
    `<div class="stat"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join("")}</div>`;
}
function render2048(state) {
  const board = state.board || [];
  const html = [
    renderStats([
      ["Score", state.score],
      ["Max Tile", state.max_tile],
      ["Turn", current.turn],
      ["Status", current.terminal ? "Done" : "Live"]
    ]),
    `<div class="board">${board.flat().map(value =>
      `<div class="tile" style="background:${TILE_COLORS[value] || "#665c37"};color:${value >= 64 ? "#fff" : "#26302b"}">${value || ""}</div>`
    ).join("")}</div>`,
    `<div class="options">${(latestOptions()).map(renderOption).join("")}</div>`
  ].join("");
  document.getElementById("game-state").innerHTML = html;
}
function renderOption(opt) {
  return `<div class="option">
    <div class="option-title">${esc(opt.direction || opt.action_type || "option")}</div>
    <div class="kv"><span>gained</span><strong>${esc(opt.gained ?? "-")}</strong></div>
    <div class="kv"><span>empty after</span><strong>${esc(opt.empty_after ?? "-")}</strong></div>
    <div class="kv"><span>max after</span><strong>${esc(opt.max_tile_after ?? "-")}</strong></div>
  </div>`;
}
function peg(color) {
  return `<span class="peg" title="${esc(color)}" style="background:${PEG_COLORS[color] || "#aaa"}"></span>`;
}
function renderMastermind(state) {
  const hist = state.history || [];
  const html = [
    renderStats([
      ["Candidates", state.candidate_count],
      ["Attempts Left", state.attempts_remaining],
      ["Turn", current.turn],
      ["Status", current.terminal ? "Done" : "Live"]
    ]),
    `<div class="palette">${(state.colors || []).map(peg).join("")}</div>`,
    hist.length ? hist.map(row => {
      const dots = [];
      for (let i = 0; i < row.exact; i++) dots.push('<span class="feedback-dot exact"></span>');
      for (let i = 0; i < row.partial; i++) dots.push('<span class="feedback-dot partial"></span>');
      while (dots.length < state.code_length) dots.push('<span class="feedback-dot"></span>');
      return `<div class="history-row"><div class="guess">${row.guess.map(peg).join("")}</div><div class="feedback-pegs">${dots.join("")}</div></div>`;
    }).join("") : `<div class="empty">No guesses yet.</div>`,
    state.secret ? `<details open><summary>Secret</summary><div class="guess" style="margin-top:8px">${state.secret.map(peg).join("")}</div></details>` : ""
  ].join("");
  document.getElementById("game-state").innerHTML = html;
}
function latestOptions() {
  const hist = current.history || [];
  if (hist.length) return hist[hist.length - 1].legal_options || [];
  return (current.state.legal_directions || []).map(direction => ({direction}));
}
function renderTimeline(history) {
  const el = document.getElementById("timeline");
  if (!history.length) {
    el.innerHTML = `<div class="empty">Ready.</div>`;
    return;
  }
  el.innerHTML = history.slice().reverse().map(turn => {
    const decision = turn.planner_trace?.decision || {};
    const tools = turn.planner_trace?.tool_calls || [];
    return `<article class="turn">
      <div class="turn-head"><span class="turn-title">Turn ${turn.turn}</span><span class="badge">${esc(turn.action?.action_type || "-")}</span></div>
      <div class="kv"><span>action</span><strong>${esc(actionLabel(turn.action))}</strong></div>
      <div class="kv"><span>intent</span><strong>${esc(decision.intent || "")}</strong></div>
      <div class="kv"><span>observation</span><strong>${esc(turn.observation || "")}</strong></div>
      <div class="rationale">${esc(decision.public_rationale || "")}</div>
      <div class="kv"><span>feedback</span><strong>${esc(turn.feedback?.content || "")}</strong></div>
      <details open><summary>Options</summary><pre>${esc(pretty(turn.legal_options || []))}</pre></details>
      <details open><summary>Action analysis</summary><pre>${esc(pretty(turn.action_analysis || {}))}</pre></details>
      <details open><summary>Safe planner trace</summary><pre>${esc(pretty(turn.planner_trace || {}))}</pre></details>
      ${tools.length ? `<details open><summary>Tool calls</summary><pre>${esc(pretty(tools))}</pre></details>` : ""}
      ${(turn.planner_trace?.preview_notes || []).length ? `<details open><summary>Planner previews</summary><pre>${esc(pretty(turn.planner_trace.preview_notes))}</pre></details>` : ""}
      ${(turn.planner_trace?.intervention_notes || []).length ? `<details open><summary>Interventions</summary><pre>${esc(pretty(turn.planner_trace.intervention_notes))}</pre></details>` : ""}
      ${(turn.planner_trace?.parse_errors || []).length ? `<details open><summary>Parse and fallback text</summary><pre>${esc(pretty({
        parse_errors: turn.planner_trace.parse_errors,
        fallback: turn.planner_trace.fallback,
        fallback_reason: turn.planner_trace.fallback_reason || ""
      }))}</pre></details>` : ""}
    </article>`;
  }).join("");
}
function renderCurrentAct() {
  const el = document.getElementById("current-act");
  const trace = current.latest_trace;
  if (!trace) {
    el.innerHTML = `<div class="empty">No acts yet. Press Step to run one move.</div>`;
    return;
  }
  const decision = trace.planner_trace?.decision || {};
  el.innerHTML = `<div class="turn" style="margin-bottom:10px">
    <div class="turn-head"><span class="turn-title">Current act: move ${trace.turn}</span><span class="badge">${esc(actionLabel(trace.action))}</span></div>
    <div class="kv"><span>intent</span><strong>${esc(decision.intent || "")}</strong></div>
    <div class="kv"><span>result</span><strong>${esc(trace.feedback?.content || "")}</strong></div>
    <div class="kv"><span>log file</span><strong>${esc(current.log_path || "logging off")}</strong></div>
    <div class="rationale">${esc(decision.public_rationale || "")}</div>
  </div>`;
}
function actionLabel(action) {
  if (!action) return "";
  if (action.payload?.direction) return action.payload.direction;
  if (action.payload?.code) return action.payload.code.join(" ");
  return action.action_type;
}

applyDefaults();
toggleGameControls();
resetSession();
</script>
</body>
</html>
"""


LLMFactory = Callable[[GameRunConfig], BaseLLM]
LogDirFactory = Callable[[GameRunConfig], Optional[str]]


def create_game_ui_app(
    llm_factory: LLMFactory | None = None,
    default_config: GameRunConfig | None = None,
    log_dir_factory: LogDirFactory | None = None,
):
    """Create the local dashboard app."""
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import HTMLResponse

    app = FastAPI(docs_url=None, redoc_url=None)
    sessions: dict[str, GameThoughtSession] = {}

    def _build_session(payload: dict[str, Any] | None) -> tuple[str, GameThoughtSession]:
        data = _config_to_payload(default_config)
        data.update(payload or {})
        config = GameRunConfig.from_dict(data)
        if config.log_dir is None and log_dir_factory is not None:
            config = replace(config, log_dir=log_dir_factory(config))
        llm = (
            llm_factory(config)
            if llm_factory is not None
            else MockLLM(mock_responses_for_game(config.game))
        )
        session = GameThoughtSession(config, llm, model_label=repr(llm))
        session_id = uuid.uuid4().hex[:10]
        sessions[session_id] = session
        return session_id, session

    html = _HTML.replace(
        "__DEFAULT_CONFIG__",
        json.dumps(_config_to_payload(default_config), default=str),
    )

    @app.get("/")
    async def index():
        return HTMLResponse(html)

    @app.post("/api/sessions")
    async def create_session(payload: Any = Body(default=None)):
        try:
            session_id, session = _build_session(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"session_id": session_id, **session.snapshot()}

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str):
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Unknown session.")
        return {"session_id": session_id, **session.snapshot()}

    @app.post("/api/sessions/{session_id}/step")
    async def step_session(session_id: str):
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Unknown session.")
        session.step()
        return {"session_id": session_id, **session.snapshot()}

    return app


def _config_to_payload(config: GameRunConfig | None) -> dict[str, Any]:
    if config is None:
        return {}
    return {
        "game": config.game,
        "seed": config.seed,
        "max_turns": config.max_turns,
        "size": config.size,
        "colors": list(config.mastermind_colors),
        "code_length": config.mastermind_code_length,
        "max_attempts": config.mastermind_max_attempts,
        "duplicates_allowed": config.mastermind_duplicates_allowed,
        "simulate_before_plan": config.simulate_before_plan,
        "max_tool_calls": config.max_tool_calls,
        "log_dir": config.log_dir,
        "log_filename": config.log_filename,
        "episode": config.episode,
    }

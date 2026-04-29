"""
causal_agent/ui_server.py

Local web UI for agent-operator communication.

AgentUIServer starts a tiny FastAPI + WebSocket server in a daemon thread.
Open http://localhost:<port> in a browser and get a live chat feed with the
running agent.

Communication model
-------------------
Agent → Operator   human_notify / human_ask / human_confirm / plan_complete
Operator → Agent   check_operator_instructions (polled tool) or
                   replies to ask/confirm requests

The operator input box is always visible.  When the agent is waiting for a
reply (ask/confirm), the input is used as the reply.  Otherwise, the message
is queued as an instruction the agent can pick up by calling
check_operator_instructions().

WebBackend implements the HumanInterface._Backend protocol.

Usage
-----
    from causal_agent.ui_server import AgentUIServer, WebBackend
    from causal_agent import HumanInterface

    server = AgentUIServer(port=8765)
    server.start()
    hi = HumanInterface(backend=WebBackend(server))
    hi.register_all(registry)           # also registers check_operator_instructions

    import webbrowser
    webbrowser.open(f"http://localhost:{server.port}")
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import uuid
from typing import Any

log = logging.getLogger("causal_agent.ui_server")

# ---------------------------------------------------------------------------
# HTML frontend
# ---------------------------------------------------------------------------

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Causal Agent</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: #111;
  color: #e0e0e0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-size: 13px;
}

/* ── Header ── */
header {
  padding: 10px 18px;
  border-bottom: 1px solid #1e1e1e;
  background: #161616;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
header h1 { font-size: 13px; font-weight: 600; letter-spacing: 0.05em; color: #bbb; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #333; transition: background .3s; }
.dot.ok  { background: #4caf50; }
.dot.err { background: #f44336; }
#conn-label { font-size: 11px; color: #444; margin-left: auto; }

/* ── Feed ── */
#feed {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.empty { display: flex; align-items: center; justify-content: center; flex: 1; color: #2a2a2a; }

.msg { display: flex; flex-direction: column; gap: 4px; }

.msg-meta { display: flex; align-items: center; gap: 8px; }

.badge {
  font-size: 9px; font-weight: 800;
  letter-spacing: 0.1em; padding: 2px 5px;
  border-radius: 3px; text-transform: uppercase;
}
.b-notify   { background: #0d2440; color: #5ba3f5; }
.b-ask      { background: #2a1c00; color: #d4900a; }
.b-confirm  { background: #2a1000; color: #d46010; }
.b-complete { background: #082208; color: #4caf50; }
.b-you      { background: #1e1e1e; color: #666; }
.b-instr    { background: #1e1e2e; color: #888aff; }

.ts { font-size: 10px; color: #333; }

.body {
  background: #161616;
  border-left: 2px solid #252525;
  border-radius: 0 4px 4px 0;
  padding: 8px 12px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.55;
  font-family: 'SF Mono', Consolas, 'Cascadia Code', monospace;
  font-size: 12px;
  max-height: 500px;
  overflow-y: auto;
  color: #c0c0c0;
}
.body.notify   { border-color: #1a3f6e; }
.body.ask      { border-color: #6e4800; }
.body.confirm  { border-color: #6e2800; }
.body.complete { border-color: #1a5a1a; background: #0a180a; color: #6dd46d; }
.body.you      { border-color: #282828; color: #666; font-family: inherit; font-size: 12px; }
.body.instr    { border-color: #2a2a5a; color: #8888cc; font-family: inherit; font-size: 12px; }

/* ── Input zone ── */
#zone {
  flex-shrink: 0;
  border-top: 1px solid #1e1e1e;
  background: #141414;
  padding: 10px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.zone-top {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 22px;
}

#pending-badge {
  font-size: 9px; font-weight: 700; letter-spacing: 0.08em;
  padding: 2px 6px; border-radius: 3px; text-transform: uppercase;
  display: none;
}
#pending-badge.ask     { display: inline-block; background: #2a1c00; color: #d4900a; }
#pending-badge.confirm { display: inline-block; background: #2a1000; color: #d46010; }

#pending-text { font-size: 11px; color: #555; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Confirm buttons */
#confirm-btns { display: none; gap: 8px; }
#confirm-btns.show { display: flex; }
.yes { border: 1px solid #1a4a1a; color: #4caf50; background: #0c1c0c; border-radius: 4px; padding: 6px 20px; font-size: 12px; cursor: pointer; }
.yes:hover { background: #142814; }
.no  { border: 1px solid #4a1a1a; color: #f44336; background: #1c0c0c; border-radius: 4px; padding: 6px 20px; font-size: 12px; cursor: pointer; }
.no:hover  { background: #28140c; }

/* Text input */
.input-row { display: flex; gap: 8px; align-items: flex-end; }

textarea#txt {
  flex: 1;
  background: #1a1a1a;
  border: 1px solid #272727;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 13px;
  font-family: inherit;
  padding: 7px 10px;
  resize: none;
  outline: none;
  min-height: 34px;
  max-height: 120px;
  line-height: 1.4;
}
textarea#txt:focus { border-color: #404040; }
textarea#txt.waiting { border-color: #4a3800; }

button#send-btn {
  background: #1e1e1e; border: 1px solid #303030;
  color: #ccc; border-radius: 4px;
  padding: 7px 14px; font-size: 12px;
  cursor: pointer; white-space: nowrap; transition: background .12s;
}
button#send-btn:hover { background: #2a2a2a; }
button#send-btn.reply { border-color: #4a3800; color: #d4900a; }

#hint { font-size: 10px; color: #333; }
</style>
</head>
<body>

<header>
  <div class="dot" id="dot"></div>
  <h1>Causal Agent</h1>
  <span id="conn-label">Connecting…</span>
</header>

<div id="feed">
  <div class="empty">Waiting for agent…</div>
</div>

<div id="zone">
  <div class="zone-top">
    <span class="badge b-ask" id="pending-badge"></span>
    <span id="pending-text"></span>
  </div>

  <div id="confirm-btns">
    <button class="yes" onclick="sendConfirm('yes')">Yes</button>
    <button class="no"  onclick="sendConfirm('no')">No</button>
  </div>

  <div class="input-row">
    <textarea id="txt" rows="1" placeholder="Send instruction to agent…"></textarea>
    <button id="send-btn" onclick="send()">Send</button>
  </div>

  <div id="hint">Ctrl+Enter to send</div>
</div>

<script>
const PORT = __PORT__;
let ws, pendingId = null, pendingType = null;

function ts() { return new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}); }
function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function addMsg(badgeClass, badgeText, bodyClass, content) {
  const feed = document.getElementById('feed');
  feed.querySelector('.empty')?.remove();
  const d = document.createElement('div');
  d.className = 'msg';
  d.innerHTML =
    `<div class="msg-meta"><span class="badge ${badgeClass}">${badgeText}</span><span class="ts">${ts()}</span></div>` +
    `<div class="body ${bodyClass}">${esc(content)}</div>`;
  feed.appendChild(d);
  feed.scrollTop = feed.scrollHeight;
}

function setWaiting(type, label) {
  pendingType = type;
  const badge = document.getElementById('pending-badge');
  badge.className = 'badge b-' + type;
  badge.textContent = type.toUpperCase();
  document.getElementById('pending-text').textContent = label;

  const txt = document.getElementById('txt');
  const btn = document.getElementById('send-btn');
  const cfm = document.getElementById('confirm-btns');

  if (type === 'confirm') {
    cfm.classList.add('show');
    txt.placeholder = 'Or type a message to agent…';
    txt.classList.remove('waiting');
    btn.classList.remove('reply');
    btn.textContent = 'Send';
  } else {
    cfm.classList.remove('show');
    txt.placeholder = 'Type your reply…';
    txt.classList.add('waiting');
    btn.classList.add('reply');
    btn.textContent = 'Reply';
    txt.focus();
  }
}

function clearWaiting() {
  pendingId = pendingType = null;
  document.getElementById('pending-badge').className = 'badge b-ask';
  document.getElementById('pending-badge').style.display = 'none';
  document.getElementById('pending-text').textContent = '';
  document.getElementById('confirm-btns').classList.remove('show');
  const txt = document.getElementById('txt');
  txt.placeholder = 'Send instruction to agent…';
  txt.classList.remove('waiting');
  const btn = document.getElementById('send-btn');
  btn.classList.remove('reply');
  btn.textContent = 'Send';
  // reset display
  document.getElementById('pending-badge').style.removeProperty('display');
}

function setConn(ok, label) {
  document.getElementById('dot').className = 'dot ' + (ok ? 'ok' : 'err');
  document.getElementById('conn-label').textContent = label;
}

function send() {
  const val = document.getElementById('txt').value.trim();
  if (!val) return;

  if (pendingId && pendingType === 'ask') {
    // Reply to pending ask
    ws.send(JSON.stringify({id: pendingId, response: val}));
    addMsg('b-you','YOU','you', val);
    clearWaiting();
  } else {
    // Free-form instruction to agent
    ws.send(JSON.stringify({type: 'instruction', message: val}));
    addMsg('b-instr','YOU → AGENT','instr', val);
    // Don't clear waiting — confirm might still be pending
  }

  const txt = document.getElementById('txt');
  txt.value = '';
  txt.style.height = 'auto';
}

function sendConfirm(ans) {
  if (!pendingId) return;
  ws.send(JSON.stringify({id: pendingId, response: ans}));
  addMsg('b-you','YOU','you', ans);
  clearWaiting();
}

function handle(msg) {
  if (msg.type === 'notify') {
    addMsg('b-notify','NOTIFY','notify', msg.message);

  } else if (msg.type === 'ask') {
    pendingId = msg.id;
    addMsg('b-ask','ASK','ask', msg.question);
    setWaiting('ask', msg.question.split('\n')[0].slice(0, 80));

  } else if (msg.type === 'confirm') {
    pendingId = msg.id;
    addMsg('b-confirm','CONFIRM','confirm', msg.message);
    setWaiting('confirm', msg.message.split('\n')[0].slice(0, 80));

  } else if (msg.type === 'complete') {
    addMsg('b-complete','DONE','complete', msg.summary);
    clearWaiting();
  }
}

function connect() {
  ws = new WebSocket(`ws://localhost:${PORT}/ws`);
  ws.onopen  = () => setConn(true, 'Connected');
  ws.onclose = () => { setConn(false, 'Disconnected — retrying…'); setTimeout(connect, 2000); };
  ws.onerror = () => setConn(false, 'Error');
  ws.onmessage = e => handle(JSON.parse(e.data));
}

// Auto-grow textarea
document.getElementById('txt').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});
// Ctrl+Enter to send
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); send(); }
});

connect();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class AgentUIServer:
    """
    FastAPI + WebSocket server in a daemon background thread.

    Operator messages that arrive outside of ask/confirm flows are queued
    as instructions; call get_instructions() to drain the queue.
    """

    def __init__(self, port: int = 8765) -> None:
        self.port = port
        self._clients: set[Any] = set()
        self._pending: dict[str, threading.Event] = {}
        self._responses: dict[str, str] = {}
        self._instructions: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._app = self._build_app()

    # ------------------------------------------------------------------
    # Public API (called from the agent / main thread)
    # ------------------------------------------------------------------

    def start(self) -> None:
        t = threading.Thread(target=self._run, daemon=True, name="agent-ui-server")
        t.start()
        self._ready.wait(timeout=10)
        log.info("Agent UI ready at http://localhost:%d", self.port)

    def notify(self, message: str) -> None:
        self._send({"type": "notify", "message": message})

    def ask(self, question: str) -> str:
        req_id = self._new_id()
        ev = threading.Event()
        self._pending[req_id] = ev
        self._send({"type": "ask", "id": req_id, "question": question})
        ev.wait()
        return self._responses.pop(req_id, "")

    def confirm(self, message: str) -> bool:
        req_id = self._new_id()
        ev = threading.Event()
        self._pending[req_id] = ev
        self._send({"type": "confirm", "id": req_id, "message": message})
        ev.wait()
        answer = self._responses.pop(req_id, "no").lower()
        return answer in ("yes", "y")

    def complete(self, summary: str) -> None:
        self._send({"type": "complete", "summary": summary})

    def get_instructions(self) -> list[str]:
        """Drain and return all queued operator instructions."""
        msgs = []
        while not self._instructions.empty():
            try:
                msgs.append(self._instructions.get_nowait())
            except queue.Empty:
                break
        return msgs

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _new_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def _send(self, msg: dict) -> None:
        if self._loop is None:
            log.warning("UI loop not ready — dropping: %s", msg.get("type"))
            return
        future = asyncio.run_coroutine_threadsafe(self._broadcast(msg), self._loop)
        try:
            future.result(timeout=5)
        except Exception as exc:
            log.warning("UI broadcast failed: %s", exc)

    async def _broadcast(self, msg: dict) -> None:
        import json
        payload = json.dumps(msg, ensure_ascii=False)
        with self._lock:
            clients = list(self._clients)
        dead: set[Any] = set()
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        if dead:
            with self._lock:
                self._clients -= dead

    def _resolve(self, req_id: str, response: str) -> None:
        self._responses[req_id] = response
        ev = self._pending.pop(req_id, None)
        if ev:
            ev.set()

    def _build_app(self):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse

        app = FastAPI(docs_url=None, redoc_url=None)
        html = _HTML.replace("__PORT__", str(self.port))

        @app.on_event("startup")
        async def _startup():
            self._loop = asyncio.get_event_loop()
            self._ready.set()

        @app.get("/")
        async def _index():
            return HTMLResponse(html)

        @app.websocket("/ws")
        async def _ws(websocket: WebSocket):
            await websocket.accept()
            with self._lock:
                self._clients.add(websocket)
            log.info("UI client connected")
            try:
                while True:
                    data = await websocket.receive_json()

                    # Free-form operator instruction
                    if data.get("type") == "instruction":
                        msg = data.get("message", "").strip()
                        if msg:
                            self._instructions.put(msg)
                            log.info("Operator instruction queued: %r", msg)
                        continue

                    # Reply to a pending ask/confirm
                    req_id = data.get("id", "")
                    if req_id:
                        response = data.get("response", "")
                        self._resolve(req_id, response)
                        log.info("UI response for %s: %r", req_id, response)

            except WebSocketDisconnect:
                pass
            except Exception as exc:
                log.debug("WebSocket error: %s", exc)
            finally:
                with self._lock:
                    self._clients.discard(websocket)
                log.info("UI client disconnected")

        return app

    def _run(self) -> None:
        import sys
        import uvicorn
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        uvicorn.run(
            self._app,
            host="localhost",
            port=self.port,
            log_level="error",
            access_log=False,
        )


# ---------------------------------------------------------------------------
# WebBackend — implements HumanInterface._Backend protocol
# ---------------------------------------------------------------------------

class WebBackend:
    """
    Routes HumanInterface calls through AgentUIServer.

    Also exposes get_pending_instructions() so HumanInterface.register_all()
    can wire up the check_operator_instructions tool automatically.
    """

    def __init__(self, server: AgentUIServer) -> None:
        self._server = server

    def notify(self, message: str) -> None:
        log.info("UI notify (%d chars)", len(message))
        self._server.notify(message)

    def ask(self, question: str) -> str:
        log.info("UI ask — blocking for operator response")
        response = self._server.ask(question)
        log.info("UI ask response: %r", response)
        return response

    def confirm(self, message: str) -> bool:
        log.info("UI confirm — blocking for operator response")
        result = self._server.confirm(message)
        log.info("UI confirm response: %s", result)
        return result

    def get_pending_instructions(self) -> list[str]:
        """Return and clear any queued operator instructions."""
        return self._server.get_instructions()

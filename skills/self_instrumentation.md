# Self-Instrumentation: Writing Flight Scripts That Collect Their Own Evidence

## Principle

A flight script that does not write its own telemetry provides no evidence.
The agent cannot form hypotheses, cannot detect failures, and cannot improve.
Every script you generate **must** write data files autonomously — not rely on
the operator to copy-paste terminal output.

## Required Output Files per Attempt

For attempt N, the script must produce all three:

| File | Description |
|---|---|
| `telemetry_attempt_N.txt` | One row every 5 s of game time: ALT, SPD, AP, PE, BODY, FUEL, PHASE, STAGE |
| `burns_attempt_N.txt` | One row every 0.25 s during each burn: UT, RDV, SPD, THROTTLE, STAGE |
| `events_attempt_N.txt` | One row per discrete event: staging, SOI change, burn start/end, error, abort |

Write all three files unconditionally. Do not gate writes on success.

## Getting the Workspace Path

The agent knows its workspace path from `list_files()`. Embed the absolute
path directly into the generated script — never use a relative path:

```python
# At the top of every flight script the agent writes:
WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
import os
TEL_FILE    = os.path.join(WORKSPACE, "telemetry_attempt_1.txt")
BURNS_FILE  = os.path.join(WORKSPACE, "burns_attempt_1.txt")
EVENTS_FILE = os.path.join(WORKSPACE, "events_attempt_1.txt")
```

The agent replaces `1` with the actual attempt number before calling
`save_file`. The path is embedded, not computed at runtime.

## Telemetry Writer Template

```python
import time as _time

_last_tel_t = [0.0]

def write_telemetry(f, vessel, sc, launch_ut, phase):
    global _last_tel_t
    if sc.ut - _last_tel_t[0] < 5.0:
        return
    _last_tel_t[0] = sc.ut
    try:
        surf  = vessel.flight(vessel.surface_reference_frame)
        orbit = vessel.orbit
        res   = vessel.resources
        fuel_max  = res.max("LiquidFuel") + res.max("Oxidizer")
        fuel_left = res.amount("LiquidFuel") + res.amount("Oxidizer")
        fuel_pct  = 100.0 * fuel_left / max(fuel_max, 1.0)
        met = sc.ut - launch_ut
        row = (
            f"[T+{met:.0f}s] "
            f"ALT={surf.mean_altitude:.0f}m "
            f"SPD={orbit.speed:.1f}m/s "          # orbit.speed — not flight.speed
            f"AP={orbit.apoapsis_altitude:.0f}m "
            f"PE={orbit.periapsis_altitude:.0f}m "
            f"ECC={orbit.eccentricity:.4f} "
            f"BODY={orbit.body.name} "
            f"FUEL={fuel_pct:.1f}% "
            f"PHASE={phase} "
            f"STAGE={vessel.control.current_stage}\n"
        )
        f.write(row)
        f.flush()
    except Exception as exc:
        f.write(f"[TEL ERROR] {exc}\n")
        f.flush()
```

## Burn Data Writer Template

Call this inside the burn loop instead of bare `time.sleep`:

```python
def write_burn_row(f, vessel, sc, node):
    try:
        row = (
            f"UT={sc.ut:.2f} "
            f"RDV={node.remaining_delta_v:.2f} "
            f"SPD={vessel.orbit.speed:.2f} "
            f"THROTTLE={vessel.control.throttle:.2f} "
            f"STAGE={vessel.control.current_stage}\n"
        )
        f.write(row)
        f.flush()
    except Exception as exc:
        f.write(f"[BURN ERROR] {exc}\n")
        f.flush()
```

## Events Writer Template

```python
def write_event(f, vessel, sc, launch_ut, tag, extra=""):
    try:
        met = sc.ut - launch_ut
        f.write(
            f"[T+{met:.0f}s] EVENT={tag} "
            f"BODY={vessel.orbit.body.name} "
            f"ALT={vessel.flight(vessel.surface_reference_frame).mean_altitude:.0f}m "
            f"{extra}\n"
        )
        f.flush()
    except Exception as exc:
        f.write(f"[EVENT ERROR] {exc}\n")
        f.flush()
```

Emit events for at minimum:

- `LAUNCH`
- `GRAVITY_TURN_START`
- `MAX_Q` (peak dynamic pressure)
- `STAGE_N` for each stage activation
- `APOAPSIS_COAST_START`
- `BURN_START:<node_name>` and `BURN_END:<node_name>`
- `SOI_CHANGE:<new_body>` when body name changes
- `ORBIT_CONFIRMED` when AP and PE are both within target range
- `ABORT:<reason>` on any unrecoverable error

## Full File-Open Template

Open all three files at the top of the script, before the mission loop:

```python
import os, math, time, krpc

WORKSPACE   = r"C:\path\to\agent_workspace"   # injected by agent
N           = 1                               # attempt number, injected
TEL_FILE    = os.path.join(WORKSPACE, f"telemetry_attempt_{N}.txt")
BURNS_FILE  = os.path.join(WORKSPACE, f"burns_attempt_{N}.txt")
EVENTS_FILE = os.path.join(WORKSPACE, f"events_attempt_{N}.txt")

conn   = krpc.connect(name=f"flight_attempt_{N}")
sc     = conn.space_center
vessel = sc.active_vessel

with open(TEL_FILE,    "w") as tf, \
     open(BURNS_FILE,  "w") as bf, \
     open(EVENTS_FILE, "w") as ef:

    launch_ut = sc.ut
    write_event(ef, vessel, sc, launch_ut, "LAUNCH")
    # ... rest of mission ...
    # write_telemetry(tf, ...) called in every loop
    # write_burn_row(bf, ...) called in every burn loop
    # write_event(ef, ...) called at each milestone
```

## Robustness Checklist

- [ ] All file paths are absolute, not relative.
- [ ] File writes are wrapped in `try/except` — a write failure must never
  crash the flight.
- [ ] `f.flush()` is called after every write so the agent can read partial
  data even if the script crashes mid-flight.
- [ ] The script closes all files via `with` blocks or `finally` clauses.
- [ ] `orbit.speed` is used for SPD, never `flight.speed`.
- [ ] The burn loop has a velocity-fallback stop as well as an RDV-based stop.
- [ ] Eccentricity is logged so hyperbolic escape is immediately visible.

## What the Agent Does with the Data

After the operator reports the flight is done, the agent must:

1. `read_file("telemetry_attempt_N.txt")` — parse every row.
2. `read_file("burns_attempt_N.txt")` — check for overshoot or premature stop.
3. `read_file("events_attempt_N.txt")` — check sequence and timing.
4. Check for `ECC >= 1.0` rows (hyperbolic escape).
5. Check that final BODY is "Mun", not "Kerbin" or "Sun".
6. Check final AP and PE against the target orbit spec.
7. Write findings to `postmortem_attempt_N.md`.

Only after this analysis is complete should the agent form the next attempt's
hypotheses and design the next experiment.

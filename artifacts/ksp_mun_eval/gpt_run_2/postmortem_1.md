## Evidence table — attempt 1

| Metric | Predicted | Observed | Status |
|---|---|---|---|
| Launch TWR adequate | Stable liftoff and ascent | Liftoff succeeded; AP reached 90,152 m at T+194 s | PASS |
| Orbit insertion should occur after coast to AP | Throttle should be 0 during coast | THROTTLE remained 1.00 through all `COAST_TO_AP` telemetry rows from T+198 s onward | FAIL |
| Script should preserve vessel reference after staging | No vessel-handle exception | `ValueError: No such vessel ...` at T+0 exception record while entering apoapsis coast loop | FAIL |
| Phase 1 target | AP 80–100 km | AP reached 90,152 m at T+194 s | PASS |
| Phase 2 target | PE >= 75 km around Kerbin | PE only rose because engines kept firing; by T+214 s PE=24,886 m and by T+229 s PE=51,529 m while still under thrust, not by planned circularization | FAIL |
| Burn logging during node burns | burns_attempt_1.txt populated during circularization/TMI/MOI | burns_attempt_1.txt empty because no node burn was ever executed | FAIL |
| Vehicle margin | Enough dV for orbit + transfer | Fuel exhausted at T+393 s after uncontrolled full-throttle prograde escape; no mission capability evidence for nominal profile | UNRESOLVED |

## Quantitative analysis

### Ascent phase
- Launch at T+2 s.
- Booster separation at T+44 s, ALT=6,117 m.
- Core-to-second-stage event at T+162 s, ALT=50,274 m.
- AP target reached at T+194 s with AP=90,152 m, ALT=59,979 m.
- This confirms the ascent guidance was good enough to reach a target suborbital trajectory.

### Critical violation: throttle never cut after ascent
Predicted behavior after AP target:
- THROTTLE should go to 0.00 during coast to apoapsis.

Observed:
- At T+198 s first `COAST_TO_AP` row still shows THROTTLE=1.00.
- Throttle stays at 1.00 continuously through fuel depletion.
- AP rises uncontrollably: 97 km (T+198) -> 156 km (T+209) -> 637 km (T+229) -> 3,706 km (T+255) -> 22,200 km (T+265).
- At T+270 AP becomes negative (-24,155,235 m), a hyperbolic-escape signature.
- Fuel reaches 0.0% at T+393 s while SPD=6429.4 m/s and PE=153,838 m.

### Exception timing
- The event file records an exception when the script tries to evaluate `while vessel.orbit.time_to_apoapsis > 25:`.
- Exception text: `ValueError: No such vessel ...`
- This is consistent with the original vessel object becoming invalid after staging; likely the script lost the active vessel reference when a stage separated.
- However, telemetry continued after the exception because the game vehicle kept flying under the last commanded state: full throttle.

### Why the operator observed instability on some rebuilds
The manifest created a manually built rocket with radial boosters/fins but did not enforce enough structural guidance or a more stable wide lower stage. The successful logged run did reach space, but operator reports 3 manual build attempts were needed to avoid atmospheric instability, so the manifest is operationally fragile even if one build happened to fly.

## Hypothesis verdict

### U1 ascent guidance
- H1a SUPPORTED for the narrow question of reaching target apoapsis: AP reached 90,152 m.
- But the overall Phase 1->2 transition failed because propulsion did not stop.

### U2 burn stop / control logic
- H2a ELIMINATED for attempt 1 execution path: node execution never began, so dual-condition burn logic was not tested.
- New hypothesis H2d introduced: after ascent staging, the vessel handle changed/invalidated, causing the script to crash before circularization while leaving throttle at 1.00.
- Additional control bug confirmed: after AP target, the script breaks out of ascent loop without explicitly setting a persistent safe throttle state that survives any later exception path. Telemetry directly shows thrust remained open.

### U3 TMI targeting
- Unresolved. Never reached node planning/execution.

### U4 vehicle dV margin
- Unresolved from nominal mission perspective. The rocket had enough raw impulse to fling itself onto escape, but that does not prove adequate controlled mission delta-v or stability margin.

## Root cause

The script retained full throttle after reaching ascent apoapsis target and then crashed on an invalid vessel reference (`No such vessel`) before creating the circularization node, so the rocket continued burning uncontrolled into a hyperbolic escape until fuel exhaustion.

This is falsifiable: if the next script reacquires `sc.active_vessel` after every staging/major transition and forces `throttle = 0.0` before any coast loop, telemetry should show THROTTLE=0.00 immediately after AP target and no `No such vessel` exception.

## Targeted fix

1. **Force throttle-safe state before every coast / planning phase**
   - Set `vessel.control.throttle = 0.0` immediately when AP target is reached and again just before entering any coast loop.
   - In a top-level `finally`/exception handler, attempt to set active vessel throttle to zero.
   - Mechanism: prevents runaway thrust if later code fails.

2. **Reacquire the active vessel after every staging event and before every major phase**
   - Replace stale vessel-object dependence with a helper that refreshes `vessel = sc.active_vessel` and refreshes flight/stream handles as needed.
   - Mechanism: avoids `No such vessel` after decoupling/root-part changes.

3. **Design a more stable rocket manifest**
   - Use a broader and stiffer launcher with Making History high-performance parts, reducing finicky atmospheric handling.
   - Mechanism: reduces operator rebuild instability and gives higher reliability for scripted ascent.

4. **Reduce event spam**
   - `GRAVITY_TURN_START` was written dozens of times. Change to one-shot event.
   - Mechanism: clearer post-flight diagnosis.

## What the next experiment will prove or disprove

Attempt 2 will specifically test:
- H2d: Reacquiring active vessel across staging eliminates the `No such vessel` failure.
- H2e: Explicit coast-throttle safing eliminates runaway thrust after AP target.
- H4c: A sturdier launcher using advanced Making History parts improves ascent robustness while preserving >5250 m/s dV.

Predictions for attempt 2:
- After `AP_TARGET_REACHED`, the next telemetry row will show `THROTTLE=0.00` during `COAST_TO_AP`.
- `events_attempt_2.txt` will contain no `EXCEPTION ... No such vessel`.
- `burns_attempt_2.txt` will be non-empty because at least circularization should execute.
- Telemetry should show stable Kerbin orbit after circularization, with BODY=Kerbin and PE >= 75,000 m.

## Decision for attempt 2

Proceed to a redesigned, more stable rocket and a script hardened against stale vessel references and unsafe throttle persistence.
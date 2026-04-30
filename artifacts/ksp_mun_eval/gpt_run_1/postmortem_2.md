## Evidence table — attempt 2

| Metric / prediction | Predicted | Observed | Δ / note | Status |
|---|---|---|---|---|
| No early `SCRIPT_EXCEPTION` in first 30 s after fixing engine attribute bug | Yes | Yes | First exception occurred much later, at circularization setup | PASS |
| `GRAVITY_TURN_START` occurs and ascent telemetry is collected | Yes | Yes | Event at T+15 s; continuous telemetry through T+368 s | PASS |
| Rocket reaches AP 80–100 km before cutoff | 80–100 km | 90.1 km at T+197 s | Within target | PASS |
| Stable LKO after circularization (`PE >= 75 km`) | Yes | No | Circularization never executed | FAIL |
| Attempt 2 isolates whether attempt-1 failure was purely the SRB API bug | Yes | Yes | Ascent progressed normally, proving the original crash was fixed | PASS |
| Later mission architecture reaches at least node execution | Yes | Partially | CIRC node created, then failure at autopilot wait | PARTIAL |

## Computed observations

### Phase progression from events
Observed sequence:
1. T+0 s `SCRIPT_START`
2. T+2 s `LAUNCH`
3. T+2 s `STAGE_2 DETAIL=liftoff`
4. T+15 s `GRAVITY_TURN_START`
5. T+44 s `STAGE_1 DETAIL=srb_separation`
6. T+163 s `STAGE_0 DETAIL=ascent_auto_stage`
7. T+194 s `APOAPSIS_COAST_START DETAIL=AP=90041`
8. T+379 s `NODE_CREATED:CIRCULARIZE DETAIL=dv=232.80`
9. Exception during `execute_node(..., 'CIRCULARIZE')`

This confirms the ascent-loop software fix worked and the mission advanced to the first orbital burn.

### Ascent performance from telemetry
Key ascent values:
- T+45 s after SRB separation: ALT=9,753 m, SPD=458.4 m/s, AP=18,007 m
- T+166 s after final stage separation: ALT=50,149 m, SPD=1830.3 m/s, AP=67,702 m, STAGE=0
- T+191 s: ALT=58,064 m, SPD=2107.9 m/s, AP=85,095 m
- T+197 s: ALT=59,569 m, SPD=2143.4 m/s, AP=90,099 m, THROTTLE=0.00, PHASE=TO_AP_FOR_CIRC

Interpretation:
- Phase 1 succeeded: apoapsis target was reached without leaving atmosphere first.
- However, at MECO the vessel still had `PE = -134,930 m`, so circularization remained essential.

### Stage-transition effects
Fuel percentages by major stage transitions:
- T+44–45 s SRB separation: fuel jumps from 85.9% to 99.3% because total remaining fuel percentage is computed over the current attached vehicle only; this is expected after dropping spent boosters.
- T+163–166 s final stage separation: fuel jumps from 33.4% to 97.8% for the same reason.

This indicates stage events happened and were recorded. No evidence suggests fuel starvation before orbit.

### Failure mechanism at circularization
The event log and traceback show:
- Circularization node was successfully created with `dv=232.80 m/s`.
- Failure occurred inside `execute_node()` on `ap.wait()`.
- Exception: `ValueError: No such vessel <guid>` originating from the autopilot service.

This is strong evidence that the `vessel` / `auto_pilot` object reference became invalid after the final stage separation at T+163 s. In KSP/kRPC, the active vessel can change identity across staging when the old root part is discarded and the remaining spacecraft becomes a new vessel object. The script continued using the old vessel handle.

The operator’s note (“Crashed into Kerbin after final stage sep”) is consistent with this: after stage separation the surviving upper vehicle continued ballistically while the script later lost authoritative control at circularization, so no orbit was completed and the craft re-entered.

## Quantitative verdict

| Quantity | Value |
|---|---:|
| Ascent cutoff AP | 90.099 km |
| Circularization dV requested | 232.80 m/s |
| Final observed PE before burn | -135.398 km |
| Time from final stage sep to circularization node creation | ~216 s |
| Number of burn rows collected | 0 |

### Why zero burn rows matter
Because the crash occurred before `BURN_START:CIRCULARIZE`, there is no burns-file evidence. Therefore no burn-controller hypothesis is updated by this attempt.

## Hypothesis verdict

- H1 (attempt-1 failure was purely the engine-attribute bug): **CONFIRMED**. Attempt 2 proceeded through full ascent and node creation.
- H2 (additional early ascent bug): **ELIMINATED for early ascent**. No crash occurred in the first 30 s or during ascent logic.
- H3 (current launcher can reach target AP and support LKO attempt): **PARTIALLY CONFIRMED**. Vehicle achieved target AP 90 km with large upper-stage fuel reserve (~85.3% remaining on final stage before circularization), so the launcher is adequate to reach insertion conditions.
- H4 (current manifest/staging is inadequate before LKO): **NOT SUPPORTED by current evidence**. Failure was software/control-reference related, not dV shortage.
- H5/H6 (later mission stack viability): **UNRESOLVED**. A new later-phase software bug blocked circularization.
- New hypothesis H7: **CONFIRMED** — after final stage separation, the active vessel identity changed and the script continued using a stale `vessel` / `auto_pilot` reference, causing `ap.wait()` to fail with `No such vessel`.

## Root cause
After the final stage separation, KSP/kRPC changed the active vessel identity, but the script continued using a stale `vessel.auto_pilot` handle from the pre-separation craft; when circularization began, `ap.wait()` failed with `ValueError: No such vessel`, preventing the burn and leading to ballistic re-entry.

## Targeted fix and mechanistic reason
Fix for attempt 3:
1. After every staging event, reacquire `vessel = sc.active_vessel` and then reacquire dependent objects (`control`, `auto_pilot`, flight references as needed).
2. Before every major phase transition and burn, refresh `vessel = sc.active_vessel` again.
3. In `execute_node()`, do not trust a previously captured autopilot object; reacquire `vessel` and `ap = vessel.auto_pilot` at the start of the function and after any staging during the burn.
4. Add explicit event logging noting vessel refresh after stage changes.

Mechanistic reason:
- If the vessel identity changes across decoupling, reacquiring `sc.active_vessel` rebinds control to the surviving spacecraft. This prevents stale-object failures in autopilot and node execution.

## What attempt 3 will specifically prove or disprove
Attempt 3 is designed to test H7 directly.

Predictions if H7 is correct and the fix works:
- `events_attempt_3.txt` will show stage separation followed by `VESSEL_REFRESH` events.
- Circularization will proceed to `BURN_START:CIRCULARIZE` and `BURN_END:CIRCULARIZE` instead of crashing at `ap.wait()`.
- `telemetry_attempt_3.txt` after circularization will show `BODY=Kerbin` and `PE >= 75,000 m`.

Predictions if H7 is wrong:
- Even after refreshing `sc.active_vessel`, `ap.wait()` or another control call will still fail near circularization, implying a different autopilot/node interaction bug.

## Cross-attempt summary

| Attempt | Final BODY | Final AP (km) | Final PE (km) | Root cause |
|---|---|---:|---:|---|
| 1 | Kerbin | 0.08 (prelaunch row only) | -598.4 | Invalid engine attribute access during SRB check |
| 2 | Kerbin | 90.1 | -135.4 | Stale vessel/autopilot reference after final stage separation |

## Residual uncertainty
- The exact stage numbering in the VAB does not match my initial expectations, but staging functionally occurred.
- A telemetry writer error (`string[] string.Split...`) appeared after the exception; this likely came from accessing a stale object while logging failure state and should disappear once vessel-refresh logic is added, but it warrants defensive refresh in logging too.
- TMI/MOI logic remains completely untested.

## Decision for attempt 3
Proceed to attempt 3 with no rocket redesign. Modify the script so every stage event and every major burn reacquires `sc.active_vessel` and dependent control objects. The next experiment specifically tests whether stale vessel handles after separation were the true cause of circularization failure.

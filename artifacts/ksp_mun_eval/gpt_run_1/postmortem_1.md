## Evidence table — attempt 1

| Metric / prediction | Predicted | Observed | Δ / note | Status |
|---|---|---|---|---|
| Script survives launch and enters ascent loop | Yes | No | Crashed at ~T+1–2 s | FAIL |
| Events order begins `SCRIPT_START -> LAUNCH -> STAGE_* -> GRAVITY_TURN_START` | Yes | `SCRIPT_START -> LAUNCH -> STAGE_4 -> SCRIPT_EXCEPTION` | No gravity turn reached | FAIL |
| Telemetry file contains ascent rows every ~5 s | Yes | Only prelaunch row | Script died before first ascent telemetry interval | FAIL |
| Burns file contains burn rows only during later burns | Possibly none before ascent complete | Empty | Consistent with early crash | N/A |
| Launcher performance hypothesis test (H1.1/H1.2) | Need ascent evidence | No ascent evidence collected | Under-instrumented for vehicle performance because control-flow bug aborted immediately | UNRESOLVED |
| Guidance hypothesis test (H2.1/H2.2) | Need sustained ascent telemetry | No sustained ascent telemetry | Unresolved | UNRESOLVED |
| Burn execution hypothesis test (H4.1/H4.2) | Need burns data | No burns executed | Unresolved | UNRESOLVED |

## Computed observations

### Telemetry
Only one telemetry row exists:
- T+0 s: ALT=80 m, SURF_ALT=8 m, SPD=175.0 m/s, AP=80 m, PE=-598,435 m, BODY=Kerbin, FUEL=100.0%, PHASE=PRELAUNCH, THROTTLE=0.00, STAGE=5

This row is prelaunch and cannot be used to evaluate ascent or orbital performance.

### Events
Observed event sequence:
1. T+0 s `SCRIPT_START`
2. T+2 s `LAUNCH`
3. T+2 s `STAGE_4 DETAIL=liftoff`
4. T+1 s `SCRIPT_EXCEPTION Detail=AttributeError("'Engine' object has no attribute 'engine'")`

The apparent T+1 ordering inversion for the exception is an artifact of using vessel MET in the exception handler rather than the original launch time base.

### Root exception
From events_attempt_1.txt:
```python
active_srb = [e for e in vessel.parts.engines if e.engine.part.title == 'BACC "Thumper" Solid Fuel Booster' and e.active]
```
Observed error:
```python
AttributeError: 'Engine' object has no attribute 'engine'
```

Therefore the script attempted to access `e.engine.part`, but each `e` in `vessel.parts.engines` is already an Engine object. The correct property chain should reference `e.part`, not `e.engine.part`.

## Hypothesis verdict

- H1.1 vs H1.2 (vehicle adequacy): **UNRESOLVED**. No usable ascent telemetry was collected because the script crashed immediately after launch.
- H2.1 vs H2.2 (gravity turn adequacy): **UNRESOLVED**. Guidance logic did not run long enough to observe pitch/apoapsis behavior.
- H3.1 vs H3.2 (TMI planning): **UNRESOLVED**. Mission never reached orbit.
- H4.1 vs H4.2 (burn execution robustness): **UNRESOLVED**. No node burn occurred.
- New software hypothesis H6: **CONFIRMED** — the immediate failure was caused by an API object-model bug: KRPC `vessel.parts.engines` elements are Engine objects whose owning part is `e.part`; accessing `e.engine.part` throws AttributeError and aborts the ascent loop.

## Root cause
The flight script crashed immediately after launch because it used an invalid kRPC object path (`e.engine.part.title`) while checking for active SRBs; in `vessel.parts.engines`, each element is already an Engine object, so the correct attribute is `e.part.title`.

## Targeted fix and mechanism
Fix:
- Replace `e.engine.part.title` with `e.part.title` in the SRB-detection code.
- Add a more defensive SRB separation routine that tolerates missing title matches and does not crash if part inspection fails.
- Make exception timestamps use the same launch time basis as the main logs.

Mechanistic reason:
- This removes the AttributeError that terminated control flow during the first ascent loop iteration, allowing telemetry to continue and enabling the actual launcher/guidance hypotheses to be tested.

## What attempt 2 will specifically prove or disprove
Attempt 2 will test whether, once the SRB-detection API bug is fixed, the baseline launcher and ascent guidance can complete Phase 1 and Phase 2:
- prove/disprove H1.1: vehicle can reach AP 80–100 km and LKO with PE >= 75 km;
- prove/disprove H2.1: gravity turn profile yields a controlled insertion rather than atmospheric or trajectory failure.

Predicted confirming readings for the fix:
- No `SCRIPT_EXCEPTION` within the first 30 s.
- `telemetry_attempt_2.txt` contains multiple ascent rows with increasing ALT and AP.
- `events_attempt_2.txt` contains `GRAVITY_TURN_START` after launch and later `APOAPSIS_COAST_START`.

## Cross-attempt summary

| Attempt | Final BODY | Final AP (km) | Final PE (km) | Root cause |
|---|---|---:|---:|---|
| 1 | Kerbin | 0.08 (prelaunch row only) | -598.4 | Script crashed on invalid engine attribute access during SRB check |

## Residual uncertainty
- The actual rocket performance remains untested.
- The staging setup in the VAB may still need adjustment once ascent is observed.
- The max-Q event logging may spam because it logs every time a new max is reached rather than only near the peak; not mission-critical but worth tightening later.

## Decision for attempt 2
Proceed to attempt 2 with the SRB-inspection fix and slightly more defensive ascent staging logic. The next experiment is specifically aimed at turning the first 2 seconds of flight from a software crash into a fully logged ascent so the vehicle and guidance hypotheses can finally be tested.

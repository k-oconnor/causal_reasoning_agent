## Evidence table — attempt 4

| Metric / prediction | Predicted | Observed | Δ / note | Status |
|---|---|---|---|---|
| After SRB separation, active vessel should continue accelerating while burning core fuel | Yes | Yes | Fuel fell from 99.6% at T+46 s to 22.1% at T+308 s and AP rose to 89 km | PASS |
| Simplified manifest removes ascent ambiguity | Yes | Yes | No detached-dead-stage failure; ascent proceeded normally | PASS |
| AP target 80–100 km reached before coast | 80–100 km | 90.2 km at T+308 s | Within target | PASS |
| Coast to apoapsis then circularize | Yes | No | Orbit became hyperbolic; `time_to_apoapsis` never dropped below 25 s | FAIL |
| Stale-vessel fix can be evaluated at orbit insertion | Yes | Not reached | Circularization node never created due to runaway escape trajectory before apoapsis | UNRESOLVED |

## Computed observations

### Phase progression
Observed event sequence:
1. T+0 s `SCRIPT_START`
2. T+2 s `LAUNCH`
3. T+2 s `STAGE_1 DETAIL=liftoff`
4. T+16 s `GRAVITY_TURN_START`
5. T+45 s `STAGE_0 DETAIL=srb_separation`
6. T+308 s `APOAPSIS_COAST_START DETAIL=AP=90151`
7. T+4933 s `SCRIPT_EXCEPTION DETAIL=RuntimeError('Timeout in phase TO_AP_FOR_CIRC')`

No node creation occurred. The failure was not staging ambiguity; it was ascent cutoff/burn timing logic.

### Ascent performance before cutoff
Key telemetry:
- T+46 s: ALT=9,478 m, SPD=412.4 m/s, AP=15,791 m, FUEL=99.6%, STAGE=0
- T+201 s: ALT=26,633 m, SPD=788.7 m/s, AP=28,424 m, FUEL=53.6%
- T+257 s: ALT=37,189 m, SPD=1422.1 m/s, AP=40,648 m, FUEL=37.1%
- T+303 s: ALT=45,718 m, SPD=2218.3 m/s, AP=61,731 m, FUEL=23.6%
- T+308 s: ALT=46,617 m, SPD=2324.2 m/s, AP=89,056 m, PE=-9,765 m, FUEL=22.1%
- T+313 s: ALT=47,548 m, SPD=2435.4 m/s, AP=191,614 m, PE=27,745 m, THROTTLE=0.00

### Arithmetic showing the overshoot mechanism
At the moment the script decided to stop ascent and enter coast:
- T+308 s AP = 89,056 m (just under target)
- 5 seconds later, with throttle already at 0.00, AP = 191,614 m
- Increase over those 5 s = **+102,558 m**

Then the orbit kept getting more energetic during “coast” telemetry:
- T+318 s AP = 376,098 m
- T+323 s AP = 654,213 m
- T+329 s AP = 1,095,415 m
- T+339 s AP = 3,700,880 m
- T+344 s AP = 12,468,598 m
- T+349 s AP = -16,273,284 m (apoapsis becomes nonsensical/negative → hyperbolic escape symptom)

Meanwhile PE remained positive after T+313 s (~27.7 km to ~58.4 km), meaning the craft was no longer suborbital but on an escape trajectory rather than a parking orbit.

### What this implies
The script cut throttle too late. It used a simple threshold `if apoapsis_altitude >= 90000: throttle = 0`, but at T+308 s the rocket was already moving at 2324.2 m/s while still deep in atmosphere/ascent with a powerful Terrier stage. Because of control-loop latency and the craft’s very high vertical/prograde velocity, the remaining momentum after cutoff was enough to convert the trajectory into a highly energetic escape.

This is not a burn-controller/node issue; it is an ascent guidance issue:
- the gravity turn remained too vertical for too long,
- the vehicle reached high speed at only ~46.6 km altitude,
- and the script used apoapsis threshold alone rather than a predictive cutoff condition based on time-to-apoapsis / vertical speed / lower AP target for this high-Isp upper stage.

### Why the timeout happened
The script then waited for `time_to_apoapsis < 25`. But once the orbit became hyperbolic, `time_to_apoapsis` did not meaningfully converge to a normal apoapsis event, so the coast loop ran until its 4000 s timeout.

The operator’s summary (“final stage drifted off into solar orbit”) is fully consistent with the telemetry: the stage escaped Kerbin and entered a solar trajectory.

## Hypothesis verdict

- H1 (simplified launcher removes ascent ambiguity): **CONFIRMED**.
- H3 (simplified launcher still has enough performance): **CONFIRMED, perhaps too much for current ascent logic**.
- H5/H6 (stale-vessel fix at orbit insertion): **UNRESOLVED** because node execution was never reached.
- New hypothesis H9: **CONFIRMED** — the ascent cutoff logic is too naive for the simplified launcher; using `AP >= 90 km` as the sole MECO trigger causes a large post-cutoff apoapsis overshoot and eventual Kerbin escape.

## Root cause
The ascent guidance cut off based only on instantaneous apoapsis reaching 90 km, but with the Terrier-powered upper stage already accelerating hard at ~46 km altitude, the vehicle’s residual momentum after MECO caused apoapsis to surge from 89 km to hyperbolic escape, so the script entered a coast phase waiting for an apoapsis that no longer existed in a closed orbit.

## Targeted fix and mechanistic reason
Fix for attempt 5:
1. Start with a lower ascent target apoapsis (e.g. 75–80 km) for MECO, not 90 km.
2. Use a more aggressive gravity turn so the vehicle is nearer horizontal by ~35–40 km rather than still climbing steeply at 46 km.
3. Add an ascent safety abort: if apoapsis exceeds 120 km before MECO settles, or if eccentricity approaches/exceeds 1.0, immediately cut throttle and transition to recovery logic rather than waiting for normal apoapsis.
4. During coast, detect hyperbolic/escape condition explicitly (`eccentricity >= 1`, absurd or negative AP) and declare failure instead of waiting 4000 s.
5. Optionally reduce upper-stage ascent thrusting by staging slightly later or lowering throttle during late ascent if AP is rising too rapidly.

Mechanistic reason:
- A lower MECO target and flatter ascent reduce the vertical component of velocity and the amount of apoapsis growth that continues after cutoff. Hyperbolic detection prevents wasting the remaining attempt on a doomed coast.

## What attempt 5 will specifically prove or disprove
Attempt 5 will test H9 directly.

Predictions if H9 is correct and the fix works:
- Telemetry will show MECO nearer AP 75–80 km, with AP growth after cutoff remaining below ~20 km rather than >100 km.
- `APOAPSIS_COAST_START` will be followed by a valid circularization node, then `BURN_START:CIRCULARIZE` and `BURN_END:CIRCULARIZE`.
- Post-circularization telemetry will show `BODY=Kerbin` and `PE >= 75,000 m`.

Predictions if H9 is wrong:
- Even with earlier MECO and flatter ascent, the craft will still overshoot into a non-closed orbit, implying a deeper guidance or staging problem.

## Cross-attempt summary

| Attempt | Final BODY | Final AP (km) | Final PE (km) | Root cause |
|---|---|---:|---:|---|
| 1 | Kerbin | 0.08 | -598.4 | Invalid engine attribute access during SRB check |
| 2 | Kerbin | 90.1 | -135.4 | Stale vessel/autopilot reference after final stage separation |
| 3 | Kerbin | 22.3 | -597.8 | Incorrect staging/build ambiguity; core detached, next stage did not ignite |
| 4 | Kerbin/Sun escape trajectory | hyperbolic after 89 km cutoff | +58.4 before escape | Ascent cutoff too late; apoapsis overshot into escape |

## Residual uncertainty
- The stale-vessel fix still is not directly validated at circularization, because attempts 3 and 4 failed before that point for other reasons.
- The simplified vehicle may still have more ascent performance than ideal; if attempt 5 succeeds to LKO, its excess dV should help TMI/MOI rather than hurt.

## Decision for attempt 5
Proceed to a final attempt with the simplified launcher retained, but revise ascent guidance: flatter gravity turn, lower MECO target, and explicit hyperbolic/apoapsis runaway detection. This final experiment specifically tests whether controlled ascent energy management can convert the now-reliable vehicle into a usable parking orbit.

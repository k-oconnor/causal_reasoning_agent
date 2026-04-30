## Evidence table — attempt 3

| Metric | Predicted | Observed | Status |
|---|---|---|---|
| Pad departure by T+5 s | ALT > 200 m | ALT=337 m at T+5 s | PASS |
| No early RPC crash | Early ascent continues normally | No early exception in events file | PASS |
| First-stage robustness | Booster sep should not compromise ascent | Booster separation at T+38 s while core still ~70% total fuel; ascent performance degraded sharply | FAIL |
| Circularization burn geometry | Burn should start near apoapsis | Node created at T+219 s near ALT=82,791 m but burn executed at T+370 s at ALT=43,492 m | FAIL |
| Circularization effect | PE should rise to >= 75 km | PE worsened from about -461 km to -587 km; AP collapsed to 14.7 km | FAIL |
| burns file behavior | RDV should decrease toward zero | RDV increased from 915 m/s to 1916 m/s during the burn | FAIL |

## Quantitative analysis

### Ascent and staging
- Liftoff succeeded strongly: ALT=337 m at T+5 s.
- Gravity turn began at T+12 s, ALT=1503 m.
- Booster separation occurred at T+38 s, ALT=9846 m.
- Telemetry immediately after separation shows severe performance loss:
  - T+35 s: ALT=8932 m, SPD=483.9 m/s, AP=16,681 m, FUEL=69.8%, STAGE=2
  - T+40 s: ALT=10,757 m, SPD=441.4 m/s, AP=16,045 m, FUEL=97.1%, STAGE=1
  - T+45 s: ALT=12,027 m, SPD=338.7 m/s, AP=13,759 m
- This is direct evidence that the script staged away the still-needed central launch stage or otherwise transitioned to the upper stage too early when the Thumpers expired.

The operator's observation matches the telemetry: a more-than-half-full Mainsail core was effectively lost at booster burnout.

### Apoapsis reached, but on a poor suborbital trajectory
- AP target reached at T+105 s with AP=85,378 m, ALT=35,435 m, SPD=~1515 m/s.
- Remaining fuel at coast start was 31.7%, but orbit was still deeply suborbital with PE≈-458 km.
- Coasting to apoapsis worked correctly this time: throttle remained 0.00 through coast. This confirms the attempt-1 runaway-thrust bug is fixed.

### Circularization timing was catastrophically wrong
- Node created at T+219 s at ALT=82,791 m, which is near apoapsis and appropriate.
- Burn executed at T+370 s at ALT=43,492 m, far below apoapsis.
- Therefore the node UT or wait logic was wrong by roughly 151 s.

This single fact explains why the circularization burn drove the craft into Kerbin instead of orbit: the burn happened on the descending leg deep in atmosphere/upper atmosphere, not at apoapsis.

### Burn-control evidence
Burn log start/end:
- At T+370.37 s, REMAINING_DV=951.70 m/s
- At T+375.43 s, REMAINING_DV=916.31 m/s
- Then RDV reverses and climbs continuously
- At T+426.07 s, REMAINING_DV=1915.88 m/s

This violates the fundamental prediction for a correctly executed node. RDV increasing during a supposed maneuver-node burn means the vehicle was not burning in the intended node direction anymore relative to the node geometry. Because the burn started far from the intended node location, the orbital effect diverged, making the predicted remaining dV larger instead of smaller.

### Final failure values
At abort (T+426 s):
- ALT=7654 m
- AP=14,739 m
- PE=-586,761 m
- BODY=Kerbin
- Not in orbit; imminent surface impact

## Hypothesis verdict

### U1 launch failure cause from attempt 2
- H1a CONFIRMED. A clearly stronger launcher solved pad departure.

### U2 early-script robustness
- H2a SUPPORTED. No early RPC exception occurred; defensive telemetry/access was good enough for ascent.

### New staging hypothesis
- H4: The script's booster separation stage event also discarded the active liquid core / advanced staging in a way that abandoned the Mainsail stage prematurely.
- Supported by telemetry step change at T+38 to T+45 and operator observation.

### New node-timing hypothesis
- H5: The script computes maneuver node UT relative to current `time_to_apoapsis` but then later warps/waits against a stale or mismatched reference, causing execution long after the intended node time.
- Strongly supported by node creation near apoapsis and execution 151 s later at 43 km altitude.

### Burn stop logic hypothesis
- The dual-condition fallback itself is not the primary issue here. The deeper problem is that the burn was initiated at the wrong orbital location, making both node RDV and speed-delta logic meaningless for circularization.

## Root cause

Attempt 3 failed because the script staged away the needed Mainsail core when the Thumpers expired, producing a poor suborbital trajectory, and then executed the circularization burn about 151 seconds after the intended apoapsis node time, so the burn occurred while descending at 43 km altitude and drove the vessel into Kerbin.

This is falsifiable: in the next attempt, if stage sequencing is simplified so booster separation cannot discard the core, and if node execution logs both `node.ut` and `sc.ut` at burn start with a tolerance under ~2 s, then telemetry should show circularization beginning near apoapsis altitude and PE rising instead of falling.

## Targeted fix

1. **Use a manifest where booster separation is structurally impossible to confuse with core separation**
   - Separate boosters radially, but keep the core and upper stack in clearly distinct stage icons/order; alternatively use a no-booster first stage with very high thrust.
   - Mechanism: removes accidental loss of the central core at booster burnout.

2. **Add explicit timing instrumentation for node execution**
   - Log `NODE_EXECUTE detail=node_ut=..., current_ut=..., dt=...`.
   - Abort if absolute timing error exceeds a few seconds.
   - Mechanism: prevents silent late burns.

3. **Recompute burn start from the node's own UT and verify burn begins before apoapsis passes**
   - Before throttle-up, compare `sc.ut` to `node.ut`; if already late, either abort or retarget with a fresh node.
   - Mechanism: stops performing a circularization burn on the descending leg.

4. **Use a simpler ascent architecture**
   - Prefer a robust all-liquid first stage with no booster staging ambiguity, even at some mass penalty.
   - Mechanism: reduces staging-caused trajectory errors.

## On the operator suggestion (“just kalman filter yourself to Mun past 40k ft”)
That suggestion points toward closed-loop guidance rather than precomputed maneuver-node timing. The data supports moving in that direction for ascent/transfer robustness:
- We can use telemetry/state estimation and direct target metrics (AP target, PE target, closest-approach improvement) rather than trusting one-shot node timing.
- For ascent/circularization in particular, a direct closed-loop controller is likely more robust than the current node timing implementation.

## What the next experiment will prove or disprove

Attempt 4 should test two concrete changes:
- H6: A no-ambiguity first stage plus explicit stage-event validation prevents premature loss of the core.
- H7: Closed-loop circularization (burn until PE target is achieved near apoapsis) is more reliable than delayed node execution.

Predictions:
- After booster/core transitions, telemetry speed and AP will continue increasing rather than collapsing.
- Circularization phase will begin with ALT near AP altitude (>75 km), not at 43 km.
- Burns log for circularization will show PE increasing monotonically toward >= 75 km.

## Decision for attempt 4

Shift away from fragile maneuver-node circularization and toward a simpler closed-loop ascent-to-orbit approach, with a rocket whose stage sequence cannot discard the core at booster separation.
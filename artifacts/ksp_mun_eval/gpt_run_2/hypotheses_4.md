## Current belief state (attempt 4)

From postmortems 1-3:
- Runaway throttle after ascent cutoff is fixed.
- Early kRPC reference-frame robustness is improved.
- Remaining dominant failures are architectural: ambiguous stage sequencing and unreliable delayed node execution for circularization.
- The operator suggested a more closed-loop guidance style. The evidence supports that: the mission needs direct state-feedback control rather than reliance on a maneuver node whose timing can go stale or be executed late.

## Competing hypotheses

### U1. Circularization method
- H1a: Closed-loop circularization based directly on apoapsis/periapsis and `time_to_apoapsis` will be more reliable than maneuver-node execution.
- H1b: Closed-loop circularization will still fail because ascent leaves too little margin or wrong geometry.

### U2. Vehicle architecture
- H2a: A boosterless high-thrust liquid first stage eliminates accidental premature core loss and yields more predictable ascent.
- H2b: Removing boosters will hurt ascent efficiency too much, preventing orbit.

### U3. Transfer strategy
- H3a: Once LKO is reliable, closed-loop prograde TMI plus encounter checks can replace fragile node-centric timing for transfer as well.
- H3b: Even with LKO achieved, Mun transfer will still require node-based refinement.

## Predictions

If H1a and H2a are correct:
- `events_attempt_4.txt` will show no premature staging around booster burnout, because there are no boosters.
- `telemetry_attempt_4.txt` will show AP reaching 80-90 km, throttle cutting, then a circularization phase near apoapsis with PE increasing monotonically toward >= 75 km.
- `burns_attempt_4.txt` during circularization will show PE rising rather than falling.
- `events_attempt_4.txt` will contain `LKO_CONFIRMED`.

If H1b or H2b are correct:
- Telemetry will show either inability to reach target AP with remaining fuel, or PE failing to rise despite correct timing.

## Experiment design

Changes from attempt 3:
1. New boosterless, all-liquid rocket with clearly separated stages.
2. Replace node-based circularization with closed-loop burn at apoapsis: point prograde and burn until PE >= 75 km.
3. If LKO is reached with margin, continue to Mun using simplified transfer logic; otherwise the main objective of this experiment is to confirm reliable LKO.
4. Add instrumentation for start altitude and time-to-apoapsis at circularization burn start.
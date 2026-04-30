## Current belief state (attempt 2)

Based on postmortem_1.md:
- Attempt 1 did not test rocket performance or mission logic because the script crashed immediately after launch.
- The immediate cause was a kRPC API misuse: `vessel.parts.engines` items are Engine objects, so `e.engine.part` is invalid; `e.part` must be used.
- Therefore the highest-value next experiment is not a redesign of the rocket but a minimal software correction that allows ascent telemetry to be collected.

## Competing hypotheses

### Uncertainty U1: Was the first failure purely an API bug, with the underlying ascent architecture otherwise viable?
- H1: Replacing `e.engine.part.title` with `e.part.title` and making SRB separation logic defensive will eliminate the early crash; the vehicle will proceed into normal ascent.
- H2: There are additional ascent-loop logic bugs beyond the engine-attribute bug, so the script will still crash early even after the fix.

### Uncertainty U2: Can the current launcher and ascent profile reach a workable parking orbit?
- H3: The current manifest has enough TWR and dV for AP 80–100 km and Kerbin PE >= 75 km.
- H4: The current manifest or staging arrangement is inadequate, causing failure before LKO despite the software fix.

### Uncertainty U3: Is the later mission stack (TMI/MOI) likely to be reachable once ascent works?
- H5: The baseline script architecture is sound enough that, if ascent works, later phases can at least progress to LKO or beyond.
- H6: Additional latent bugs will appear in later phase transitions even if ascent succeeds.

## Predictions

If H1 is correct:
- `events_attempt_2.txt` will not contain `SCRIPT_EXCEPTION` in the first 30 s.
- `events_attempt_2.txt` will contain `GRAVITY_TURN_START` and likely an SRB separation event after launch.
- `telemetry_attempt_2.txt` will contain multiple ascent rows with ALT and AP increasing over time.

If H2 is correct:
- A new exception will occur during ascent, likely before `APOAPSIS_COAST_START`, with a different traceback or location.

If H3 is correct:
- Telemetry will show AP entering 80,000–100,000 m before throttle cutoff.
- After circularization, telemetry will show `BODY=Kerbin` and `PE >= 75,000 m`.

If H4 is correct:
- Telemetry will show one of: AP never reaches 80 km, fuel depletion before circularization, uncontrolled trajectory, or destruction.

If H5 is correct:
- Events may continue beyond LKO into `NODE_CREATED:TMI`, `BURN_START:TMI`, or encounter-related events.

If H6 is correct:
- Later events or logs will reveal a new specific failure mode after ascent is fixed.

## Experiment design

Changes from attempt 1:
- Fix SRB engine identification to use `e.part.title`.
- Make SRB detection robust by wrapping part-title matching in safe logic and falling back to `has_fuel` checks rather than assuming a particular engine object structure.
- Fix exception time-base consistency so event timestamps remain interpretable.
- Keep manifest unchanged to isolate software effects.

This experiment directly tests H1 vs H2. If ascent proceeds, it also begins testing H3 vs H4 without changing vehicle design.

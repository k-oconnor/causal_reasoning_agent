## Current belief state (attempt 1)

Workspace recovered as empty, so there is no usable prior telemetry or postmortem evidence on disk.
Operator reports a prior agent made a poor attempt, but no artifacts are present here; therefore I treat the system as effectively untested in this workspace.

Known constraints from reference material:
- The script must self-log telemetry, burns, and events to the workspace.
- `vessel.orbit.speed` must be used for SPD, not `flight.speed`.
- Burn execution must use dual stop criteria: node remaining dV and delivered speed fallback.
- A robust Mun transfer should use a nominal Hohmann burn plus a local sweep of node UT and prograde dV to secure an encounter.

## Competing hypotheses

### Uncertainty U1: Can a simple, high-margin launcher plus conservative guidance reach stable LKO reliably enough to support the Mun mission?
- H1.1: A 3-stage launcher with solid booster assist and a Terrier transfer stage, total vacuum dV > 5,250 m/s and launch TWR > 1.3, will reach LKO with substantial margin.
- H1.2: The launcher design is underperforming due to poor TWR, drag, or insufficient ascent-stage dV, causing failure before or during circularization.

### Uncertainty U2: Will the ascent guidance profile produce a controlled AP of 80–100 km without excessive drag/gravity losses?
- H2.1: A linear gravity turn from ~90 deg at 1 km to ~0 deg at 45 km, with throttle limiting at high dynamic pressure and MECO near AP 90 km, will produce a workable parking orbit.
- H2.2: The gravity turn is too aggressive or too shallow, leading to either atmospheric losses, instability, or an unusable insertion profile.

### Uncertainty U3: Will the transfer planning method secure a Mun encounter without a fragile long phase-angle wait?
- H3.1: A nominal Hohmann TMI from ~80–90 km Kerbin orbit, followed by a local sweep over node time and prograde dV, will yield `next_orbit.body == Mun`.
- H3.2: The sweep logic or scoring is insufficient, failing to produce a Mun encounter.

### Uncertainty U4: Will node execution remain accurate through staging and low-thrust upper-stage burns?
- H4.1: Dual-condition burn stop (`remaining_delta_v < 0.5` OR delivered speed >= 98% target) plus throttle taper will prevent large overshoot even if node RDV drifts.
- H4.2: RDV becomes stale or the speed fallback is insufficient, causing over/under-burn and mission failure.

### Uncertainty U5: Will the mission complete with a stable Mun orbit, not just an encounter?
- H5.1: If arrival periapsis is ~20–40 km, a periapsis retrograde burn can capture into an orbit with PE >= 10 km and AP <= 500 km.
- H5.2: Arrival geometry or fuel margin will be insufficient to complete MOI.

## Predictions

### Predictions for U1 / U2
If H1.1 and H2.1 are correct:
- `events_attempt_1.txt` will contain `LAUNCH`, `GRAVITY_TURN_START`, at least one `STAGE_` event, `APOAPSIS_COAST_START`, `BURN_START:CIRCULARIZE`, and `BURN_END:CIRCULARIZE` in that order.
- `telemetry_attempt_1.txt` will show AP rising into 80,000-100,000 m before cutoff.
- After circularization, telemetry will show `BODY=Kerbin` and `PE >= 75,000 m`.

If H1.2 is correct:
- Telemetry will show AP never reaching 80,000 m, or fuel dropping to near 0 before LKO, or a crash/destruction before `BURN_END:CIRCULARIZE`.

If H2.2 is correct:
- Telemetry will show either extreme dynamic-pressure symptoms indirectly (slow speed gain at low altitude, prolonged time in atmosphere), or insertion with AP/PE far from targets despite adequate fuel.

### Predictions for U3
If H3.1 is correct:
- `events_attempt_1.txt` will contain `BURN_START:TMI`, `BURN_END:TMI`, then `ENCOUNTER_CONFIRMED` or `SOI_CHANGE:Mun`.
- Telemetry after TMI coast will eventually show `BODY=Mun`.

If H3.2 is correct:
- TMI burn completes but no subsequent Mun SOI change occurs; final body remains Kerbin or Sun.

### Predictions for U4
If H4.1 is correct:
- `burns_attempt_1.txt` will show each burn ending with THROTTLE dropping to 0.00.
- Speed gained during burns will be near node.delta_v target; no runaway high-throttle tail should appear.
- If staging occurs during a burn, either RDV reaches near zero or the speed-fallback still terminates the burn close to target.

If H4.2 is correct:
- Burns log will show THROTTLE staying >0 deep past the expected end, or large speed overshoot/undershoot compared to target, possibly with stage-change anomalies.

### Predictions for U5
If H5.1 is correct:
- After MOI, telemetry will show `BODY=Mun`, `PE >= 10,000 m`, `AP <= 500,000 m`, and THROTTLE=0 through one full orbit period.
- `events_attempt_1.txt` will include `BURN_START:MOI`, `BURN_END:MOI`, and `ORBIT_CONFIRMED`.

If H5.2 is correct:
- Telemetry after Mun SOI entry will show either escape (`ECC >= 1`), impact-risk periapsis, or insufficient fuel before orbit closure.

## Experiment design

This first instrumented attempt is designed to test the entire baseline mission architecture end-to-end while maximizing diagnosability.

Design choices:
- Use a conservative, overbuilt 3-stage rocket with high total dV margin.
- Use explicit event logging for all phase changes, staging, node creation/removal, encounter detection, SOI changes, and exceptions.
- Use 5 s telemetry logging throughout and 0.25 s burn logging during active burns.
- Use robust node execution with velocity fallback.
- Use a local TMI search rather than a fragile phase-angle-only wait.
- At Mun arrival, target capture into roughly 20-100 km orbit first; then, if needed, perform a trim burn to ensure AP <= 500 km and PE >= 10 km.

This experiment primarily tests H1.1, H2.1, H3.1, H4.1, and H5.1 simultaneously, with instrumentation sufficient to isolate which phase fails if the full mission does not succeed.

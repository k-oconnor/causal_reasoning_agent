## Current belief state (attempt 1)

- No prior flight evidence exists in the workspace.
- The most robust first attempt is a conservative, over-capable 3-stage liquid rocket with strong launch TWR and a vacuum-optimized upper stage.
- The main mission risks on attempt 1 are not part insufficiency but script/control failure: ascent guidance, burn stop logic, and Mun transfer targeting.
- The reference material indicates a robust Mun approach: reach stable 80–100 km LKO, analytically estimate TMI dV, numerically sweep node timing/prograde for a Mun encounter, then capture at Mun periapsis.

## Material uncertainties and competing hypotheses

### U1. Will the ascent guidance place the vessel into a useful parking orbit without wasting too much delta-v?
- H1a: A linear gravity turn from 90 deg at 1 km to 0 deg at 45 km, with throttle reduction at high dynamic pressure, will produce AP 80–100 km and permit circularization to PE >= 75 km.
- H1b: The gravity turn is too aggressive, causing low vertical speed / excessive drag / failure to reach AP target.
- H1c: The gravity turn is too shallow, causing AP overshoot or near-vertical ascent and poor orbital efficiency.

### U2. Will the node-execution logic stop burns accurately enough despite possible kRPC/node inconsistencies?
- H2a: Dual-condition burn stop (remaining_delta_v plus orbital-speed-change fallback) will stop circularization, TMI, and MOI close enough to target.
- H2b: remaining_delta_v will become stale or inaccurate after staging or mass change, but the velocity fallback will still prevent severe overshoot.
- H2c: Both stop conditions are insufficiently tuned, causing significant overshoot/undershoot.

### U3. Will the TMI targeting method achieve a Mun encounter on the first attempt?
- H3a: A sweep around nominal Hohmann dV and burn time near next apoapsis will find a node whose predicted next orbit is Mun with periapsis in a capturable range.
- H3b: The sweep range/resolution is too small, so no encounter is found despite adequate vehicle performance.
- H3c: The encounter is found but the execution timing accuracy is too poor, leading to a miss after the real burn.

### U4. Will the designed rocket have adequate dV margin at Mun arrival?
- H4a: The manifested rocket provides > 5250 m/s total and enough upper-stage dV for TMI + MOI + corrections.
- H4b: Real ascent losses are high enough that the final stage arrives at Mun with inadequate fuel for capture.

## Predictions

### Predictions for U1
If H1a is correct:
- `events_attempt_1.txt` will show orderly launch and gravity-turn progression with no abort before orbit.
- `telemetry_attempt_1.txt` will show AP first crossing 80,000 m while BODY=Kerbin and ALT < 70,000 m or shortly after atmospheric exit, then a coast to apoapsis and circularization.
- After circularization, telemetry will show BODY=Kerbin and PE >= 75,000 m.

If H1b is correct:
- Telemetry will show low horizontal speed growth, AP plateauing below 80,000 m, or fuel depletion/staging before orbit.

If H1c is correct:
- Telemetry will show AP rising too fast with poor PE recovery, possibly AP > 120,000 m before stable orbit, or excessive drag signatures during lower atmosphere.

### Predictions for U2
If H2a is correct:
- `burns_attempt_1.txt` will show RDV decreasing toward < 1 m/s near burn end and throttle tapering from 1.00 toward low values before cutoff.
- Event log will show BURN_END entries with no script exception and resulting orbit parameters near target after each burn.

If H2b is correct:
- Burns file may show RDV behavior inconsistent with delivered speed change, but throttle will still cut when speed change reaches ~98% of target dV.
- Resulting overshoot should remain modest (< ~50 m/s equivalent on orbit-shaping burns).

If H2c is correct:
- Burns file will show either prolonged throttle after target orbit should have been achieved, or cutoff too early with large residual orbit error.

### Predictions for U3
If H3a is correct:
- `events_attempt_1.txt` will show NODE_CREATED/TMI-related events followed by a logged predicted encounter with Mun.
- After TMI execution, telemetry/events will show `BODY=Kerbin` then an SOI change to `BODY=Mun`.

If H3b is correct:
- Events will show no acceptable encounter found in the sweep and a script abort or fallback path before TMI.

If H3c is correct:
- The node prediction will indicate Mun encounter, but after burn execution `next_orbit` will no longer be Mun or closest approach will remain large; no SOI change occurs.

### Predictions for U4
If H4a is correct:
- Final stage will retain significant propellant after LKO and still have enough for TMI and MOI.
- During Mun approach, telemetry will show fuel remaining > 5% before MOI and stable Mun orbit after capture.

If H4b is correct:
- Telemetry will show low fuel prior to or during MOI, with inability to raise Mun periapsis to >= 10 km or apoapsis to <= 500 km.

## Experiment chosen for this iteration

Attempt 1 will test H1a + H2a/H2b + H3a + H4a together using:
- A conservative high-margin 3-stage rocket manifest.
- Fully instrumented script with telemetry every 5 s, burn logging every 0.25 s, and explicit events for staging, node creation/removal, burn boundaries, SOI changes, and exceptions.
- Dual-condition burn termination and TMI node sweep.

This is the highest-information first experiment because it can reveal whether any failure is caused by vehicle design, ascent guidance, transfer targeting, or burn-control logic.
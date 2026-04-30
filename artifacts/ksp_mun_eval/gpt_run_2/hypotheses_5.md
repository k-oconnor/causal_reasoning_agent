## Current belief state (attempt 5)

Based on postmortem_4.md and direct inspection of telemetry_attempt_4.txt / flight_attempt_4.py:
- The rocket architecture from attempt 4 is likely adequate in raw delta-v and initial ascent stability.
- Attempt 4 failed before orbit because staging logic used total-vessel propellant percentage (`fpct(v)`), which stayed at 37.1% after the first stage emptied because upper stages still contained fuel.
- The ascent loop therefore never called `activate_next_stage()` after launch, so the vehicle coasted to ~50.4 km and impacted Kerbin.
- The event `ABORT failed_pad_departure` was misnamed; telemetry shows the failure happened after a substantial ascent, not on the pad. This label should be corrected for interpretability.
- Mission-critical remaining uncertainty is no longer whether the rocket can lift off, but whether stage transitions can be sensed robustly enough to reach orbit and continue through TMI/MOI.

## Material uncertainties and competing hypotheses

### U1 — Why did stage 1 separation fail in attempt 4?
- H1a: The failure was caused by using total-vessel fuel percentage as the staging sensor; once the first stage emptied, total fuel remained high because upper stages were still full.
- H1b: The failure was caused by engine-thrust / autopilot / aerodynamic instability rather than the staging sensor.

### U2 — What sensor should trigger staging reliably in attempt 5?
- H2a: Stage based on active-engine fuel depletion (`all(active_engines have_fuel == False)`) plus a minimum time gap; this will trigger promptly at burnout.
- H2b: Stage based on a thrust-collapse sensor (`throttle commanded high` AND `available_thrust or thrust near zero`) plus altitude/time guard; this will trigger even if engine fuel flags are imperfect.
- H2c: Either sensor alone is brittle; using both in OR logic will be more reliable.

### U3 — Will the vehicle still have enough performance after fixing staging?
- H3a: Yes; if staging occurs promptly near first-stage burnout, apoapsis will resume increasing beyond 85 km and the mission can reach at least LKO.
- H3b: No; the rocket is underperforming and even with correct staging it will still fail to reach orbital conditions.

## Predictions

### Predictions for U1
If H1a is correct:
- `events_attempt_5.txt` will show a `STAGE` event within roughly 0–5 s after the first sustained period where active first-stage engines report no fuel or thrust collapses.
- `telemetry_attempt_5.txt` will no longer show a long plateau at constant `FUEL` with unchanged `STAGE` during ascent.
- After staging, `AP` should continue rising rather than stagnating near ~50 km.

If H1b is correct:
- Even with revised staging logic, either no clean `STAGE` event will occur or post-stage ascent will immediately become unstable / lose AP growth.
- Telemetry will show AP stagnation or loss despite successful stage separation.

### Predictions for U2
If H2a is correct:
- Just before staging, `events_attempt_5.txt` will record engine fuel depletion details, and stage separation will occur while commanded throttle remains > 0.9.
- There will be no long delay between engine burnout and stage event.

If H2b is correct:
- The event log will show thrust-collapse metrics crossing threshold before staging, even if fuel flags remain ambiguous.

If H2c is correct:
- At least one of the two conditions will trigger every required staging event; ascent will proceed cleanly through stage 1 and stage 2 separations.

### Predictions for U3
If H3a is correct:
- `telemetry_attempt_5.txt` will show `AP >= 85000 m` before engine cutoff.
- `events_attempt_5.txt` will contain `LKO_CONFIRMED` and ideally `MUN_ENCOUNTER_CONFIRMED` later in the mission.

If H3b is correct:
- Even after corrected staging, ascent terminates with `AP < 85000 m` or circularization aborts due to low fuel.

## Experiment design

This attempt directly tests H1a/H2c by changing only the sensing and control logic for staging and by instrumenting the relevant sensor values.

Changes from attempt 4:
1. Replace total-vessel fuel-percentage staging with a robust depletion detector using active engine `has_fuel` state OR thrust collapse while throttle is commanded high.
2. Log explicit staging-check events containing current stage, active-engine count, active-engine has_fuel flags, thrust, available_thrust, and total fuel percentage.
3. Correct abort naming so the event reflects actual failure mode (e.g. ascent failure / impact after ascent, not pad departure).
4. Keep the manifest architecture essentially the same to isolate the software fix.

This experiment is designed to prove or disprove that staging-sensor repair alone is sufficient to restore ascent continuity and allow the mission to proceed beyond the attempt-4 failure boundary.
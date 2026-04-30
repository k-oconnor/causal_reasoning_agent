## Evidence table — attempt 4

| Metric | Predicted | Observed | Status |
|---|---|---|---|
| Boosterless staging simplicity | Stage separation should occur cleanly by fuel threshold | No stage separation event occurred at all | FAIL |
| Launch robustness | Strong ascent to AP target | Initial ascent reached ALT ~50 km, AP ~52 km before engine burnout | PARTIAL |
| Stage trigger correctness | First-stage separation should occur once liquid stage nearly empty | Fuel plateaued at 37.1% from T+66 s onward while STAGE remained 2 and no stage event occurred | FAIL |
| Closed-loop ascent to AP 85 km | AP should continue increasing or reach cutoff | AP peaked around 51,828 m at T+66 s, then stagnated and fell | FAIL |

## Quantitative analysis

### What happened
- Launch was successful and stable at first.
- Peak ascent metrics from telemetry:
  - T+66 s: ALT=23,087 m, SPD=1073.1 m/s, AP=51,828 m, FUEL=37.1%
- After T+66 s, fuel percentage stays exactly 37.1% for the rest of the log.
- That flat fuel signal means the active first stage had burned out and the remaining 37.1% fuel was trapped in upper stages.
- No `STAGE` event ever occurred after launch.
- The vehicle then coasted ballistically upward to ~50.4 km and fell back into the ocean.

### Why stage separation never happened
The script used total-vessel fuel percentage `fpct(v) < 12` to trigger first-stage separation.
But upper stages still contained fuel, so total-vessel fuel never dropped below 37.1% even after the first stage was completely empty.
Therefore the condition was never satisfied.

This is a strong falsifiable root cause because the telemetry plateau is exact and persistent.

### Implications
- The manifest itself may be acceptable structurally.
- The main failure is now a **stage-resource sensing bug**: using total vehicle fuel percentage instead of current-stage depletion to decide staging.
- This also explains why the rocket never reached the closed-loop circularization logic: ascent never achieved the AP cutoff.

## Hypothesis verdict

### U1 circularization method
- Untested in attempt 4. The script never reached circularization.

### U2 vehicle architecture
- H2a partially supported: boosterless design removed prior ambiguity and launched stably.
- But mission still failed due to staging logic, not vehicle instability.

### New staging hypothesis
- H4 confirmed: total-vessel fuel percentage is the wrong sensor for stage depletion. It hides empty lower stages when upper stages still contain propellant.

## Root cause

Attempt 4 failed because stage separation logic used total-vessel propellant percentage, so the script never detected that the Mainsail first stage was empty; the rocket therefore never staged, coasted to ~50 km apoapsis, and fell back to Kerbin.

This is falsifiable: if the next script stages based on current-stage thrust loss plus a stage-specific fuel/depletion check, telemetry should show a stage event shortly after first-stage burnout and continued ascent thereafter.

## Targeted fix

1. **Stage on active-engine depletion, not total vessel fuel percentage**
   - Detect stage exhaustion with active engine state / available thrust / resource-in-decouple-stage checks.
   - Mechanism: isolates the currently burning stage instead of being confused by fuel in upper stages.

2. **Add explicit stage-depletion instrumentation**
   - Log current stage number, thrust, available thrust, and stage-resource readings at staging decision time.
   - Mechanism: makes the next staging failure directly observable.

3. **Retain the boosterless manifest**
   - Since the vehicle launched stably, keep the architecture and only repair the staging sensor/control logic.

## What the next experiment would prove or disprove

If there were another attempt, it should test:
- H5: staging based on current active-engine depletion will allow the rocket to continue ascent and reach AP >= 85 km.
- Prediction: a `STAGE` event should appear soon after fuel plateau / thrust drop, and telemetry should show AP resuming growth after staging rather than stagnating at ~50 km.

## Decision

No mission success yet. The dominant remaining issue is well diagnosed: staging logic must use current-stage depletion rather than total vessel fuel percentage.
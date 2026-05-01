## Evidence table — attempt 2

| Metric | Predicted | Observed | Status |
|---|---|---|---|
| Launch TWR >= 1.3 | Vehicle should leave pad immediately | ALT stayed ~81 m -> 77 m -> 70 m from T+5 to T+15 s; no liftoff | FAIL |
| New manifest should improve ascent robustness | Stable pad departure | Vehicle remained on pad while fuel drained | FAIL |
| Script should avoid attempt-1 vessel exception | No `No such vessel` exception | Different exception occurred: `RPCError ... string.Split ...` when calling `vessel.surface_reference_frame` | PARTIAL/FAIL |
| Burn logs should exist if orbital burn reached | burns file non-empty | burns_attempt_2.txt empty | FAIL |
| Stage logic orderly | No accidental over-staging on pad | Telemetry STAGE changed 4 -> 2 while still on pad by T+15 s | FAIL |

## Quantitative analysis

### Pad behavior
Telemetry rows:
- T+5 s: ALT=81 m, SPD=174.7 m/s, FUEL=98.7%, THROTTLE=1.00, STAGE=4
- T+10 s: ALT=77 m, FUEL=97.3%, THROTTLE=1.00, STAGE=4
- T+15 s: ALT=70 m, FUEL=100.0%, THROTTLE=1.00, STAGE=2

Interpretation:
- The vehicle did not gain altitude; it slightly settled/shifted on the pad.
- Fuel consumption between T+5 and T+10 confirms some engines/boosters were firing.
- Stage count dropping from 4 to 2 while still on the pad indicates the script's thrust-based staging heuristic misfired, likely because thrust was low/zero after booster depletion or due to pad clamping, causing premature stage activation.

### Launch TWR diagnosis
The manifest assumed all of the following ignited in the first stage:
- 1x Skiff
- 2x Thumper

That theoretical total thrust was ~740.91 kN for ~56.0 t, TWR ~1.35.

Observed reality strongly supports that actual launch thrust was lower than manifest expectation. Likely explanations:
1. Operator staging order in the built vehicle did not ignite the Skiff together with the boosters.
2. The Skiff/booster combination on this assembled rocket still produced insufficient effective pad thrust due to staging misconfiguration.
3. The script's stage heuristics over-staged on the pad after initial ignition.

Because the telemetry never showed altitude increase, the exact root cause among these is less important than the design conclusion: **attempt-2 launch configuration was not robust to real staging/build conditions.**

### Script exception
Exception occurred at:
- `surf = vessel.flight(vessel.surface_reference_frame)`
- Error: `RPCError: string[] string.Split(char,System.StringSplitOptions)`

This indicates a kRPC-side issue when repeatedly reacquiring/using `surface_reference_frame` on the active vessel during the failed pad state. It is not the same as attempt 1's stale-vessel error, but it still shows the script needs more defensive handling around flight/reference-frame calls.

## Hypothesis verdict

### U1 attempt-1 crash source
- H1a not fully tested. The prior `No such vessel` failure did not recur, so reacquiring active vessel may have helped.
- However, a new kRPC reference-frame-related RPC error occurred, so the broader robustness problem remains unresolved.

### U2 runaway thrust
- H2a SUPPORTED as fixed in this attempt: there was no runaway coast-to-space burn. The attempt failed before launch, not from persistent throttle after apoapsis cutoff.

### U3 advanced launcher stability and adequacy
- H3a ELIMINATED for this specific manifest: the manifested vehicle did not robustly launch.
- New hypothesis H3c: relying on a marginal TWR core with auxiliary boosters plus manual staging setup is too fragile; a substantially higher-thrust first stage is required.

### U4 reach stable LKO
- H4a ELIMINATED for attempt 2 because the vehicle failed at launch.

## Root cause

Attempt 2 failed because the manifested first stage had insufficiently robust real-world launch thrust/staging behavior, causing the rocket to remain on the pad while consuming fuel and prematurely staging, after which the script hit a kRPC reference-frame RPC error.

This is falsifiable: a next design with a clearly overpowered liquid first stage (without depending on borderline booster/core ignition assumptions) should show ALT increasing within the first 5 seconds and STAGE remaining unchanged until actual depletion.

## Targeted fix

1. **Replace the marginal first stage with an unequivocally high-thrust core**
   - Use a `RE-M3 "Mainsail" Liquid Fuel Engine` or `LV-TX87 "Bobcat"` cluster on a heavier core so launch TWR is comfortably > 1.5.
   - Mechanism: removes dependence on delicate booster staging for pad departure.

2. **Simplify staging logic in script**
   - Do not infer staging from transient `thrust < 1` near the pad.
   - Instead gate booster separation by altitude/time and only stage liquid cores when fuel percentage in current stack is clearly low and altitude is safely above the pad.
   - Mechanism: prevents pad over-staging.

3. **Wrap flight/reference-frame reads more defensively**
   - Use a helper that retries `vessel.flight(vessel.surface_reference_frame)` or falls back to cached values instead of crashing immediately.
   - Mechanism: tolerates kRPC reference-frame RPC glitches.

## What the next experiment will prove or disprove

Attempt 3 will test:
- H3c: a clearly overpowered launcher solves pad departure and ascent instability.
- H5: staging logic constrained by altitude/time rather than transient thrust prevents accidental on-pad stage consumption.
- H6: defensive telemetry acquisition avoids the `string.Split` RPC crash.

Predictions:
- `telemetry_attempt_3.txt` at T+5 s will show ALT > 200 m and rising.
- STAGE will not drop more than one step in the first 20 s unless an intentional booster separation event is logged.
- No RPC exception will appear in `events_attempt_3.txt` during early ascent.

## Decision for attempt 3

Redesign with a much stronger, simpler launcher and harden the telemetry/reference-frame access paths before reattempting.
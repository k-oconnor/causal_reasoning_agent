## Current belief state (attempt 3)

From postmortem_1.md and postmortem_2.md:
- Attempt 1 proved ascent guidance can roughly shape a useful trajectory, but software safety around throttle and vessel/reference handling was inadequate.
- Attempt 2 proved the revised launcher manifest was not robust enough to leave the pad reliably in practice.
- Therefore the next experiment should remove pad-TWR ambiguity entirely and simplify the flight stack.
- We should prefer an obviously powerful first stage with a vacuum-optimized upper stage, rather than a marginal Skiff-plus-booster compromise.

## Competing hypotheses

### U1. Launch failure cause
- H1a: Attempt 2 failed primarily because the real launch-stage thrust/staging arrangement was too marginal/fragile.
- H1b: Attempt 2 failed primarily because of operator staging construction mismatch, not the basic launcher concept.

### U2. Early-script robustness
- H2a: Defensive wrappers around flight/reference-frame access will prevent the `string.Split` RPC error from killing ascent logging/control.
- H2b: The RPC error is symptomatic of a deeper kRPC issue and may recur regardless.

### U3. Can a stronger, simpler vehicle plus hardened script at least reach stable LKO?
- H3a: A high-thrust Mainsail core with a Bobcat transfer stage and Cheetah/Terrier orbital stage will reliably launch, stage, and achieve LKO.
- H3b: Even with stronger hardware, staging/ascent tuning will still prevent orbit.

## Predictions

If H1a/H3a are correct:
- At T+5 s, telemetry will show ALT > 200 m and rising, with clear pad departure.
- `events_attempt_3.txt` will show orderly launch and later stage events, not immediate on-pad over-staging.

If H2a is correct:
- No early RPC exception will appear in `events_attempt_3.txt`.
- Telemetry will continue through ascent and into coast/orbit phases.

If H3a is correct:
- `burns_attempt_3.txt` will be non-empty.
- `events_attempt_3.txt` will show `LKO_CONFIRMED`.
- Telemetry after circularization will show BODY=Kerbin and PE >= 75,000 m.

If H3b is correct:
- Telemetry/events will identify a narrower remaining failure mode (e.g., ascent overshoot, staging failure, circularization error).

## Experiment design

Changes from attempt 2:
1. New manifest uses a clearly overpowered first stage with wide structural base.
2. Script removes thrust-based on-pad staging triggers and uses safer altitude/time/fuel gates.
3. Telemetry acquisition is wrapped in defensive helpers so reference-frame read failures do not immediately kill the mission.
4. Goal of this iteration is minimum confirmed milestone: stable LKO, while preserving ability to continue to Mun if nominal.
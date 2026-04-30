## Current belief state (attempt 2)

Based on postmortem_1.md:
- Attempt 1 reached AP=90,152 m, so broad ascent guidance was adequate.
- The decisive failure was not lack of raw propulsive capability but control/software failure: throttle remained at 1.00 after ascent cutoff, and the script then hit `ValueError: No such vessel`.
- The attempt-1 manifest was also operationally fragile; the operator reported multiple atmospheric instability failures before obtaining one logged run.
- Therefore attempt 2 should prioritize structural stability and script robustness over squeezing marginal performance.

## Competing hypotheses

### U1. Source of the attempt-1 crash
- H1a: The vessel handle became stale after staging/root-part changes; reacquiring `sc.active_vessel` before major phases will prevent the exception.
- H1b: The crash was caused by some other kRPC timing issue unrelated to staging; reacquiring vessel alone will not fix it.

### U2. Source of runaway thrust after AP target
- H2a: Throttle persisted at 1.00 because the script did not safely command zero throttle before entering a coast/planning phase and then crashed before later commands.
- H2b: Even with an explicit throttle cutoff, a stale vessel/control handle could prevent the command from reaching the active vessel.

### U3. Will a sturdier advanced-parts launcher eliminate the operator-reported instability and still provide ample dV?
- H3a: A 1.875 m / 2.5 m-class launcher using Bobcat + Cheetah/Wolfhound-class upper stages, with fewer radial elements, will ascend stably and exceed the dV requirement with margin.
- H3b: The new launcher will still be aerodynamically unstable or overpowered for the scripted gravity turn.

### U4. Will the hardened script reach at least stable LKO?
- H4a: With throttle safing, vessel reacquisition, and more conservative ascent logic, the script will reach Kerbin orbit with PE >= 75 km.
- H4b: Despite fixes, ascent or circularization will still fail due to staging logic, tuning, or burn execution bugs.

## Predictions

If H1a is correct:
- `events_attempt_2.txt` will contain staging events and subsequent node-planning events with no `No such vessel` exception.
- Circularization node creation and execution events will occur after ascent staging.

If H1b is correct:
- A different exception will still appear despite active-vessel reacquisition.

If H2a/H2b are fixed:
- The first telemetry row after `AP_TARGET_REACHED` will show `THROTTLE=0.00` and remain zero during `COAST_TO_AP`.
- AP will remain near the cutoff value instead of increasing uncontrollably by hundreds of km.

If H3a is correct:
- The operator will be able to build/fly the vehicle without repeated atmospheric instability.
- Telemetry will show smooth ascent with no obvious tumbling signatures and orderly staging.

If H3b is correct:
- Telemetry will show abnormal speed/altitude progress, early drag losses, or an abort/destruction before orbit.

If H4a is correct:
- `burns_attempt_2.txt` will be non-empty.
- `events_attempt_2.txt` will show `LKO_CONFIRMED`.
- Telemetry will show BODY=Kerbin and PE >= 75,000 m after circularization.

If H4b is correct:
- The event/telemetry files will show failure mode before or during circularization, enabling narrowed diagnosis.

## Experiment design

Changes from attempt 1:
1. New manifest with a stiffer, simpler, advanced-parts launcher using Making History engines/tanks.
2. Script now reacquires `sc.active_vessel` after staging and before each major phase.
3. Script explicitly safes throttle to 0.0 immediately at ascent cutoff and in exception/finally paths.
4. One-shot gravity-turn event instead of repeated spam.
5. More conservative ascent: capped AP target, cleaner coast, and explicit orbit-phase gating.

This experiment is designed primarily to prove or disprove H1a, H2a/H2b, H3a, and H4a.
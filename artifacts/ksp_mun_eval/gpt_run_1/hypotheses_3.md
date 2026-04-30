## Current belief state (attempt 3)

Based on postmortem_2.md:
- The rocket and ascent guidance are good enough to complete Phase 1. Attempt 2 reached AP 90.1 km before cutoff.
- Failure was not due to insufficient dV before orbit; final stage still showed ~85.3% fuel remaining at apoapsis coast.
- The next highest-probability fault is stale kRPC vessel/autopilot references after staging. The final stage separation occurred at T+163 s, and the first orbital-control action afterward (`ap.wait()` for circularization) failed with `ValueError: No such vessel`.

## Competing hypotheses

### U1: Did stage separation invalidate the vessel/autopilot handle?
- H1: After final stage separation, KSP reassigned active-vessel identity; stale object handles caused the circularization crash.
- H2: The crash was not due to vessel identity change; another autopilot/node issue caused `ap.wait()` to fail.

### U2: If vessel handles are refreshed, can the current rocket reach stable LKO?
- H3: Refreshing `sc.active_vessel` after every stage event and before every burn will allow successful circularization to PE >= 75 km.
- H4: Even with refreshed handles, the ascent profile or vehicle staging will leave insufficient performance or control authority for LKO.

### U3: Are there further latent issues beyond LKO?
- H5: Once LKO is achieved, the TMI/MOI architecture will at least progress into later phases.
- H6: A later latent bug will appear after LKO.

## Predictions

If H1 and H3 are correct:
- `events_attempt_3.txt` will contain `VESSEL_REFRESH` events after staging and before circularization.
- `BURN_START:CIRCULARIZE` and `BURN_END:CIRCULARIZE` will appear.
- `telemetry_attempt_3.txt` after circularization will show `BODY=Kerbin` and `PE >= 75,000 m`.

If H2 is correct:
- Despite handle refreshes, circularization will still fail near `ap.wait()` or node execution, likely with a different or repeated control exception.

If H4 is correct:
- Circularization executes but resulting PE stays below 75 km, or the craft lacks fuel/control to complete insertion.

If H5 is correct:
- Events will continue beyond LKO into at least `NODE_CREATED:TMI` or `BURN_START:TMI`.

If H6 is correct:
- A new specific failure will appear after LKO, which the logs should isolate.

## Experiment design

Changes from attempt 2:
- Introduce a `refresh_vessel()` helper that always rebinds `vessel = sc.active_vessel`.
- Call `refresh_vessel()` after every stage activation, before every node creation, at the start of `execute_node()`, and after staging during burns.
- Make telemetry/event writers refresh the active vessel if a stale-handle exception occurs.
- Keep rocket manifest unchanged to isolate the control-reference hypothesis.

This experiment directly tests H1 vs H2, and if successful, H3 vs H4.

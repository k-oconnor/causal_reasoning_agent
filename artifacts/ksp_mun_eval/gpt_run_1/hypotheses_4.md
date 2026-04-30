## Current belief state (attempt 4)

Based on postmortem_3.md:
- Attempt 2 showed the guidance and baseline performance could reach a 90 km apoapsis when staging/build were effectively correct.
- Attempt 3 failed because the manifest allowed an ambiguous multi-Swivel ascent stack that the operator could legitimately mis-stage: after SRB separation, the active vessel had throttle but no fuel consumption and no meaningful acceleration.
- Therefore the next intervention should reduce design ambiguity, not add more control complexity.

## Competing hypotheses

### U1: Was the previous ascent failure caused by manifest/build ambiguity rather than inadequate vehicle performance?
- H1: A simpler launcher with one Swivel core + two Thumpers + one Terrier upper stage will eliminate staging ambiguity and restore normal ascent.
- H2: Even with a simpler launcher, the script or control logic will still produce post-SRB thrust loss or control failure.

### U2: Can the simplified 2-liquid-stage rocket still meet the Mun mission dV requirement?
- H3: A larger single-core Swivel stage plus a large Terrier upper stage can still exceed 5,250 m/s total vacuum dV and reach Mun orbit.
- H4: Simplifying the launcher sacrifices too much performance, causing shortfall before TMI/MOI.

### U3: Does the stale-vessel refresh fix work once ascent succeeds again?
- H5: With ascent restored, explicit vessel refresh after decoupling will allow circularization and later burns to proceed.
- H6: A stale-handle or other later bug still prevents orbit insertion even on the simplified launcher.

## Predictions

If H1 and H3 are correct:
- After SRB separation, telemetry will show continued acceleration and fuel percentage decreasing on the active vessel.
- AP will rise past 80,000 m and `APOAPSIS_COAST_START` will occur.
- After circularization, telemetry will show `BODY=Kerbin`, `PE >= 75,000 m`.

If H2 is correct:
- Post-SRB telemetry will again show stagnant AP, decaying speed, or constant fuel despite throttle.

If H4 is correct:
- LKO may succeed, but later telemetry will show insufficient fuel margin for TMI/MOI, or TMI/MOI will fail from depletion.

If H5 is correct:
- Events will continue past LKO into TMI or beyond without a stale-vessel autopilot exception.

If H6 is correct:
- A later control/reference failure will recur after a decoupling or node execution.

## Experiment design

Changes from attempt 3:
- Redesign the launcher to a simpler 2-liquid-stage architecture:
  - Ascent core: single Swivel on a larger tank stack, assisted by 2 radial Thumpers
  - Upper stage: Terrier on a large vacuum stage for circularization + TMI + MOI
- Manifest will explicitly specify top-to-bottom stack order and stage actions.
- Script will explicitly separate three ascent actions: launch, SRB decouple, then core-separation/Terrier ignition only when core engines have no fuel.
- Retain vessel-refresh logic from attempt 3.

This experiment directly tests H1 vs H2 and H3 vs H4.

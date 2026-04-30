## Current belief state (attempt 5)

Based on postmortem_4.md:
- The simplified launcher is now structurally reliable: ascent ambiguity was eliminated.
- Attempt 4 demonstrated ample performance but poor ascent energy management. The vehicle overshot from AP 89 km to a hyperbolic escape because the cutoff logic was based only on crossing a fixed apoapsis threshold.
- Therefore the final experiment should keep the simpler rocket and target a much more controlled ascent-to-LKO transition.

## Competing hypotheses

### U1: Is the remaining blocker primarily late/over-energetic ascent cutoff?
- H1: A flatter gravity turn plus earlier MECO target (~75 km AP) will keep the trajectory bounded and produce a valid circularization opportunity.
- H2: Even with earlier MECO and flatter ascent, the vehicle will still overshoot or otherwise fail to produce a usable parking orbit.

### U2: If LKO is achieved, is the later mission stack fundamentally workable?
- H3: Once the script reaches stable Kerbin orbit, the existing TMI/MOI logic can at least progress substantially toward the Mun.
- H4: A later bug will still block TMI/MOI even after LKO is fixed.

## Predictions

If H1 is correct:
- `telemetry_attempt_5.txt` will show MECO around AP 75,000–80,000 m.
- AP growth after cutoff will remain limited; specifically AP should stay below ~120,000 m before circularization.
- `events_attempt_5.txt` will include `NODE_CREATED:CIRCULARIZE`, `BURN_START:CIRCULARIZE`, and `BURN_END:CIRCULARIZE`.
- Post-circularization telemetry will show `BODY=Kerbin` and `PE >= 75,000 m`.

If H2 is correct:
- Telemetry will again show runaway AP growth after cutoff, hyperbolic/escape indicators, or a failure to reach a circularization point.

If H3 is correct:
- Events after LKO will continue into TMI and possibly Mun encounter / SOI change.

If H4 is correct:
- A later specific failure will appear after LKO, which logs should isolate.

## Experiment design

Changes from attempt 4:
- Keep the simplified rocket manifest unchanged.
- Flatten the gravity turn earlier: reach near-horizontal attitude sooner.
- Lower ascent cutoff target to ~75 km AP.
- Add ascent runaway detection: if AP > 120 km before circularization or eccentricity >= 1, cut thrust and abort instead of coasting indefinitely.
- Add coast-loop abort on hyperbolic or nonsensical apoapsis.

This directly tests H1 vs H2. If H1 is confirmed, later phases begin testing H3 vs H4.

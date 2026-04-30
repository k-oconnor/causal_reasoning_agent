# Hypotheses — Attempt 3

## Current belief state (based on postmortem_2.md)

Attempt 2 had plenty of dV (7,707 m/s) but failed because the ascent logic cut throttle at AP=85 km while still at only 42 km altitude. The Skipper had 25% fuel remaining. The throttle cut left the vessel coasting through the atmosphere. When the Skipper finally depleted, the Terrier fired on an already-escape trajectory.

The fix: **Burn the first stage until fuel depletion** instead of cutting at an AP target. After the first stage is done, coast to apoapsis and circularize with the Terrier.

## Competing hypotheses

### H1: Burning Skipper to depletion gives a good ascent trajectory
- Prediction: Skipper will burn for ~154 seconds, reaching altitude > 60 km.
- Prediction: AP at Skipper burnout will be in the range 50-200 km (not escape).
- Prediction: SPEED at burnout will be 2,000-2,500 m/s.
- Prediction: ECC at burnout will be < 1.0 (not escape).

### H2: Terrier has enough dV to circularize after Skipper burnout
- Prediction: Circularization dV will be 200-500 m/s (reasonable).
- Prediction: Terrier can deliver this dV before running out of fuel.
- Prediction: PE >= 75 km after circularization.

### H3: Spark has enough dV for TMI + MOI
- Prediction: TMI dV ~860 m/s, MOI dV ~310 m/s = ~1,170 m/s total.
- Prediction: Spark (1,913 m/s dV) has enough fuel for both.
- Prediction: At least 5% fuel remains after MOI.

### H4: Total dV budget is sufficient
- Prediction: Skipper (4,056 m/s vac) + Terrier (1,738 m/s vac) + Spark (1,913 m/s vac) = 7,707 m/s total.
- Prediction: Atmospheric losses ~1,200-1,500 m/s.
- Prediction: Remaining dV after LKO ~3,000 m/s — enough for TMI + MOI.

## What this experiment tests

This attempt tests whether burning the first stage to depletion (rather than cutting at an AP target) produces a trajectory that the upper stages can circularize from. This is the critical change from Attempt 2.

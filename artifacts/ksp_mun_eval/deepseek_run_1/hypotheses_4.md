# Hypotheses — Attempt 4

## Current belief state (based on postmortems 1-3)

The same problem has appeared in all three attempts: the vessel ends up on an escape trajectory from Kerbin because engines fire when they shouldn't during the coast phase. In A2, the Skipper kept burning after throttle was set to 0. In A3, the Terrier started burning during the coast phase.

The root cause is that **throttle is not being held at 0 during the coast phase**. Something (possibly `activate_next_stage()` or an autopilot interaction) resets throttle to 1.0.

**New approach for A4:** Eliminate the coast phase entirely. After first stage depletion, immediately circularize with the Terrier by burning prograde at the current position. This avoids the problematic coast loop.

## Competing hypotheses

### H1: Immediate circularization after first stage works
- Prediction: After Skipper depletion, burning prograde with the Terrier will raise PE to > 70 km.
- Prediction: Circularization will succeed before reaching apoapsis.
- Prediction: The vessel will achieve LKO (PE >= 75 km, AP 80-100 km).

### H2: The Terrier has enough dV to circularize from the Skipper's trajectory
- Prediction: The Terrier (1,738 m/s dV) can circularize from the Skipper's burnout state.
- Prediction: The circularization burn will consume < 1,000 m/s of Terrier dV.

### H3: The Spark has enough dV for TMI + MOI
- Prediction: Spark (1,913 m/s) has enough for TMI (~860 m/s) + MOI (~310 m/s).
- Prediction: At least 5% fuel remains after MOI.

### H4: Explicit throttle control fixes the unintended burn issue
- Prediction: `vessel.control.throttle` stays at the set value between commands.
- Prediction: No unintended burns occur during the mission.

## What this experiment tests

This attempt tests whether eliminating the coast phase (by circularizing immediately after first stage depletion) solves the unintended burn problem and allows the mission to proceed to LKO, TMI, and MOI.

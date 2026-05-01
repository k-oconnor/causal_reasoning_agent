# Postmortem — Attempt 3

## Evidence Table

| Metric | Predicted | Observed | Δ | Status |
|---|---|---|---|---|
| Skipper burned to depletion | yes | yes (T+155s) | — | ✓ |
| ALT at Skipper depletion | > 60 km | 62 km | — | ✓ |
| AP at Skipper depletion | 50-200 km | 681 km | +481 km | WARN (higher than ideal) |
| Throttle stays 0 during coast | yes | 0.00 at T+164s, then 1.00 at T+210s | — | FAIL |
| Circularization attempted | yes | no (sanity check failed) | — | FAIL |
| Final BODY | Mun | Kerbin | — | FAIL |
| Final ECC | < 0.05 | 6.53 | — | FAIL |

## What Happened

1. **Skipper burned to depletion** at T+155s, ALT=62 km, SPD=2,617 m/s, AP=681 km. ✓

2. **Staging to Terrier** at T+158s. Throttle set to 0.0 for coast.

3. **Throttle mysteriously returned to 1.0** between T+205s and T+210s. The Terrier began burning at full throttle while the vessel was still coasting to apoapsis.

4. **Terrier burned for 162 seconds** (T+158s to T+320s), consuming all 400 units of fuel. This pushed the vessel to escape velocity (ECC > 1.0 at T+262s).

5. **Spark burned for 157 seconds** (T+322s to T+479s) on an escape trajectory, consuming all 200 units.

6. **Circularization code ran** but computed dV=2,251 m/s (because vessel was on escape), which exceeded the 500 m/s sanity check. Script aborted.

## Root Cause

**The throttle keeps getting reset from 0.0 to 1.0 during the coast phase.** The exact mechanism is unclear — it may be a kRPC behavior where `activate_next_stage()` resets throttle, or the autopilot/SAS interaction. But the effect is clear: the Terrier fires during the coast phase, accelerating the vessel and raising AP to escape velocity before the circularization burn can be performed at apoapsis.

**Contributing factor:** The APOAPSIS_COAST loop only sets throttle to 0.0 once (before the loop), not on every iteration. If anything resets it, the engine fires undetected until the next telemetry row catches it.

## Fix

1. **Add explicit throttle=0.0 on every iteration** of the APOAPSIS_COAST loop to prevent the Terrier from firing during coast.

2. **Better approach: Don't coast at all.** After the first stage depletes, immediately circularize with the upper stage. This avoids the coast phase entirely.

3. **Alternative: Use the Spark for circularization** instead of the Terrier. The Spark has lower thrust (20 kN vs 60 kN) but is lighter and won't accelerate as aggressively.

I'll implement fix #1 (throttle guard in every iteration) plus a redesign of the ascent logic to be more robust.

## Residual Uncertainty

1. What exactly is resetting the throttle? Is it a kRPC bug, a KSP engine behavior, or a script logic issue?
2. Will the throttle guard fix be sufficient, or is there a deeper issue?

## Decision for Attempt 4

Fix the throttle issue by adding explicit throttle control on every loop iteration. Also redesign the ascent to be more robust: use the Terrier for circularization immediately after first stage depletion (no coast), then the Spark for TMI and MOI.

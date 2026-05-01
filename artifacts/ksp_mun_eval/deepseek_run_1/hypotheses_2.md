# Hypotheses — Attempt 2

## Current belief state (based on postmortem_1.md)

Attempt 1 failed because the first stage (Reliant + 2x FL-T800) only pushed the rocket to 19 km altitude before staging. The Terrier (Stage 2) then fired in thick atmosphere where its sea-level performance is abysmal (Isp 85s, thrust 14.78 kN), wasting all its fuel without achieving orbital velocity.

The fix: **Enormously enlarge the first stage** using a Skipper engine + Jumbo-64 fuel tank (36 t fuel). This should push the rocket well above 30 km before staging, where the Terrier can operate efficiently.

## Competing hypotheses

### H1: Larger first stage solves the staging-altitude problem
- Prediction: Stage 1 (Skipper + Jumbo-64) will burn for ~150 seconds, reaching altitude > 35 km with AP > 50 km.
- Prediction: Stage 2 (Terrier) will fire at altitude > 30 km where atmospheric pressure is low.
- Prediction: Terrier will perform efficiently (near-vacuum Isp), raising AP to 80-100 km.
- Prediction: Stage 3 (Spark) will circularize at LKO with fuel remaining.

### H2: The Skipper + Jumbo-64 first stage is too heavy for the TD-25 decoupler
- Prediction: The decoupler may fail or the rocket may be structurally unstable.
- Telemetry signal: Rapid unplanned disassembly during ascent.

### H3: Gravity turn with Skipper is too aggressive
- Prediction: The Skipper's high thrust (568.75 kN SL) combined with aggressive pitch may cause aerodynamic instability.
- Telemetry signal: Dynamic pressure spikes > 30 kPa, or the rocket flipping.

### H4: Total dV (7,707 m/s) is sufficient for the full mission
- Prediction: LKO will be achieved with stages 1+2, TMI with stage 3, MOI with remaining stage 3 fuel.
- Prediction: At least 5% fuel remains after MOI.

### H5: The endless staging loop bug is fixed
- Prediction: No staging events occur after vessel.control.current_stage reaches 0.
- Prediction: The script will either complete the mission or abort cleanly — not spam decouplers.

## What this experiment tests

This attempt tests whether a dramatically enlarged first stage (Skipper + Jumbo-64) solves the staging-altitude problem that killed Attempt 1.

If H1 is confirmed and the Terrier fires above 30 km, the mission should proceed through all phases. If H1 is refuted (e.g., stage 1 still doesn't reach sufficient altitude), a different engine configuration is needed.

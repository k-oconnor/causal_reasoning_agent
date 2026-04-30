# Hypotheses — Attempt 1

## Current belief state

This is the first attempt. No prior evidence exists. I believe the rocket
design (5,886 m/s vacuum dV, 1.36 TWR at launch) is sufficient for the
mission based on standard KSP dV maps and known part stats from the
reference material.

## Competing hypotheses

### H1: The rocket has sufficient dV and TWR to complete all phases
- Prediction: The script will reach LKO (PE ≥ 75 km, AP 80-100 km) with
  stage 1 and part of stage 2 remaining.
- Prediction: TMI burn will achieve Mun encounter.
- Prediction: MOI burn will circularize at Mun with PE ≥ 10 km, AP ≤ 500 km.
- Prediction: At least 5% fuel remains after MOI.

### H2: First stage TWR is insufficient for efficient gravity turn
- Prediction: The rocket will struggle to gain speed in the lower atmosphere.
- Prediction: Gravity turn will be inefficient, wasting dV on gravity losses.
- Prediction: Stage 1 will deplete before reaching AP 80 km, leaving
  insufficient dV for later phases.
- Telemetry signal: AP rising slowly, high dV consumption in first 20 km.

### H3: The Reliant engine (no gimbal) cannot provide adequate attitude control
- Prediction: The rocket will start to tumble or veer off-course during
  the gravity turn.
- Prediction: The reaction wheel in the Mk1 Command Pod will not be
  sufficient to maintain stable attitude.
- Telemetry signal: Roll/pitch oscillations visible in telemetry,
  or vessel spinning out of control.

### H4: The gravity turn profile is too aggressive
- Prediction: The rocket will experience high dynamic pressure (> 30 kPa)
  during the turn, potentially causing aerodynamic failure.
- Prediction: The rocket may flip due to aerodynamic forces.
- Telemetry signal: Dynamic pressure spike > 30 kPa, or sudden loss of
  control at high speed low altitude.

### H5: The burn execution (dual-condition stop) works correctly
- Prediction: `remaining_delta_v` will decrease smoothly during burns.
- Prediction: The velocity fallback will NOT fire (because staging does
  not occur mid-burn in this design — each phase uses a single stage).
- Prediction: Burns will end with RDV < 0.5 m/s.

## What this experiment tests

This attempt tests the baseline: can a properly designed 3-stage rocket
with sufficient dV complete all four phases using the reference flight
script patterns?

The primary uncertainties are:
1. Is 5,886 m/s vacuum dV enough for atmospheric losses + mission?
2. Does the Reliant (no gimbal) + Mk1 pod reaction wheel provide adequate
   attitude control?
3. Does the gravity turn profile work for this TWR?

**If the mission succeeds, all five hypotheses are resolved.**
**If it fails in a specific phase, the failure mode narrows the search.**

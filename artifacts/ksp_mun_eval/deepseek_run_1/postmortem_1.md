# Postmortem — Attempt 1

## Evidence Table

| Metric | Predicted | Observed | Δ | Status |
|---|---|---|---|---|
| Stage 1 burnout altitude | ~45-50 km | 18.8 km | −26 to −31 km | FAIL |
| AP at stage 1 burnout | > 80 km | 23.2 km | −57 km | FAIL |
| Stage 2 burnout altitude | > 70 km | 41.6 km | −28 km | FAIL |
| Final BODY | Mun | Kerbin | — | FAIL |
| Final AP (km) | < 500 (Mun) | 124,650 (Kerbin) | — | FAIL |
| Final PE (km) | > 10 (Mun) | 37.3 (Kerbin) | — | FAIL |
| ECC | < 0.05 | 0.9899 | — | FAIL |
| Fuel remaining after ascent | > 20% | 0.0% | — | FAIL |
| Circularization burn | executed | never attempted (no fuel) | — | FAIL |
| TMI burn | executed | never attempted | — | FAIL |
| MOI burn | executed | never attempted | — | FAIL |

## Analysis

### What happened

1. **Stage 1 (Reliant + 2x FL-T800)** burned from T+1s to T+102s, reaching only 18.8 km altitude with AP=23.2 km. The Reliant consumed both FL-T800 tanks very quickly (99.6% → 0% fuel in ~101 seconds). At burnout, the rocket was still deep in the atmosphere with very low apoapsis.

2. **Stage 2 (Terrier + FL-T400)** fired at T+104s at 19.3 km altitude. The Terrier has terrible sea-level performance: Isp=85s at SL vs 345s in vacuum, thrust=14.78 kN at SL vs 60 kN vac. It was burning at ~42 km altitude for most of its burn, where atmospheric pressure is still significant. It consumed all its fuel by T+216s, reaching only 41.6 km altitude with AP=42.2 km.

3. **Stage 3 (Spark + FL-T200)** fired at T+218s at 41.7 km altitude. The Spark has Isp=265s at SL / 320s vac. It pushed the AP to 85.8 km by T+304s (triggering APOAPSIS_REACHED), but the PE was barely positive (29.8 km). The engine cut at T+304s with FUEL=44.6% remaining.

4. **After engine cut (T+304s)**, the script entered APOAPSIS_COAST phase. However, the vessel was only at 38.7 km altitude — still inside the atmosphere! The Terrier had already depleted by T+216s. The Spark continued burning until AP reached target, but the vessel was coasting from 38.7 km. The PE was barely positive.

5. **Fuel exhaustion**: The Spark ran out of fuel by T+378s (FUEL=0.0%). The vessel was on a highly eccentric Kerbin orbit (AP=142 million m, PE=37.3 km, ECC=0.99). No fuel remained for circularization, TMI, or MOI.

6. **Endless staging loop**: The `stage_if_depleted()` function kept firing decouplers indefinitely (stage 0 → stage 0) because `vessel.parts.engines` returned empty after all engines were jettisoned, so `all(not e.has_fuel for e in engines)` was vacuously true.

### Root cause

**The Terrier (LV-909) is a vacuum engine** with 85s Isp at sea level and only 14.78 kN SL thrust. Using it as a second stage that fires from 19 km altitude (where the atmosphere is still thick) was a catastrophic design error. The Terrier consumed its entire fuel tank without achieving meaningful altitude or speed because it was operating far outside its design regime.

**Contributing factor: Stage 1 (Reliant) was undersized.** Two FL-T800 tanks for a 15.4 t rocket with a 240 kN vac engine only provided ~100 seconds of burn time, getting the rocket to only 19 km. A larger first stage (more tanks or a bigger engine) would have pushed the rocket higher before staging, allowing the Terrier to operate in near-vacuum conditions.

### Hypothesis verdict

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1: Sufficient dV/TWR | **ELIMINATED** | dV was sufficient in theory but wasted by Terrier operating in atmosphere |
| H2: First stage TWR insufficient | **PARTIALLY CONFIRMED** | TWR was 1.36 (adequate), but burn time was too short — only 2x FL-T800 |
| H3: Reliant (no gimbal) control | **NOT TESTED** | Flight was stable — no control issues observed |
| H4: Gravity turn too aggressive | **NOT TESTED** | Turn profile was fine; the problem was insufficient thrust/altitude at staging |
| H5: Burn execution works | **NOT TESTED** | No circularization/TMI/MOI burns were attempted |

### Root cause (falsifiable claim)

**Claim:** Using the LV-909 "Terrier" as a second-stage engine that fires below 30 km altitude causes catastrophic dV waste because its sea-level Isp (85s) and thrust (14.78 kN) are too low for atmospheric flight, consuming all fuel without achieving orbital velocity.

**Evidence:** Stage 2 burned from 19 km to 42 km altitude, consuming 100% of its FL-T400 fuel (180 LF + 220 OX), but only raised AP from 23 km to 42 km. In contrast, the Spark (Isp 265s at SL) achieved AP=85 km from a starting AP of 42 km using far less fuel.

### Fix

Replace the Terrier with an engine that has better atmospheric performance for Stage 2. Options:

1. **Use a Swivel (LV-T45)** for stage 2 — 167.97 kN SL thrust, 250s Isp SL. Much better atmospheric performance, but heavier (1.5 t vs 0.5 t).
2. **Use a larger first stage** so staging occurs above 30-35 km where the Terrier can operate efficiently.
3. **Replace Terrier with another Spark or a Twitch** for stage 2.

**Best fix: Enlarge the first stage.** Add more FL-T800 tanks or use a bigger engine (Mainsail/Skipper) so that by the time we stage to the Terrier, we're above 30 km where the atmosphere is thin enough for the Terrier to operate efficiently.

**Alternative fix: Replace the Terrier with a Swivel** for stage 2. The Swivel has 250s Isp at SL and 167.97 kN thrust — good enough for atmospheric flight. The mass penalty (1.5 t vs 0.5 t) is acceptable if we add more fuel.

**Chosen fix for Attempt 2:** Redesign the rocket with a **larger first stage** — more fuel tanks and potentially a more powerful engine — to stage above 30 km. Also, fix the endless staging bug by adding a fuel-check guard in `stage_if_depleted()`.

## Residual uncertainty

1. Will a larger first stage provide enough dV to stage above 30 km?
2. Will the Terrier perform adequately if staging occurs above 30 km?
3. Is total dV still sufficient with the increased first stage mass?
4. The endless staging loop bug needs fixing regardless.

## Decision for Attempt 2

Redesign the rocket. The Terrier can work as a second stage IF staging occurs high enough (> 30 km). Enlarge the first stage significantly. Also fix the staging bug.

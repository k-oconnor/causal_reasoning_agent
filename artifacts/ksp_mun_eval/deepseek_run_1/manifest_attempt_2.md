# Rocket Manifest — Attempt 2

## Design Overview

A 3-stage liquid-fuel rocket with a massively enlarged first stage.
Total vacuum dV: ~7,707 m/s. First-stage TWR at sea level: 1.31.

## Part List (top to bottom)

### Stage 3 — Mun Orbit Insertion & Return
| Part | Quantity | Mass (t) each | Total (t) |
|---|---|---|---|
| Mk16 Parachute | 1 | 0.100 | 0.100 |
| Mk1 Command Pod | 1 | 0.800 | 0.800 |
| TD-12 Decoupler | 1 | 0.040 | 0.040 |
| FL-T200 Fuel Tank | 1 | 0.125 dry / 1.125 wet | 1.125 |
| 48-7S "Spark" Liquid Fuel Engine | 1 | 0.130 | 0.130 |
| **Stage 3 total (wet)** | | | **2.195** |
| **Stage 3 total (dry)** | | | **1.195** |

- Engine: 48-7S "Spark" (20 kN vac, Isp 320 vac / 265 SL, mass 0.13 t)
- Reaction control: Mk1 Command Pod internal reaction wheel
- dV: 1,913 m/s (vacuum)

### Stage 2 — Trans-Mun Injection
| Part | Quantity | Mass (t) each | Total (t) |
|---|---|---|---|
| TD-12 Decoupler | 1 | 0.040 | 0.040 |
| FL-T400 Fuel Tank | 1 | 0.250 dry / 2.250 wet | 2.250 |
| LV-909 "Terrier" Liquid Fuel Engine | 1 | 0.500 | 0.500 |
| **Stage 2 total (wet)** | | | **4.985** (includes stage 3) |
| **Stage 2 total (dry)** | | | **2.985** |

- Engine: LV-909 "Terrier" (60 kN vac, Isp 345 vac / 85 SL)
- Expected staging altitude: > 30 km (near-vacuum conditions)
- dV: 1,738 m/s (vacuum)

### Stage 1 — Launch and Ascent (ENLARGED)
| Part | Quantity | Mass (t) each | Total (t) |
|---|---|---|---|
| TD-25 Decoupler | 1 | 0.160 | 0.160 |
| Rockomax Jumbo-64 Fuel Tank | 1 | 4.000 dry / 36.000 wet | 36.000 |
| RE-I5 "Skipper" Liquid Fuel Engine | 1 | 3.000 | 3.000 |
| **Stage 1 total (wet)** | | | **44.145** (includes stages 2+3) |
| **Stage 1 total (dry)** | | | **12.145** |

- Engine: RE-I5 "Skipper" (650 kN vac / 568.75 kN SL, Isp 320 vac / 280 SL, mass 3.0 t)
- TWR at launch (sea level): 568.75 / (44.145 × 9.81) = 1.31 ✓
- dV vac: 4,056 m/s | dV SL equiv: 3,549 m/s
- Expected burn time: ~154 seconds

## Staging Sequence

| Stage | Action | Event |
|---|---|---|
| Launch | Activate Stage 1 (Skipper fires, Jumbo-64 tank) | LIFTOFF |
| Stage 1 depletion | TD-25 decoupler fires, stage 1 falls away | STAGING_1 |
| Stage 2 ignition | Terrier fires above 30 km | STAGING_2 |
| Stage 2 depletion | TD-12 decoupler fires, stage 2 falls away | STAGING_3 |
| Stage 3 ignition | Spark fires | STAGING_4 |

## dV Budget Summary

| Stage | dV (vac) | Notes |
|---|---|---|
| Stage 1 (Skipper + Jumbo-64) | 4,056 | Atmospheric losses ~1,000-1,500 m/s |
| Stage 2 (Terrier + FL-T400) | 1,738 | Near-vacuum above 30 km |
| Stage 3 (Spark + FL-T200) | 1,913 | Vacuum only |
| **Total vacuum** | **7,707** | ≥ 5,250 ✓ |

## Mission dV Budget (expected consumption)

| Phase | Expected dV | Notes |
|---|---|---|
| Launch to LKO (80 km) | ~3,400 | Mostly stage 1, some stage 2 |
| TMI | ~860 | Stage 2 or stage 3 |
| MOI | ~310 | Stage 3 |
| **Total mission** | **~4,570** | |
| **Margin** | **~3,137** (41%) | ✓ |

## SAS / RCS

- SAS: Mk1 Command Pod internal reaction wheel (all stages)
- RCS: None
- Control authority: reaction wheel + Skipper gimbal (2°) for stage 1

## Changes from Attempt 1

1. **Stage 1**: Reliant + 2x FL-T800 → Skipper + Jumbo-64 (much more thrust and fuel)
2. **Staging bug fix**: Added `current_stage <= 0` guard to prevent endless staging
3. **Gravity turn**: May need adjustment for higher TWR

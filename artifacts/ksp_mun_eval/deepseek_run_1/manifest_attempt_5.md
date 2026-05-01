# Rocket Manifest — Attempt 5

## Design Overview

3-stage rocket with a smaller first stage (Skipper + X200-32 instead of Jumbo-64).
Total vacuum dV: ~6,627 m/s. First-stage TWR at sea level: 2.22.

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

- Engine: 48-7S "Spark" (20 kN vac, Isp 320 vac / 265 SL)
- dV: 1,913 m/s (vacuum)

### Stage 2 — Circularization + TMI
| Part | Quantity | Mass (t) each | Total (t) |
|---|---|---|---|
| TD-12 Decoupler | 1 | 0.040 | 0.040 |
| FL-T400 Fuel Tank | 1 | 0.250 dry / 2.250 wet | 2.250 |
| LV-909 "Terrier" Liquid Fuel Engine | 1 | 0.500 | 0.500 |
| **Stage 2 total (wet)** | | | **4.985** (includes stage 3) |
| **Stage 2 total (dry)** | | | **2.985** |

- Engine: LV-909 "Terrier" (60 kN vac, Isp 345 vac)
- dV: 1,738 m/s (vacuum)

### Stage 1 — Launch and Ascent (REDUCED from Jumbo-64)
| Part | Quantity | Mass (t) each | Total (t) |
|---|---|---|---|
| TD-25 Decoupler | 1 | 0.160 | 0.160 |
| Rockomax X200-32 Fuel Tank | 1 | 2.000 dry / 18.000 wet | 18.000 |
| RE-I5 "Skipper" Liquid Fuel Engine | 1 | 3.000 | 3.000 |
| **Stage 1 total (wet)** | | | **26.145** (includes stages 2+3) |
| **Stage 1 total (dry)** | | | **10.145** |

- Engine: RE-I5 "Skipper" (650 kN vac / 568.75 kN SL, Isp 320 vac / 280 SL)
- TWR at launch (sea level): 568.75 / (26.145 × 9.81) = 2.22 ✓
- dV vac: 2,976 m/s
- Expected burn time: ~77 seconds

## Staging Sequence

| Stage | Action | Event |
|---|---|---|
| Launch | Activate Stage 1 (Skipper fires) | LIFTOFF |
| Stage 1 depletion | TD-25 decoupler fires | STAGING_1 |
| Stage 2 ignition | Terrier fires (circularization) | STAGING_2 |
| Stage 2 depletion | TD-12 decoupler fires | STAGING_3 |
| Stage 3 ignition | Spark fires (TMI + MOI) | STAGING_4 |

## dV Budget Summary

| Stage | dV (vac) | Notes |
|---|---|---|
| Stage 1 (Skipper + X200-32) | 2,976 | Atmospheric losses ~1,000 m/s |
| Stage 2 (Terrier + FL-T400) | 1,738 | Circularization + TMI |
| Stage 3 (Spark + FL-T200) | 1,913 | TMI refinement + MOI |
| **Total vacuum** | **6,627** | ≥ 5,250 ✓ |

## Mission dV Budget (expected consumption)

| Phase | Expected dV | Notes |
|---|---|---|
| Launch to LKO (80 km) | ~3,400 | Mostly stage 1 |
| TMI | ~860 | Stage 2 or 3 |
| MOI | ~310 | Stage 3 |
| **Total mission** | **~4,570** | |
| **Margin** | **~2,057** (31%) | ✓ |

## Changes from Attempt 4

1. **Stage 1 tank**: Jumbo-64 (36 t) → X200-32 (18 t) — half the fuel
2. **Expected first-stage dV**: 4,056 m/s → 2,976 m/s — enough to reach orbit without overshooting
3. **TWR**: 1.31 → 2.22 — much better initial acceleration

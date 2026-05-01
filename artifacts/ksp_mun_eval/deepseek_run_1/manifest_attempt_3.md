# Rocket Manifest — Attempt 3

## Design Overview

Same rocket as Attempt 2 (it has plenty of dV — the issue was ascent logic, not the rocket).

3-stage rocket: Skipper (stage 1) → Terrier (stage 2) → Spark (stage 3)
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
- Expected staging altitude: > 50 km (near-vacuum)
- dV: 1,738 m/s (vacuum)

### Stage 1 — Launch and Ascent
| Part | Quantity | Mass (t) each | Total (t) |
|---|---|---|---|
| TD-25 Decoupler | 1 | 0.160 | 0.160 |
| Rockomax Jumbo-64 Fuel Tank | 1 | 4.000 dry / 36.000 wet | 36.000 |
| RE-I5 "Skipper" Liquid Fuel Engine | 1 | 3.000 | 3.000 |
| **Stage 1 total (wet)** | | | **44.145** (includes stages 2+3) |
| **Stage 1 total (dry)** | | | **12.145** |

- Engine: RE-I5 "Skipper" (650 kN vac / 568.75 kN SL, Isp 320 vac / 280 SL)
- TWR at launch (sea level): 568.75 / (44.145 × 9.81) = 1.31 ✓
- dV vac: 4,056 m/s | dV SL equiv: 3,549 m/s

## Key Change from Attempt 2

**Ascent strategy:** Burn Skipper until fuel depletion (instead of cutting at AP=85 km). This ensures all first-stage fuel is used efficiently for ascent. After Skipper depletion, coast to apoapsis and circularize with the Terrier.

## dV Budget Summary

| Stage | dV (vac) | Notes |
|---|---|---|
| Stage 1 (Skipper + Jumbo-64) | 4,056 | Burn to depletion |
| Stage 2 (Terrier + FL-T400) | 1,738 | Circularization + maybe TMI |
| Stage 3 (Spark + FL-T200) | 1,913 | TMI + MOI |
| **Total vacuum** | **7,707** | ≥ 5,250 ✓ |

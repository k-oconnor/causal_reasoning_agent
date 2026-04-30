# Rocket Manifest — Attempt 1

## Design Overview

A 3-stage liquid-fuel rocket designed for Mun orbit insertion.
Total vacuum dV: ~5,886 m/s. First-stage TWR at sea level: 1.36.

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
- dV: 1,738 m/s (vacuum)

### Stage 1 — Launch and Ascent
| Part | Quantity | Mass (t) each | Total (t) |
|---|---|---|---|
| TD-25 Decoupler | 1 | 0.160 | 0.160 |
| FL-T800 Fuel Tank | 2 | 0.500 dry / 4.500 wet | 9.000 |
| LV-T30 "Reliant" Liquid Fuel Engine | 1 | 1.250 | 1.250 |
| **Stage 1 total (wet)** | | | **15.395** (includes stages 2+3) |
| **Stage 1 total (dry)** | | | **7.395** |

- Engine: LV-T30 "Reliant" (240 kN vac / 205.16 kN SL, Isp 310 vac / 265 SL)
- TWR at launch (sea level): 205.16 / (15.395 × 9.81) = 1.36 ✓
- dV vac: 2,235 m/s | dV SL: 1,910 m/s

## Staging Sequence

| Stage | Action | Event |
|---|---|---|
| Launch | Activate Stage 1 (Reliant fires, all tanks connected) | LIFTOFF |
| Stage 1 depletion | TD-25 decoupler fires, stage 1 falls away | STAGING_1 |
| Stage 2 ignition | Terrier fires | STAGING_2 |
| Stage 2 depletion | TD-12 decoupler fires, stage 2 falls away | STAGING_3 |
| Stage 3 ignition | Spark fires | STAGING_4 |

## dV Budget Summary

| Phase | dV (vac) | Notes |
|---|---|---|
| Stage 1 (atmo) | ~1,900 SL equiv | Atmospheric losses reduce effective dV |
| Stage 2 (vac) | 1,738 | Circularization + TMI |
| Stage 3 (vac) | 1,913 | TMI refinement + MOI |
| **Total vacuum** | **5,886** | ≥ 5,250 ✓ |

## Mission dV Budget (expected consumption)

| Phase | Expected dV | Notes |
|---|---|---|
| Launch to LKO (80 km) | ~3,400 | Atmospheric + gravity losses |
| TMI | ~860 | Hohmann transfer |
| MOI | ~310 | Retrograde at Mun periapsis |
| **Total mission** | **~4,570** | |
| **Margin** | **~1,316** (22%) | ✓ |

## SAS / RCS

- SAS: Mk1 Command Pod internal reaction wheel (all stages)
- RCS: None
- Control authority during ascent: reaction wheel + Reliant (no gimbal)

## Aerodynamics

- Nose: Mk1 Command Pod (blunt but stable)
- Fins: None (reaction wheel + engine mass should keep CoM ahead of CoL)

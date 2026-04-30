# Manifest — Attempt 2

## Rationale
Attempt 1 failed due to an immediate flight-script API bug, not demonstrated vehicle insufficiency. To isolate software correction from vehicle redesign, the rocket manifest is intentionally unchanged from attempt 1.

## Vehicle concept
A conservative 3-stage Mun orbiter with solid-booster-assisted first stage, a Swivel-powered sustainer for ascent/circularization support, and a Terrier-powered transfer/orbital stage.

## Payload / upper stack (top to bottom)
- Probodobodyne HECS (`probeCoreHex`)
- FL-T400 Fuel Tank (`fuelTank`)
- FL-T400 Fuel Tank (`fuelTank`)
- LV-909 "Terrier" Liquid Fuel Engine (`liquidEngine3_v2`)
- TD-12 Decoupler (`Decoupler_1`)

## Sustainer / orbital insertion stage
- FL-T800 Fuel Tank (`fuelTank_long`)
- FL-T800 Fuel Tank (`fuelTank_long`)
- LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
- TD-12 Decoupler (`Decoupler_1`)

## Booster core / launch stage
- FL-T800 Fuel Tank (`fuelTank_long`)
- LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
- 2 × BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`)
- 2 × TT-70 Radial Decoupler (`radialDecoupler2`)
- 4 × Basic Fin

## Staging order
1. Launch stage: lower LV-T45 "Swivel" + both BACC "Thumper" SRBs ignite together
2. SRB separation: decouple both radial boosters when empty
3. Core separation / sustainer continuation
4. Upper-stage separation and Terrier ignition

## Exact part list
- 1 × Probodobodyne HECS
- 2 × FL-T400 Fuel Tank
- 3 × FL-T800 Fuel Tank
- 1 × LV-909 "Terrier" Liquid Fuel Engine
- 2 × LV-T45 "Swivel" Liquid Fuel Engine
- 2 × BACC "Thumper" Solid Fuel Booster
- 2 × TD-12 Decoupler
- 2 × TT-70 Radial Decoupler
- 4 × Basic Fin

## Stage performance estimate
| Firing stage | Components active | Approx vacuum dV | Approx TWR at ignition |
|---|---|---:|---:|
| Launch assist | 2 × BACC + lower Swivel | ~2100 m/s | ~2.0+ |
| Sustainer | Swivel + 2 × FL-T800 | ~1900 m/s | ~1.1+ in upper atmosphere/vac |
| Transfer/capture | Terrier + 2 × FL-T400 | ~1800 m/s | ~0.6 in vacuum |

## Total delta-v
Estimated total vacuum dV: **~5800 m/s**

## TWR constraints
- Launch TWR: **> 1.3** (planned ~2.0+)
- Upper stages: lower TWR acceptable for vacuum burns

## Decoupler placement
- `TD-12 Decoupler` between Terrier upper stage and sustainer
- `TD-12 Decoupler` between sustainer and lower core
- `TT-70 Radial Decoupler` under each Thumper

## SAS / RCS
- SAS/attitude authority: HECS reaction wheel + kRPC autopilot
- RCS: none

## Operator build notes
Build exactly as in attempt 1. No vehicle redesign is intended for this software-isolation run.

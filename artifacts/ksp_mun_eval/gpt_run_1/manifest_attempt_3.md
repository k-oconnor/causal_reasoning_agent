# Manifest — Attempt 3

## Rationale
Attempt 2 demonstrated adequate ascent performance and failed due to a stale vessel/autopilot reference after stage separation, not due to vehicle insufficiency. Therefore the manifest remains unchanged to isolate the software-control fix.

## Vehicle concept
Conservative 3-stage Mun orbiter with:
- Launch core: lower Swivel + 2 radial Thumpers
- Sustainer/orbital insertion stage: Swivel + 2 × FL-T800
- Transfer/capture stage: Terrier + 2 × FL-T400

## Exact parts
- 1 × Probodobodyne HECS (`probeCoreHex`)
- 2 × FL-T400 Fuel Tank (`fuelTank`)
- 3 × FL-T800 Fuel Tank (`fuelTank_long`)
- 1 × LV-909 "Terrier" Liquid Fuel Engine (`liquidEngine3_v2`)
- 2 × LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
- 2 × BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`)
- 2 × TD-12 Decoupler (`Decoupler_1`)
- 2 × TT-70 Radial Decoupler (`radialDecoupler2`)
- 4 × Basic Fin

## Stage table
| Firing stage | Components active | Approx vacuum dV | Approx TWR at ignition | Decoupler / separation |
|---|---|---:|---:|---|
| Launch assist | Lower LV-T45 "Swivel" + 2 × BACC "Thumper" | ~2100 m/s | ~2.0+ | TT-70 radial decouplers release SRBs after burnout |
| Sustainer ascent | LV-T45 "Swivel" + 2 × FL-T800 | ~1900 m/s | ~1.1+ in upper atmosphere/vac | TD-12 separates sustainer from Terrier stack |
| Transfer/capture | LV-909 "Terrier" + 2 × FL-T400 | ~1800 m/s | ~0.6 in vacuum | No further separation required |

## Total delta-v
Estimated total vacuum dV: **~5800 m/s**

## TWR constraints
- First-stage liftoff TWR: **> 1.3**, planned ~2.0+
- Upper stages: lower TWR acceptable for vacuum operations

## Decoupler placement
- `TT-70 Radial Decoupler` beneath each radial Thumper
- `TD-12 Decoupler` between lower core and sustainer/upper stack
- `TD-12 Decoupler` between sustainer and Terrier transfer stage

## SAS / RCS
- SAS / attitude authority via HECS reaction wheel and kRPC autopilot
- RCS not included

## Operator notes
Build identically to attempt 2 / attempt 1. No design changes are intended in this iteration.

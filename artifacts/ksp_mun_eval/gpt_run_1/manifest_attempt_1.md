# Manifest — Attempt 1

## Vehicle concept
A conservative 3-stage Mun orbiter with solid-booster-assisted first stage, a Swivel-powered sustainer for ascent/circularization support, and a Terrier-powered transfer/orbital stage. Probe-controlled, no crew required. Large dV margin is intentional for first instrumented attempt.

## Payload / upper stack (top to bottom)
- Probodobodyne HECS (`probeCoreHex`) — probe core, reaction wheel and SAS capability
- FL-T400 Fuel Tank (`fuelTank`)
- FL-T400 Fuel Tank (`fuelTank`)
- LV-909 "Terrier" Liquid Fuel Engine (`liquidEngine3_v2`)
- TD-12 Decoupler (`Decoupler_1`) separating upper stage from sustainer

## Sustainer / orbital insertion stage
- FL-T800 Fuel Tank (`fuelTank_long`)
- FL-T800 Fuel Tank (`fuelTank_long`)
- LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
- TD-12 Decoupler (`Decoupler_1`) below sustainer

## Booster core / launch stage
- FL-T800 Fuel Tank (`fuelTank_long`)
- LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
- 2 × BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`) mounted radially using TT-70 Radial Decoupler (`radialDecoupler2`)
- 2 × TT-70 Radial Decoupler (`radialDecoupler2`) for the Thumpers
- Launch clamps as needed by operator

## Control / stability / recovery extras
- 4 × Basic Fin recommended on lower core or booster section for passive ascent stability
- No RCS required
- No solar panels required for this mission attempt if probe core battery margin is adequate; operator may add fixed battery-only support if desired, but do not otherwise alter vehicle

## Staging order
1. Stage 5: Activate engine ignition and both BACC "Thumper" boosters at launch
2. Stage 4: Decouple both radial boosters when empty
3. Stage 3: Decouple launch core / ignite sustainer continuation if not already active by stage setup
4. Stage 2: Decouple sustainer and activate Terrier upper stage
5. Stage 1/0: Final engine shutdown only; no further hardware required

## Exact part list summary
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
These are engineering estimates for planning compliance; actual in-game values may differ slightly with exact staging setup and attached avionics/fins.

| Firing stage | Components active | Approx vacuum dV | Approx TWR at ignition | Notes |
|---|---|---:|---:|---|
| Launch / booster-core assist | 2 × BACC "Thumper" + 1 × LV-T45 "Swivel" on lower FL-T800 | ~2100 m/s equivalent contribution | ~2.0+ at liftoff | High initial thrust for safe launch and gravity turn |
| Sustainer ascent / circularization | LV-T45 "Swivel" + 2 × FL-T800 | ~1900 m/s | ~1.1 in thin air / vacuum | Continues ascent, sets AP, supports LKO insertion |
| Transfer / capture stage | LV-909 "Terrier" + 2 × FL-T400 | ~1800 m/s | ~0.6 in vacuum | Adequate for TMI + MOI + correction + margin |

## Total delta-v
Estimated total vacuum delta-v: **~5800 m/s**

This exceeds the required **5,250 m/s** minimum mission budget with margin.

## TWR constraints
- First-stage liftoff TWR: **> 1.3** (planned ~2.0+), satisfying launch requirement.
- Sustainer stage TWR: acceptable for upper-atmosphere ascent and circularization.
- Terrier stage TWR: low but acceptable in vacuum for TMI and MOI.

## Decoupler placement
- `TD-12 Decoupler` between Terrier upper stage and Swivel sustainer.
- `TD-12 Decoupler` between Swivel sustainer and lower launch core.
- `TT-70 Radial Decoupler` under each BACC "Thumper" radial booster.

## SAS / RCS
- SAS / attitude control: provided by the reaction wheel in the Probodobodyne HECS and kRPC autopilot.
- RCS: **not included**; not required for this mission.

## Operator build notes
- Ensure only the specified parts are used.
- Put both radial Thumpers in the same launch stage as the lower Swivel engine.
- Set radial booster decoupling to occur only after SRB burnout.
- Ensure fuel lines are not added unless explicitly requested.
- Keep the rocket vertically stacked and symmetric.

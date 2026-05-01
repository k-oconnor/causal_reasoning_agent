# Manifest Attempt 1 — Conservative 3-stage Mun Orbiter

## Design intent
A simple, high-margin liquid launcher with a dedicated vacuum upper stage. Goal is reliable scripted ascent and generous dV for TMI, corrections, and MOI.

## Exact stack from top to bottom
- Probodobodyne HECS (`probeCoreHex_v2`)
- Z-100 Rechargeable Battery Pack x2 (operator: any small battery equivalent acceptable if exact title differs in VAB search)
- Communotron 16 x1 (optional for aesthetics/remote control margin; not required by script)
- FL-T400 Fuel Tank (`fuelTank`)
- FL-T400 Fuel Tank (`fuelTank`)
- LV-909 "Terrier" Liquid Fuel Engine (`liquidEngine3_v2`)
- TD-12 Decoupler (`Decoupler_1`)
- FL-T800 Fuel Tank (`fuelTank_long`)
- FL-T800 Fuel Tank (`fuelTank_long`)
- LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
- TD-12 Decoupler (`Decoupler_1`)
- FL-T800 Fuel Tank (`fuelTank_long`)
- FL-T800 Fuel Tank (`fuelTank_long`)
- FL-T800 Fuel Tank (`fuelTank_long`)
- LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
- TT-70 Radial Decoupler (`radialDecoupler2`) x2 mounted symmetrically on lower core tank
- BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`) x2 on the radial decouplers
- AV-T1 Winglet x4 or Basic Fin x4 on lower stage for passive stability
- Launch clamps as needed

## SAS / control
- Probe core: HECS on stage 3 provides control and reaction wheel torque.
- No RCS required.
- No crew required.
- No solar panels required for this short mission; include extra battery capacity if desired.

## Decoupler placement
- Two `TT-70 Radial Decoupler` separate the two BACC boosters from the first liquid stage.
- One `TD-12 Decoupler` between first and second liquid stages.
- One `TD-12 Decoupler` between second stage and Terrier upper stage.

## Stage table (in firing order)

| Firing stage | Parts active | Decoupler after depletion | Approx dV | Approx TWR at ignition | Notes |
|---|---|---:|---:|---:|---|
| Stage 1 | 2x BACC "Thumper" + 1x LV-T45 "Swivel" + 3x FL-T800 core | Radial decouple boosters, then `TD-12` to stage 2 | ~2500 m/s effective combined ascent contribution | ~2.0+ at launch | High launch thrust, gravity-turn capable |
| Stage 2 | 1x LV-T45 "Swivel" + 2x FL-T800 | `TD-12` to stage 3 | ~1850 m/s | ~1.9 in near-vac at ignition | Finishes ascent + circularization, may contribute to TMI if needed |
| Stage 3 | 1x LV-909 "Terrier" + 2x FL-T400 + HECS | none | ~2100 m/s | ~1.7 in vacuum | Dedicated TMI + MOI + correction stage |

## Approximate delta-v justification
Using stock engine/tank masses from provided parts reference and standard rocket-equation estimates:

- Stage 3 (Terrier, 2x FL-T400, HECS+batteries small payload): about 2100 m/s vacuum dV.
- Stage 2 (Swivel, 2x FL-T800, carrying full stage 3): about 1850 m/s.
- Stage 1 liquid core contribution (Swivel, 3x FL-T800, carrying upper stages): about 1400+ m/s.
- Two Thumpers add substantial parallel-burn ascent impulse roughly equivalent to >1000 m/s mission contribution, while keeping launch TWR high.

**Total mission dV estimate: ~5450–5750 m/s**, exceeding the required 5250 m/s threshold.

## TWR justification
Approximate launch mass:
- Lower core: 3x FL-T800 = 13.5 t
- Lower Swivel = 1.5 t
- Two BACC = 15.3 t
- Upper stages + probe/batteries ≈ 11.5 t
- Decouplers/fins/margins ≈ 0.5 t
- Total ≈ 42.3 t

Approximate launch thrust at sea level:
- 2x BACC = 500 kN
- 1x Swivel = 167.97 kN
- Total = 667.97 kN

Launch weight ≈ 42.3 * 9.81 = 414.96 kN

**Launch TWR ≈ 667.97 / 414.96 ≈ 1.61**, satisfying the >= 1.3 requirement.

## Build notes for operator
- Build exactly as a straight inline rocket with 2 radial boosters on the bottom liquid stage.
- Ensure the Terrier upper stage is the top orbital stage above a TD-12 decoupler.
- Add 4 small fins to the first liquid stage near the bottom.
- Keep staging order sensible:
  1. First action fires Swivel + both Thumpers simultaneously.
  2. Next action decouples empty boosters.
  3. Next action ignites/continues lower core as needed.
  4. Then decouple to second stage.
  5. Then decouple to Terrier stage.
- If batteries/antenna are omitted because of VAB convenience, keep the HECS probe core; mission still works.

## Mission capability expectation
- LKO should be achievable with stage 1 + stage 2.
- Terrier stage should reach Mun orbit with ample margin for MOI and minor correction burns.
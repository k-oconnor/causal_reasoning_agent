# Manifest Attempt 2 — Advanced Stable Mun Orbiter

## Design intent
Use sturdier Making History hardware with fewer radial complications. The goal is a stable scripted ascent, robust stage transitions, and abundant delta-v for Mun transfer and capture.

## Exact stack from top to bottom
### Payload / orbital stage
- Probodobodyne HECS (`probeCoreHex_v2`)
- Small battery packs x2 (operator may choose any small stock battery)
- FL-T400 Fuel Tank (`fuelTank`)
- FL-T400 Fuel Tank (`fuelTank`)
- LV-T91 "Cheetah" Liquid Fuel Engine (`LiquidEngineLV-T91`)
- TD-12 Decoupler (`Decoupler_1`)

### Transfer / upper ascent stage
- FL-TX900 Fuel Tank (`Size1p5_Tank_03`)
- FL-TX900 Fuel Tank (`Size1p5_Tank_03`)
- LV-TX87 "Bobcat" Liquid Fuel Engine (`LiquidEngineLV-TX87`)
- TD-18 Decoupler (`Decoupler_1p5`)

### Core launch stage
- FL-A215 Fuel Tank Adapter (`Size1p5_Size2_Adapter_01`)  [2.5 m bottom to 1.875 m upper stack]
- Rockomax X200-16 Fuel Tank (`Rockomax16_BW`)
- Rockomax X200-16 Fuel Tank (`Rockomax16_BW`)
- RE-I2 "Skiff" Liquid Fuel Engine (`LiquidEngineRE-I2`)
- AV-T1 Winglet or Delta-Deluxe Winglet x4 near base
- Launch clamps as needed

## SAS / RCS
- HECS probe core provides reaction wheel authority.
- No RCS required.
- No radial boosters in this attempt to maximize stability and simplify staging.

## Decoupler placement
- `TD-18 Decoupler` between core launch stage and Bobcat stage.
- `TD-12 Decoupler` between Bobcat stage and Cheetah stage.

## Stage table (in firing order)

| Firing stage | Parts active | Decoupler placement | Approx dV | Approx TWR at ignition | Notes |
|---|---|---|---:|---:|---|
| Stage 1 | RE-I2 "Skiff" + 2x Rockomax X200-16 + FL-A215 adapter | `TD-18` above adapter/upper stack | ~2500 m/s | ~1.7 at launch | Stable 2.5 m core launcher |
| Stage 2 | LV-TX87 "Bobcat" + 2x FL-TX900 | `TD-12` above 1.875 m stage | ~1750 m/s | ~1.8 in upper atmosphere/vac | Finishes ascent, circularizes, performs most/all TMI |
| Stage 3 | LV-T91 "Cheetah" + 2x FL-T400 + probe/batteries | none | ~1900 m/s | ~2.5 in vacuum | Dedicated Mun capture/corrections/orbit shaping |

## Delta-v justification
Approximate vacuum budget from reference-part masses and engine Isp:
- Stage 1: ~2500 m/s
- Stage 2: ~1750 m/s
- Stage 3: ~1900 m/s

**Total estimated dV: ~6150 m/s**, comfortably above the 5,250 m/s requirement.

## Launch TWR justification
Approximate launch mass:
- Core stage: FL-A215 6.75 t + 2x X200-16 18 t + Skiff 1.6 t = 26.35 t
- Upper stages combined ≈ 13.5 t
- Probe/decouplers/fins/batteries margin ≈ 0.8 t
- Total ≈ 40.7 t

Approximate sea-level thrust:
- RE-I2 "Skiff" thrust SL = 240.91 kN

This alone gives TWR ≈ 240.91 / (40.7*9.81) ≈ 0.60, which is insufficient.

Therefore add **2x BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`)** radially on the lower core with **2x TT-70 Radial Decoupler (`radialDecoupler2`)**.

Updated launch thrust:
- Skiff: 240.91 kN
- 2x BACC: 500 kN
- Total: 740.91 kN

Updated launch mass adds 15.3 t boosters -> total ≈ 56.0 t
Launch weight ≈ 56.0 * 9.81 = 549.4 kN

**Launch TWR ≈ 740.91 / 549.4 ≈ 1.35**, satisfying the >= 1.3 requirement.

The boosters are attached to a broad 2.5 m core with fins, making this much more stable than attempt 1's narrow lower stack.

## Final exact lower stack amendment
From bottom upward, the true lower stage is:
- RE-I2 "Skiff" Liquid Fuel Engine (`LiquidEngineRE-I2`)
- Rockomax X200-16 Fuel Tank (`Rockomax16_BW`)
- Rockomax X200-16 Fuel Tank (`Rockomax16_BW`)
- FL-A215 Fuel Tank Adapter (`Size1p5_Size2_Adapter_01`)
- TD-18 Decoupler (`Decoupler_1p5`)
- Bobcat stage above

Radially attached to the lowest X200-16:
- TT-70 Radial Decoupler x2
- BACC "Thumper" x2
- 4 fins on the core base

## Build notes for operator
- Keep the rocket perfectly symmetrical.
- Put the two Thumpers directly opposite each other, low on the core.
- Put four fins evenly around the bottom core tank.
- Ensure staging order is:
  1. Launch stage: ignite Skiff + both Thumpers.
  2. Separate Thumpers when empty.
  3. Continue core stage.
  4. Decouple to Bobcat stage.
  5. Decouple to Cheetah stage.
- Do not add extra payload or recovery hardware.

## Expected mission profile
- Core + boosters: safe atmospheric ascent.
- Bobcat stage: upper ascent + circularization + TMI.
- Cheetah stage: Mun arrival correction + MOI + final stable orbit.
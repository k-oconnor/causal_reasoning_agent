# Manifest Attempt 4 — Boosterless Closed-Loop Orbiter

## Design intent
Remove all radial-booster staging ambiguity. Use a powerful liquid first stage and two clean upper stages. Mission software will use closed-loop circularization rather than delayed maneuver-node execution.

## Exact stack from top to bottom
### Stage 3 — Mun capture/orbital stage
- Probodobodyne HECS (`probeCoreHex_v2`)
- Small battery packs x2
- FL-T400 Fuel Tank (`fuelTank`)
- FL-T400 Fuel Tank (`fuelTank`)
- LV-T91 "Cheetah" Liquid Fuel Engine (`LiquidEngineLV-T91`)
- TD-12 Decoupler (`Decoupler_1`)

### Stage 2 — Orbital/TMI stage
- FL-TX1800 Fuel Tank (`Size1p5_Tank_04`)
- LV-TX87 "Bobcat" Liquid Fuel Engine (`LiquidEngineLV-TX87`)
- TD-18 Decoupler (`Decoupler_1p5`)

### Stage 1 — Liquid launch stage
- FL-A215 Fuel Tank Adapter (`Size1p5_Size2_Adapter_01`)
- Rockomax X200-32 Fuel Tank (`Rockomax32_BW`)
- Rockomax X200-16 Fuel Tank (`Rockomax16_BW`)
- RE-M3 "Mainsail" Liquid Fuel Engine (`liquidEngineMainsail_v2`)
- AV-T1 Winglet / equivalent fins x4 at base
- Launch clamps as needed

## SAS / RCS
- HECS probe core provides control.
- No RCS required.

## Decoupler placement
- `TD-18 Decoupler` between liquid first stage and Bobcat stage.
- `TD-12 Decoupler` between Bobcat stage and Cheetah stage.

## Stage table

| Firing stage | Parts active | Approx dV | Approx TWR at ignition | Notes |
|---|---|---:|---:|---|
| Stage 1 | RE-M3 "Mainsail" + X200-32 + X200-16 + FL-A215 | ~3300 m/s | ~2.0 at launch | Strong, simple atmospheric stage |
| Stage 2 | LV-TX87 "Bobcat" + FL-TX1800 | ~1600 m/s | ~1.9 vac | Circularization + most/all TMI |
| Stage 3 | LV-T91 "Cheetah" + 2x FL-T400 | ~1900 m/s | ~2.5 vac | Mun capture / corrections |

## Delta-v justification
Estimated total: ~6800 m/s.
- Stage 1: ~3300 m/s
- Stage 2: ~1600 m/s
- Stage 3: ~1900 m/s

This exceeds the required 5250 m/s by a large margin.

## Launch TWR justification
Approximate launch mass:
- X200-32: 18.0 t
- X200-16: 9.0 t
- FL-A215: 6.75 t
- Mainsail: 6.0 t
- Upper stages + payload: ~14 t
- Misc: ~0.8 t
- Total ≈ 54.6 t

Sea-level thrust:
- Mainsail: 1379.03 kN

Launch weight ≈ 54.6 * 9.81 = 535.6 kN

**Launch TWR ≈ 1379.03 / 535.6 ≈ 2.57**, well above minimum.

## Build notes for operator
- This is a pure inline rocket: no radial boosters.
- Keep the stack perfectly straight.
- Put four fins around the base.
- Staging order should be extremely simple:
  1. Ignite Mainsail
  2. Decouple to Bobcat stage
  3. Decouple to Cheetah stage

## Expected mission profile
- Mainsail takes vehicle high and fast without staging ambiguity.
- Bobcat performs upper ascent and circularization.
- Cheetah reserved for transfer/capture precision.
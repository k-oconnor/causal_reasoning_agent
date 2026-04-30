# Manifest Attempt 3 — High-Thrust Simple Mun Launcher

## Design intent
Eliminate pad-thrust ambiguity and reduce build fragility. This design uses a powerful 2.5 m core with radial boosters and two clean upper stages.

## Exact stack from top to bottom
### Stage 3 — Mun orbital stage
- Probodobodyne HECS (`probeCoreHex_v2`)
- Small battery packs x2
- FL-T400 Fuel Tank (`fuelTank`)
- FL-T400 Fuel Tank (`fuelTank`)
- LV-T91 "Cheetah" Liquid Fuel Engine (`LiquidEngineLV-T91`)
- TD-12 Decoupler (`Decoupler_1`)

### Stage 2 — Kerbin upper ascent / TMI stage
- FL-TX1800 Fuel Tank (`Size1p5_Tank_04`)
- LV-TX87 "Bobcat" Liquid Fuel Engine (`LiquidEngineLV-TX87`)
- TD-18 Decoupler (`Decoupler_1p5`)

### Stage 1 — Launch core
- FL-A215 Fuel Tank Adapter (`Size1p5_Size2_Adapter_01`)
- Rockomax X200-32 Fuel Tank (`Rockomax32_BW`)
- RE-M3 "Mainsail" Liquid Fuel Engine (`liquidEngineMainsail_v2`)
- TT-70 Radial Decoupler (`radialDecoupler2`) x2
- BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`) x2
- AV-T1 Winglet / similar fins x4 at base
- Launch clamps as needed

## SAS / RCS
- HECS provides control authority.
- No RCS required.

## Decoupler placement
- `TT-70 Radial Decoupler` separate the two BACC boosters from the first stage.
- `TD-18 Decoupler` between Mainsail core and Bobcat stage.
- `TD-12 Decoupler` between Bobcat stage and Cheetah stage.

## Stage table (firing order)

| Firing stage | Parts active | Approx dV | Approx TWR at ignition | Notes |
|---|---|---:|---:|---|
| Stage 1 | RE-M3 "Mainsail" + 2x BACC + 1x Rockomax X200-32 | ~3000 m/s effective ascent contribution | ~1.9+ at launch | Strong, unambiguous liftoff |
| Stage 2 | LV-TX87 "Bobcat" + 1x FL-TX1800 | ~1600 m/s | ~1.8 vac | Completes ascent/circularization/TMI support |
| Stage 3 | LV-T91 "Cheetah" + 2x FL-T400 | ~1900 m/s | ~2.5 vac | Mun capture/orbit shaping |

## Delta-v justification
Conservative estimate:
- Stage 1 effective ascent contribution: ~3000 m/s
- Stage 2: ~1600 m/s
- Stage 3: ~1900 m/s

**Total estimated mission dV: ~6500 m/s**, well above 5250 m/s requirement.

## Launch TWR justification
Approximate launch mass:
- X200-32: 18.0 t
- Mainsail: 6.0 t
- Two BACC: 15.3 t
- Adapter: 6.75 t
- Upper stages + payload: ~14 t
- Decouplers/fins margin: ~0.8 t
- Total ≈ 60.9 t

Approximate sea-level thrust:
- Mainsail SL thrust: 1379.03 kN
- 2x BACC: 500 kN
- Total: 1879.03 kN

Launch weight ≈ 60.9 * 9.81 = 597.4 kN

**Launch TWR ≈ 1879.03 / 597.4 ≈ 3.15**, far above the minimum 1.3 and comfortably robust.

## Build notes for operator
- Keep the vehicle perfectly straight and symmetric.
- Place two Thumpers symmetrically low on the core tank.
- Add four fins around the bottom.
- Verify first stage staging group ignites Mainsail and both Thumpers together.
- Next stage should decouple the boosters only.
- Then the core continues until near depletion; then decouple to Bobcat; then to Cheetah.

## Expected mission profile
- Very strong initial ascent with throttle limiting under max Q.
- Bobcat handles upper ascent and likely most TMI.
- Cheetah reserved for fine transfer/capture work at Mun.
# Manifest Attempt 5 — Inline 3-Stage Mun Orbiter (staging-sensor fix test)

## Design intent
Reuse the attempt-4 inline architecture because the prior failure was software staging detection, not a demonstrated vehicle performance shortfall. Keep the rocket simple, high-margin, and easy to instrument.

## Exact stack from top to bottom

### Stage 3 — Mun transfer / capture / final orbit stage
- Probodobodyne HECS (`probeCoreHex_v2`)
- Z-200 Battery Bank x2
- FL-T400 Fuel Tank (`fuelTank`)
- FL-T400 Fuel Tank (`fuelTank`)
- LV-T91 "Cheetah" Liquid Fuel Engine (`LiquidEngineLV-T91`)
- TD-12 Decoupler (`Decoupler_1`)

### Stage 2 — Upper ascent / circularization / main TMI stage
- FL-TX1800 Fuel Tank (`Size1p5_Tank_04`)
- LV-TX87 "Bobcat" Liquid Fuel Engine (`LiquidEngineLV-TX87`)
- TD-18 Decoupler (`Decoupler_1p5`)

### Stage 1 — Kerbin launch stage
- FL-A215 Fuel Tank Adapter (`Size1p5_Size2_Adapter_01`)
- Rockomax X200-32 Fuel Tank (`Rockomax32_BW`)
- Rockomax X200-16 Fuel Tank (`Rockomax16_BW`)
- RE-M3 "Mainsail" Liquid Fuel Engine (`liquidEngineMainsail_v2`)
- AV-T1 Winglet x4 near the base
- Launch clamps as needed

## SAS / RCS
- SAS authority via HECS probe core reaction wheel.
- No RCS required.

## Decoupler placement
- `TD-18 Decoupler` between Stage 1 and Stage 2.
- `TD-12 Decoupler` between Stage 2 and Stage 3.

## Stage table

| Firing stage | Engines / tanks / separators | Approx dV | Approx TWR at ignition | Notes |
|---|---|---:|---:|---|
| Stage 1 | RE-M3 "Mainsail" + `Rockomax32_BW` + `Rockomax16_BW` + `Size1p5_Size2_Adapter_01` | ~3300 m/s | ~2.5 at Kerbin SL | Atmospheric ascent to high suborbital trajectory |
| Stage 2 | LV-TX87 "Bobcat" + `Size1p5_Tank_04` | ~1600 m/s | ~1.9 vac | Finish ascent, circularize, deliver most/all TMI |
| Stage 3 | LV-T91 "Cheetah" + 2×`fuelTank` | ~1900 m/s | ~2.5 vac | Mun encounter refinement, MOI, and orbit trimming |

## Total delta-v
Estimated total vacuum delta-v: **~6800 m/s**.

Breakdown:
- Stage 1: ~3300 m/s
- Stage 2: ~1600 m/s
- Stage 3: ~1900 m/s

This exceeds the mission minimum **5250 m/s** by roughly **1550 m/s**.

## TWR justification

### Launch stage
Approximate launch mass:
- Rockomax X200-32 Fuel Tank: 18.0 t
- Rockomax X200-16 Fuel Tank: 9.0 t
- FL-A215 Fuel Tank Adapter: 6.75 t
- RE-M3 "Mainsail": 6.0 t
- Upper stages + probe + batteries + decouplers + fins: ~14.8 t
- Total ≈ 54.6 t

Sea-level thrust:
- RE-M3 "Mainsail": 1379.03 kN

Weight at launch ≈ 54.6 × 9.81 = 535.6 kN

**Launch TWR ≈ 1379.03 / 535.6 ≈ 2.57**, satisfying the requirement `>= 1.3` with wide margin.

### Upper stages
- Bobcat stage TWR in vacuum is comfortably above 1, suitable for circularization and TMI.
- Cheetah stage TWR in vacuum is also comfortably above 1, suitable for MOI and cleanup burns.

## Operator build notes
- Build as a perfectly straight inline stack.
- Put four AV-T1 Winglets symmetrically around the Mainsail stage.
- Ensure staging order in the editor is:
  1. Launch clamps release + Mainsail ignite
  2. `TD-18 Decoupler` separate Stage 1 and ignite Bobcat stage
  3. `TD-12 Decoupler` separate Stage 2 and ignite Cheetah stage
- No manual piloting during flight.

## Mission expectation for this attempt
The rocket should now pass the prior failure boundary if the new script stages on actual active-stage depletion. Primary success criterion for this experiment: clean separation to Bobcat stage and continuation to AP >= 85 km; full mission success remains the overall goal.
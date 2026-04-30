# Manifest — Attempt 4

## Design goal
Eliminate ascent-stage ambiguity while keeping total vacuum delta-v above the 5,250 m/s requirement.

## Top-to-bottom stack order (build exactly in this order)
1. Probodobodyne HECS (`probeCoreHex`)
2. FL-T400 Fuel Tank (`fuelTank`)
3. FL-T400 Fuel Tank (`fuelTank`)
4. FL-T400 Fuel Tank (`fuelTank`)
5. LV-909 "Terrier" Liquid Fuel Engine (`liquidEngine3_v2`)
6. TD-12 Decoupler (`Decoupler_1`)  ← separates upper Terrier stage from ascent core
7. FL-T800 Fuel Tank (`fuelTank_long`)
8. FL-T800 Fuel Tank (`fuelTank_long`)
9. FL-T800 Fuel Tank (`fuelTank_long`)
10. LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
11. 2 × BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`) mounted radially on the lower core using 2 × TT-70 Radial Decoupler (`radialDecoupler2`)
12. 4 × Basic Fin on lower core/booster section

## Vehicle concept
- **Stage A (launch core):** single Swivel core with 3 × FL-T800, assisted by 2 radial Thumpers
- **Stage B (orbital/transfer stage):** Terrier with 3 × FL-T400

This removes the ambiguous second Swivel stage entirely.

## Exact part list
- 1 × Probodobodyne HECS
- 3 × FL-T400 Fuel Tank
- 3 × FL-T800 Fuel Tank
- 1 × LV-909 "Terrier" Liquid Fuel Engine
- 1 × LV-T45 "Swivel" Liquid Fuel Engine
- 2 × BACC "Thumper" Solid Fuel Booster
- 1 × TD-12 Decoupler
- 2 × TT-70 Radial Decoupler
- 4 × Basic Fin

## Stage table
| Firing stage | Components active | Approx vacuum dV | Approx TWR at ignition | Decoupler placement / action |
|---|---|---:|---:|---|
| Launch assist | LV-T45 "Swivel" + 2 × BACC "Thumper" | ~2500 m/s equivalent ascent contribution | ~1.8–2.0 | SRBs drop from TT-70 radial decouplers after burnout |
| Upper stage | LV-909 "Terrier" + 3 × FL-T400 | ~3300 m/s vacuum | ~0.45–0.6 depending on mass | TD-12 separates exhausted Swivel core, Terrier ignites |

## Total delta-v
Estimated total vacuum delta-v: **~5800–6200 m/s**

This exceeds the required **5,250 m/s** threshold.

## TWR constraints
- Launch TWR: **> 1.3** (planned ~1.8–2.0 with Thumpers + Swivel)
- Upper stage TWR: low but acceptable in vacuum for circularization/TMI/MOI

## Decoupler placement
- `TT-70 Radial Decoupler` under each Thumper
- `TD-12 Decoupler` between the 3×FL-T800 Swivel core and the 3×FL-T400 Terrier stage

## SAS / RCS
- SAS / attitude control via HECS reaction wheel + kRPC autopilot
- No RCS

## Mandatory VAB staging order (very important)
Configure stages so that:
1. **Launch stage:** ignite Swivel core and both Thumpers together
2. **Second stage action:** decouple both radial Thumpers only
3. **Third stage action:** decouple the exhausted core AND ignite the Terrier upper stage

There should be **no other engine activations or decouplers** in the ascent stack.

## Operator build notes
- Build exactly top-to-bottom as listed.
- Ensure the Terrier stage is above the TD-12 decoupler and the Swivel core is below it.
- Ensure the Swivel is the only liquid engine below the decoupler.
- Ensure the Terrier ignition is in the same stage action as core separation, or at least immediately after it per script expectations.

# Manifest — Attempt 5

## Rationale
Attempt 4 showed the simplified launcher is structurally reliable and has sufficient performance. The remaining change for the final attempt is guidance, not vehicle hardware. Therefore the manifest is unchanged from attempt 4.

## Top-to-bottom stack order
1. Probodobodyne HECS (`probeCoreHex`)
2. FL-T400 Fuel Tank (`fuelTank`)
3. FL-T400 Fuel Tank (`fuelTank`)
4. FL-T400 Fuel Tank (`fuelTank`)
5. LV-909 "Terrier" Liquid Fuel Engine (`liquidEngine3_v2`)
6. TD-12 Decoupler (`Decoupler_1`)
7. FL-T800 Fuel Tank (`fuelTank_long`)
8. FL-T800 Fuel Tank (`fuelTank_long`)
9. FL-T800 Fuel Tank (`fuelTank_long`)
10. LV-T45 "Swivel" Liquid Fuel Engine (`liquidEngine2_v2`)
11. 2 × BACC "Thumper" Solid Fuel Booster (`solidBooster1-1`) on 2 × TT-70 Radial Decoupler (`radialDecoupler2`)
12. 4 × Basic Fin on lower core

## Stage table
| Firing stage | Components active | Approx vacuum dV | Approx TWR at ignition | Decoupler placement / action |
|---|---|---:|---:|---|
| Launch assist | LV-T45 "Swivel" + 2 × BACC "Thumper" | ~2500 m/s ascent contribution | ~1.8–2.0 | SRBs decouple from TT-70 radial decouplers after burnout |
| Upper stage | LV-909 "Terrier" + 3 × FL-T400 | ~3300 m/s vacuum | ~0.45–0.6 | TD-12 separates exhausted core and ignites Terrier |

## Total delta-v
Estimated total vacuum dV: **~5800–6200 m/s**

## TWR constraints
- Liftoff TWR: **> 1.3**
- Upper-stage TWR: suitable for vacuum burns

## Decoupler placement
- `TT-70 Radial Decoupler` under each Thumper
- `TD-12 Decoupler` between core and Terrier upper stage

## SAS / RCS
- SAS/attitude control via HECS reaction wheel and kRPC autopilot
- No RCS

## Mandatory VAB staging order
1. Launch: ignite Swivel core and both Thumpers together
2. Decouple both SRBs only
3. Decouple exhausted core and ignite Terrier upper stage

No additional ascent-stage complexity.

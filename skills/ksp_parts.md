# KSP 1.12.5 Stock Parts Reference

Generated directly from GameData .cfg files — exact stats for this installation.

**Internal Name** = the `name` field in the .cfg — what kRPC returns for `part.name`.
**Title** = the display name shown in the VAB parts list.

Mass = dry mass for engines, decouplers, command pods.
For tanks: dry mass (empty) and wet mass (full). 1 unit LF or OX = 5 kg.

**Thrust SL** is computed from `thrust_vac × (Isp_SL / Isp_vac)`.

Pack: `Squad` = stock, `MakingHistory` = Making History DLC, `Serenity` = Breaking Ground DLC.

---

## Liquid Fuel Engines

| Title | Internal Name | Mass (t) | Thrust Vac (kN) | Thrust SL (kN) | Isp Vac (s) | Isp SL (s) | Gimbal (°) | Pack |
|---|---|---|---|---|---|---|---|---|
| LV-1 "Ant" Liquid Fuel Engine | `microEngine_v2` | 0.020 | 2.00 | 0.51 | 315 | 80 | 0.0 | Squad |
| LV-1R "Spider" Liquid Fuel Engine | `radialEngineMini_v2` | 0.020 | 2.00 | 1.79 | 290 | 260 | 10.0 | Squad |
| 24-77 "Twitch" Liquid Fuel Engine | `smallRadialEngine` | 0.090 | 16.00 | 13.79 | 290 | 250 | 8.0 | Squad |
| 24-77 "Twitch" Liquid Fuel Engine | `smallRadialEngine_v2` | 0.080 | 16.00 | 15.17 | 290 | 275 | 8.0 | Squad |
| 48-7S "Spark" Liquid Fuel Engine | `liquidEngineMini_v2` | 0.130 | 20.00 | 16.56 | 320 | 265 | 3.0 | Squad |
| O-10 "Puff" MonoPropellant Fuel Engine | `omsEngine` | 0.090 | 20.00 | 9.60 | 250 | 120 | 6.0 | Squad |
| RV-1 "Cub" Vernier Engine | `LiquidEngineRV-1` | 0.180 | 32.00 | 28.90 | 310 | 280 | 22.5 | MakingHistory |
| LV-909 "Terrier" Liquid Fuel Engine | `liquidEngine3_v2` | 0.500 | 60.00 | 14.78 | 345 | 85 | 4.0 | Squad |
| LV-N "Nerv" Atomic Rocket Motor | `nuclearEngine` | 3.000 | 60.00 | 13.88 | 800 | 185 | 0.0 | Squad |
| Mk-55 "Thud" Liquid Fuel Engine | `radialLiquidEngine1-2` | 0.900 | 120.00 | 108.20 | 305 | 275 | 8.0 | Squad |
| LV-T91 "Cheetah" Liquid Fuel Engine | `LiquidEngineLV-T91` | 1.000 | 125.00 | 52.82 | 355 | 150 | 4.0 | MakingHistory |
| T-1 Toroidal Aerospike "Dart" Liquid Fuel Engine | `toroidalAerospike` | 1.000 | 180.00 | 153.53 | 340 | 290 | 0.0 | Squad |
| LV-T45 "Swivel" Liquid Fuel Engine | `liquidEngine2` | 1.500 | 215.00 | 167.97 | 320 | 250 | 3.0 | Squad |
| LV-T45 "Swivel" Liquid Fuel Engine | `liquidEngine2_v2` | 1.500 | 215.00 | 167.97 | 320 | 250 | 3.0 | Squad |
| LV-T30 "Reliant" Liquid Fuel Engine | `liquidEngine` | 1.250 | 240.00 | 205.16 | 310 | 265 | 0.0 | Squad |
| LV-T30 "Reliant" Liquid Fuel Engine | `liquidEngine_v2` | 1.250 | 240.00 | 205.16 | 310 | 265 | 0.0 | Squad |
| RE-L10 "Poodle" Liquid Fuel Engine | `liquidEngine2-2_v2` | 1.750 | 250.00 | 64.29 | 350 | 90 | 5.0 | Squad |
| RK-7 "Kodiak" Liquid Fueled Enine | `LiquidEngineRK-7` | 1.250 | 260.00 | 247.00 | 300 | 285 | 0.0 | MakingHistory |
| RE-I2 "Skiff" Liquid Fuel Engine | `LiquidEngineRE-I2` | 1.600 | 300.00 | 240.91 | 330 | 265 | 2.0 | MakingHistory |
| RE-J10 "Wolfhound"  Liquid Fuel Engine | `LiquidEngineRE-J10` | 3.300 | 375.00 | 69.08 | 380 | 70 | 3.0 | MakingHistory |
| LV-TX87 "Bobcat" Liquid Fuel Engine | `LiquidEngineLV-TX87` | 2.000 | 400.00 | 374.19 | 310 | 290 | 5.0 | MakingHistory |
| RE-I5 "Skipper" Liquid Fuel Engine | `engineLargeSkipper_v2` | 3.000 | 650.00 | 568.75 | 320 | 280 | 2.0 | Squad |
| S3 KS-25 "Vector" Liquid Fuel Engine | `SSME` | 4.000 | 1000.00 | 936.51 | 315 | 295 | 10.5 | Squad |
| Kerbodyne KE-1 "Mastodon" Liquid Fuel Engine | `LiquidEngineKE-1` | 5.000 | 1350.00 | 1283.61 | 305 | 290 | 5.0 | MakingHistory |
| RE-M3 "Mainsail" Liquid Fuel Engine | `liquidEngineMainsail_v2` | 6.000 | 1500.00 | 1379.03 | 310 | 285 | 2.0 | Squad |
| LFB KR-1x2 "Twin-Boar" Liquid Fuel Engine | `Size2LFB` | 10.500 | 2000.00 | 1866.67 | 300 | 280 | 1.5 | Squad |
| LFB KR-1x2 "Twin-Boar" Liquid Fuel Engine | `Size2LFB_v2` | 10.500 | 2000.00 | 1866.67 | 300 | 280 | 1.5 | Squad |
| Kerbodyne KR-2L+ "Rhino" Liquid Fuel Engine | `Size3AdvancedEngine` | 9.000 | 2000.00 | 1205.88 | 340 | 205 | 4.0 | Squad |
| S3 KS-25x4 "Mammoth" Liquid Fuel Engine | `Size3EngineCluster` | 15.000 | 4000.00 | 3746.03 | 315 | 295 | 2.0 | Squad |

## Solid Rocket Boosters

| Title | Internal Name | Mass Dry (t) | Mass Wet (t) | SolidFuel (u) | Thrust Vac (kN) | Thrust SL (kN) | Isp Vac (s) | Isp SL (s) | Pack |
|---|---|---|---|---|---|---|---|---|---|
| FM1 "Mite" Solid Fuel Booster | `Mite` | 0.075 | 0.375 | 40 | 12.50 | 11.01 | 210 | 185 | Squad |
| F3S0 "Shrimp" Solid Fuel Booster | `Shrimp` | 0.150 | 0.825 | 90 | 30.00 | 26.51 | 215 | 190 | Squad |
| RT-5 "Flea" Solid Fuel Booster | `solidBooster_sm_v2` | 0.450 | 1.500 | 140 | 192.00 | 162.91 | 165 | 140 | Squad |
| RT-10 "Hammer" Solid Fuel Booster | `solidBooster_v2` | 0.750 | 3.562 | 375 | 227.00 | 197.90 | 195 | 170 | Squad |
| BACC "Thumper" Solid Fuel Booster | `solidBooster1-1` | 1.500 | 7.650 | 820 | 300.00 | 250.00 | 210 | 175 | Squad |
| S1 SRB-KD25k "Kickback" Solid Fuel Booster | `MassiveBooster` | 4.500 | 24.000 | 2600 | 670.00 | 593.86 | 220 | 195 | Squad |
| Launch Escape System | `LaunchEscapeSystem` | 0.900 | 1.125 | 30 | 750.00 | 666.67 | 180 | 160 | Squad |
| THK "Pollux" Solid Fuel Booster | `Pollux` | 8.000 | 51.500 | 5800 | 1300.00 | 1155.56 | 225 | 200 | MakingHistory |
| S2-17 "Thoroughbred" Solid Fuel Booster | `Thoroughbred` | 10.000 | 70.000 | 8000 | 1700.00 | 1515.22 | 230 | 205 | Squad |
| S2-33 "Clydesdale" Solid Fuel Booster | `Clydesdale` | 21.000 | 144.000 | 16400 | 3300.00 | 2948.94 | 235 | 210 | Squad |

## Liquid Fuel + Oxidizer Tanks

| Title | Internal Name | Mass Dry (t) | Mass Wet (t) | LF (u) | OX (u) | Pack |
|---|---|---|---|---|---|---|
| R-4 'Dumpling' External Tank | `externalTankRound` | 0.0138 | 0.1237 | 10 | 12 | Squad |
| Oscar-B Fuel Tank | `miniFuelTank` | 0.0250 | 0.2250 | 18 | 22 | Squad |
| Mk0 Liquid Fuel Fuselage | `miniFuselage` | 0.0250 | 0.2750 | 50 | 0 | Squad |
| R-11 'Baguette' External Tank | `externalTankCapsule` | 0.0338 | 0.3038 | 24 | 30 | Squad |
| R-12 'Doughnut' External Tank | `externalTankToroid` | 0.0375 | 0.3375 | 27 | 33 | Squad |
| Engine Pre-cooler | `radialEngineBody` | 0.1500 | 0.3500 | 40 | 0 | Squad |
| NCS Adapter | `noseConeAdapter` | 0.1000 | 0.5000 | 80 | 0 | Squad |
| FL-T100 Fuel Tank | `fuelTankSmallFlat` | 0.0625 | 0.5625 | 45 | 55 | Squad |
| Engine Nacelle | `nacelleBody` | 0.1500 | 0.9000 | 150 | 0 | Squad |
| FL-A150 Fuel Tank Adapter | `Size1p5_Size0_Adapter_01` | 0.1000 | 0.9000 | 72 | 88 | MakingHistory |
| FL-A151S Fuel Tank Adapter | `Size1p5_Size1_Adapter_02` | 0.1000 | 0.9000 | 72 | 88 | MakingHistory |
| FL-T200 Fuel Tank | `fuelTankSmall` | 0.1250 | 1.1250 | 90 | 110 | Squad |
| Mk1 Diverterless Supersonic Intake | `MK1IntakeFuselage` | 0.1700 | 1.1700 | 200 | 0 | Squad |
| FL-TX220 Fuel Tank | `Size1p5_Tank_01` | 0.1375 | 1.2375 | 99 | 121 | MakingHistory |
| FL-T400 Fuel Tank | `fuelTank` | 0.2500 | 2.2500 | 180 | 220 | Squad |
| Mk1 Liquid Fuel Fuselage | `MK1Fuselage` | 0.2500 | 2.2500 | 400 | 0 | Squad |
| Mk2 Bicoupler | `mk2_1m_Bicoupler` | 0.2900 | 2.2900 | 180 | 220 | Squad |
| Mk2 to 1.25m Adapter | `mk2SpacePlaneAdapter` | 0.2900 | 2.2900 | 180 | 220 | Squad |
| Mk2 Liquid Fuel Fuselage Short | `mk2FuselageShortLiquid` | 0.2900 | 2.2900 | 400 | 0 | Squad |
| Mk2 Rocket Fuel Fuselage Short | `mk2FuselageShortLFO` | 0.2900 | 2.2900 | 180 | 220 | Squad |
| FL-TX440 Fuel Tank | `Size1p5_Tank_02` | 0.2750 | 2.4750 | 198 | 242 | MakingHistory |
| FL-A151L Fuel Tank Adapter | `Size1p5_Size1_Adapter_01` | 0.3750 | 3.3750 | 270 | 330 | MakingHistory |
| Rockomax X200-8 Fuel Tank | `Rockomax8BW` | 0.5000 | 4.5000 | 360 | 440 | Squad |
| FL-T800 Fuel Tank | `fuelTank_long` | 0.5000 | 4.5000 | 360 | 440 | Squad |
| 2.5m to Mk2 Adapter | `adapterSize2-Mk2` | 0.5700 | 4.5700 | 360 | 440 | Squad |
| C7 Brand Adapter - 2.5m to 1.25m | `adapterSize2-Size1` | 0.5700 | 4.5700 | 360 | 440 | Squad |
| C7 Brand Adapter Slanted - 2.5m to 1.25m | `adapterSize2-Size1Slant` | 0.5700 | 4.5700 | 360 | 440 | Squad |
| Mk2 to 1.25m Adapter Long | `mk2_1m_AdapterLong` | 0.5700 | 4.5700 | 360 | 440 | Squad |
| Mk2 Liquid Fuel Fuselage | `mk2Fuselage` | 0.5700 | 4.5700 | 800 | 0 | Squad |
| Mk2 Rocket Fuel Fuselage | `mk2FuselageLongLFO` | 0.5700 | 4.5700 | 360 | 440 | Squad |
| FL-TX900 Fuel Tank | `Size1p5_Tank_03` | 0.5625 | 5.0625 | 405 | 495 | MakingHistory |
| FL-A215 Fuel Tank Adapter | `Size1p5_Size2_Adapter_01` | 0.7500 | 6.7500 | 540 | 660 | MakingHistory |
| Rockomax X200-16 Fuel Tank | `Rockomax16_BW` | 1.0000 | 9.0000 | 720 | 880 | Squad |
| FL-TX1800 Fuel Tank | `Size1p5_Tank_04` | 1.1250 | 10.1250 | 810 | 990 | MakingHistory |
| Mk3 to Mk2 Adapter | `adapterMk3-Mk2` | 1.4300 | 11.4300 | 900 | 1100 | Squad |
| Mk3 to 2.5m Adapter | `adapterMk3-Size2` | 1.7900 | 14.2900 | 1125 | 1375 | Squad |
| Mk3 to 2.5m Adapter Slanted | `adapterMk3-Size2Slant` | 1.7900 | 14.2900 | 1125 | 1375 | Squad |
| Mk3 to 3.75m Adapter | `adapterSize3-Mk3` | 1.7900 | 14.2900 | 1125 | 1375 | Squad |
| Mk3 Liquid Fuel Fuselage Short | `mk3FuselageLF_25` | 1.7900 | 14.2900 | 2500 | 0 | Squad |
| Mk3 Rocket Fuel Fuselage Short | `mk3FuselageLFO_25` | 1.7900 | 14.2900 | 1125 | 1375 | Squad |
| Kerbodyne ADTP-2-3 | `Size3To2Adapter_v2` | 1.8750 | 16.8750 | 1350 | 1650 | Squad |
| Rockomax X200-32 Fuel Tank | `Rockomax32_BW` | 2.0000 | 18.0000 | 1440 | 1760 | Squad |
| Kerbodyne S3-3600 Tank | `Size3SmallTank` | 2.2500 | 20.2500 | 1620 | 1980 | Squad |
| Mk3 Liquid Fuel Fuselage | `mk3FuselageLF_50` | 3.5700 | 28.5700 | 5000 | 0 | Squad |
| Mk3 Rocket Fuel Fuselage | `mk3FuselageLFO_50` | 3.5700 | 28.5700 | 2250 | 2750 | Squad |
| Rockomax Jumbo-64 Fuel Tank | `Rockomax64_BW` | 4.0000 | 36.0000 | 2880 | 3520 | Squad |
| Kerbodyne S3-S4 Adapter Tank | `Size3_Size4_Adapter_01` | 4.0000 | 36.0000 | 2880 | 3520 | MakingHistory |
| Kerbodyne S4-64 Fuel Tank | `Size4_Tank_01` | 4.0000 | 36.0000 | 2880 | 3520 | MakingHistory |
| Kerbodyne S3-7200 Tank | `Size3MediumTank` | 4.5000 | 40.5000 | 3240 | 3960 | Squad |
| Kerbodyne Engine Cluster Adapter Tank | `Size4_EngineAdapter_01` | 5.6250 | 50.6250 | 4050 | 4950 | MakingHistory |
| Mk3 Liquid Fuel Fuselage Long | `mk3FuselageLF_100` | 7.1400 | 57.1400 | 10000 | 0 | Squad |
| Mk3 Rocket Fuel Fuselage Long | `mk3FuselageLFO_100` | 7.1400 | 57.1400 | 4500 | 5500 | Squad |
| Kerbodyne S4-128 Fuel Tank | `Size4_Tank_02` | 8.0000 | 72.0000 | 5760 | 7040 | MakingHistory |
| Kerbodyne S3-14400 Tank | `Size3LargeTank` | 9.0000 | 81.0000 | 6480 | 7920 | Squad |
| Kerbodyne S4-256 Fuel Tank | `Size4_Tank_03` | 16.0000 | 144.0000 | 11520 | 14080 | MakingHistory |
| Kerbodyne S4-512 Fuel Tank | `Size4_Tank_04` | 32.0000 | 288.0000 | 23040 | 28160 | MakingHistory |

## Decouplers and Separators

| Title | Internal Name | Mass (t) | Ejection Force (kN) | Pack |
|---|---|---|---|---|
| TD-06 Decoupler | `Decoupler_0` | 0.0100 | 50 | Squad |
| TS-06 Stack Separator | `Separator_0` | 0.0100 | 50 | Squad |
| Heat Shield (0.625m) | `HeatShield0` | 0.0250 | 50 | Squad |
| TT-38K Radial Decoupler | `radialDecoupler` | 0.0250 | 250 | Squad |
| TD-12 Decoupler | `Decoupler_1` | 0.0400 | 100 | Squad |
| TS-12 Stack Separator | `Separator_1` | 0.0500 | 100 | Squad |
| Small Hardpoint | `smallHardpoint` | 0.0500 | 60 | Squad |
| TT-70 Radial Decoupler | `radialDecoupler2` | 0.0500 | 260 | Squad |
| EP-12 Engine Plate | `EnginePlate5` | 0.0620 | 250 | MakingHistory |
| TD-18 Decoupler | `Decoupler_1p5` | 0.0900 | 125 | MakingHistory |
| Size 1.5 Decoupler | `Size1p5_Strut_Decoupler` | 0.0900 | 125 | MakingHistory |
| Heat Shield (1.25m) | `HeatShield1` | 0.1000 | 100 | Squad |
| TS-18 Stack Separator | `Separator_1p5` | 0.1200 | 125 | MakingHistory |
| EP-18 Engine Plate | `EnginePlate1p5` | 0.1400 | 250 | MakingHistory |
| TD-25 Decoupler | `Decoupler_2` | 0.1600 | 150 | Squad |
| Structural Pylon | `structuralPylon` | 0.2000 | 250 | Squad |
| TS-25 Stack Separator | `Separator_2` | 0.2100 | 150 | Squad |
| EP-25 Engine Plate | `EnginePlate2` | 0.2500 | 250 | MakingHistory |
| Heat Shield (1.875m) | `HeatShield1p5` | 0.3000 | 100 | MakingHistory |
| TD-37 Decoupler | `Decoupler_3` | 0.3600 | 200 | Squad |
| Hydraulic Detachment Manifold | `radialDecoupler1-2` | 0.4000 | 450 | Squad |
| TS-37 Stack Separator | `Separator_3` | 0.4800 | 200 | Squad |
| Heat Shield (2.5m) | `HeatShield2` | 0.5000 | 100 | Squad |
| EP-37 Engine Plate | `EnginePlate3` | 0.5800 | 250 | MakingHistory |
| TD-50 Decoupler | `Decoupler_4` | 0.6400 | 250 | MakingHistory |
| KV-1 'Onion' Reentry Module | `kv1Pod` | 0.7500 | 10 | MakingHistory |
| TS-50 Stack Separator | `Separator_4` | 0.8500 | 250 | MakingHistory |
| Heat Shield (3.75m) | `HeatShield3` | 1.0000 | 100 | Squad |
| EP-50 Engine Plate | `EnginePlate4` | 1.0000 | 250 | MakingHistory |
| Heat Shield (10m) | `InflatableHeatShield` | 1.5000 | 100 | Squad |
| KV-2 'Onion' Reentry Module | `kv2Pod` | 1.5000 | 10 | MakingHistory |
| KV-3 'Tato' Reentry Module | `kv3Pod` | 2.2500 | 10 | MakingHistory |

## Command Modules

| Title | Internal Name | Mass (t) | Pack |
|---|---|---|---|
| Mk2 Lander Can | `mk2LanderCabin_v2` | 0.0000 | Squad |
| Probodobodyne OKTO2 | `probeCoreOcto2_v2` | 0.0400 | Squad |
| Probodobodyne Stayputnik | `probeCoreSphere_v2` | 0.0500 | Squad |
| Probodobodyne QBE | `probeCoreCube` | 0.0700 | Squad |
| Probodobodyne HECS | `probeCoreHex` | 0.1000 | Squad |
| Probodobodyne HECS | `probeCoreHex_v2` | 0.1000 | Squad |
| Probodobodyne OKTO | `probeCoreOcto_v2` | 0.1000 | Squad |
| RC-001S Remote Guidance Unit | `probeStackSmall` | 0.1000 | Squad |
| Probodobodyne RoveMate | `roverBody` | 0.1500 | Squad |
| Probodobodyne RoveMate | `roverBody_v2` | 0.1500 | Squad |
| MK2 Drone Core | `mk2DroneCore` | 0.2000 | Squad |
| Probodobodyne HECS2 | `HECS2_ProbeCore` | 0.2000 | Squad |
| MPO Probe | `MpoProbe` | 0.3950 | Squad |
| MTM Stage | `MtmStage` | 0.4150 | Squad |
| RC-L01 Remote Guidance Unit | `probeStackLarge` | 0.5000 | Squad |
| Mk1 Lander Can | `landerCabinSmall` | 0.6000 | Squad |
| Mk1 Command Pod | `mk1pod_v2` | 0.8000 | Squad |
| PPD-12 Cupola Module | `cupola` | 0.9400 | Squad |
| Mk1 Inline Cockpit | `Mark2Cockpit` | 1.0000 | Squad |
| Mk1 Cockpit | `Mark1Cockpit` | 1.2500 | Squad |
| Munar Excursion Module (M.E.M.) | `MEMLander` | 1.3550 | MakingHistory |
| Mk2 Command Pod | `Mk2Pod` | 1.5600 | MakingHistory |
| Mk2 Inline Cockpit | `mk2Cockpit_Inline` | 2.0000 | Squad |
| Mk2 Cockpit | `mk2Cockpit_Standard` | 2.0000 | Squad |
| Mk2 Lander Can | `mk2LanderCabin` | 2.5000 | Squad |
| Mk1-3 Command Pod | `mk1-3pod` | 2.6000 | Squad |
| Mk3 Cockpit | `mk3Cockpit_Shuttle` | 3.5000 | Squad |

## Parachutes

| Title | Internal Name | Mass (t) | Pack |
|---|---|---|---|
| Mk12-R Radial-Mount Drogue Chute | `radialDrogue` | 0.0750 | Squad |
| Mk16 Parachute | `parachuteSingle` | 0.1000 | Squad |
| Mk2-R Radial-Mount Parachute | `parachuteRadial` | 0.1000 | Squad |
| Mk25 Parachute | `parachuteDrogue` | 0.2000 | Squad |
| Mk16-XL Parachute | `parachuteLarge` | 0.3000 | Squad |

## MonoPropellant Tanks

| Title | Internal Name | Mass Dry (t) | Mass Wet (t) | MonoProp (u) | Pack |
|---|---|---|---|---|---|
| Stratus-V Minified Monopropellant Tank | `monopropMiniSphere` | 0.0100 | 0.0400 | 8 | MakingHistory |
| FL-R20 RCS Fuel Tank | `rcsTankMini` | 0.0200 | 0.1000 | 20 | Squad |
| Stratus-V Roundified Monopropellant Tank | `radialRCSTank` | 0.0200 | 0.1000 | 20 | Squad |
| Stratus-V Cylindrified Monopropellant Tank | `rcsTankRadialLong` | 0.0300 | 0.2300 | 50 | Squad |
| FL-R120 RCS Fuel Tank | `RCSFuelTank` | 0.0800 | 0.5600 | 120 | Squad |
| FL-R400 RCS Fuel Tank | `Size1p5_Monoprop` | 0.2500 | 1.8500 | 400 | MakingHistory |
| Mk2 Monopropellant Tank | `mk2FuselageShortMono` | 0.2900 | 1.8900 | 400 | Squad |
| Mk2 Clamp-O-Tron | `mk2DockingPort` | 0.3000 | 0.6000 | 75 | Squad |
| FL-R750 RCS Fuel Tank | `RCSTank1-2` | 0.4000 | 3.4000 | 750 | Squad |
| Mk3 Monopropellant Tank | `mk3FuselageMONO` | 1.4000 | 9.8000 | 2100 | Squad |

## RCS Thrusters

| Title | Internal Name | Mass (t) | Thrust (kN) | Pack |
|---|---|---|---|---|
| Place Anywhere 1 Linear RCS Port | `RCSLinearSmall` | 0.0013 | 0.200 | Squad |
| RV-1X Variable Thruster Block | `RCSblock_01_small` | 0.0050 | 0.100 | Squad |
| Place-Anywhere 7 Linear RCS Port | `linearRcs` | 0.0200 | 2.000 | Squad |
| RV-105 RCS Thruster Block | `RCSBlock_v2` | 0.0400 | 1.000 | Squad |
| Vernor Engine | `vernierEngine` | 0.0800 | 12.000 | Squad |
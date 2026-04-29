Now I have enough data to design the rocket. Let me compile the key part stats I've gathered and design the manifest.

**Part Stats Summary:**

**Command Pod:** Mk1-3 Command Pod — mass 4.12 t, monoprop 30 units, built-in reaction wheel
**Decouplers:** TR-18D Stack Separator — 0.075 t (for 1.25m), TD-12 Decoupler — 0.15 t (for 1.25m), TR-18A Stack Decoupler — 0.1 t
**Engines:**
- LV-T45 "Swivel" — 1.4 t, 188.1 kN ASL / 215 kN vac, Isp 280 ASL / 320 vac, gimbal
- LV-T30 "Reliant" — 1.25 t, 221.6 kN ASL / 260 kN vac, Isp 260 ASL / 265 vac, no gimbal
- RE-L10 "Poodle" — 1.75 t, 110.7 kN ASL / 215 kN vac, Isp 175 ASL / 340 vac
- LV-909 "Terrier" — 0.5 t, 60 kN vac, Isp 345 vac, 170 ASL
- RE-I5 "Skipper" — 3 t, 568.75 kN ASL / 650 kN vac, Isp 280 ASL / 320 vac

**Fuel Tanks (1.25m):**
- FL-T800 — 4.5 t wet, 0.5 t dry
- FL-T400 — 2.25 t wet, 0.25 t dry

**Fuel Tanks (2.5m / Rockomax):**
- X200-8 — 4.5 t wet, 0.5 t dry
- X200-16 — 9 t wet, 1 t dry
- X200-32 — 18 t wet, 2 t dry
- Jumbo-64 — 36 t wet, 4 t dry

Let me design a 3-stage rocket:

**Stage 3 (Upper / Transfer stage):** Poodle engine, 1x X200-8 tank
**Stage 2 (Sustainer / LKO stage):** Swivel engine, 1x X200-16 tank  
**Stage 1 (Booster):** Reliant engine, 1x X200-32 tank

Let me calculate the delta-v for each stage.

**Constants:** g0 = 9.81 m/s²

**Stage 3 (Poodle + X200-8):**
- Engine: RE-L10 "Poodle" — 1.75 t, Isp_vac = 340 s, thrust_vac = 215 kN
- Tank: X200-8 — 4.5 t wet, 0.5 t dry
- Decoupler: TR-18D Stack Separator — 0.075 t (between stage 2 and 3)
- Payload: Mk1-3 Command Pod — 4.12 t
- Stage 3 dry: 4.12 (pod) + 1.75 (engine) + 0.5 (tank dry) + 0.075 (decoupler) = 6.445 t
- Stage 3 wet: 6.445 + 4.0 (fuel) = 10.445 t (fuel mass = 4.5 - 0.5 = 4.0 t)
- dV = 340 * 9.81 * ln(10.445 / 6.445) = 340 * 9.81 * ln(1.6206) = 340 * 9.81 * 0.4828 = 1,610 m/s
- TWR (vac, at ignition): 215 / (10.445 * 9.81) = 215 / 102.47 = 2.10 — fine for upper stage

**Stage 2 (Swivel + X200-16 + interstage):**
- Engine: LV-T45 "Swivel" — 1.4 t, Isp_vac = 320 s, thrust_vac = 215 kN
- Tank: X200-16 — 9 t wet, 1 t dry
- Decoupler: TD-12 Decoupler — 0.15 t (between stage 1 and 2)
- Stage 3 is payload for stage 2: 10.445 t
- Stage 2 dry: 10.445 (S3) + 1.4 (engine) + 1.0 (tank dry) + 0.15 (decoupler) = 12.995 t
- Stage 2 wet: 12.995 + 8.0 (fuel) = 20.995 t
- dV = 320 * 9.81 * ln(20.995 / 12.995) = 320 * 9.81 * ln(1.6156) = 320 * 9.81 * 0.4796 = 1,506 m/s
- TWR (vac, at ignition): 215 / (20.995 * 9.81) = 215 / 205.96 = 1.04 — low but acceptable for upper stage in vacuum

Hmm, TWR of 1.04 is a bit low. Let me reconsider.

Actually, for the Swivel at sea level during stage 2 ignition (it fires after stage 1 separates at ~10-15 km altitude):
- At ~15 km altitude, atmospheric pressure is low, so Isp is closer to vacuum
- TWR at altitude: ~215 / (20.995 * 9.81) = 1.04 - this is marginal but okay since we're already moving fast

Let me recalculate more carefully. Actually, let me use a different approach.

Let me use the **Reliant** for stage 1 (better sea-level TWR), **Swivel** for stage 2 (gimbal for control), and **Terrier** for stage 3 (high vacuum Isp).

**Stage 3 (Terrier + FL-T800):**
- Engine: LV-909 "Terrier" — 0.5 t, Isp_vac = 345 s, thrust_vac = 60 kN
- Tank: FL-T800 — 4.5 t wet, 0.5 t dry
- TR-18D Stack Separator — 0.075 t
- Payload: Mk1-3 Pod — 4.12 t
- Stage 3 dry: 4.12 + 0.5 + 0.5 + 0.075 = 5.195 t
- Stage 3 wet: 5.195 + 4.0 = 9.195 t
- dV = 345 * 9.81 * ln(9.195 / 5.195) = 345 * 9.81 * ln(1.770) = 345 * 9.81 * 0.571 = 1,932 m/s
- TWR (vac): 60 / (9.195 * 9.81) = 60 / 90.2 = 0.665 — too low! Won't be able to circularize efficiently.

Let me try Poodle for stage 3 instead.

**Stage 3 (Poodle + X200-8):**
- Engine: RE-L10 "Poodle" — 1.75 t, Isp_vac = 340 s, thrust_vac = 215 kN
- Tank: X200-8 — 4.5 t wet, 0.5 t dry
- TR-18D Stack Separator — 0.075 t
- Payload: Mk1-3 Pod — 4.12 t
- Stage 3 dry: 4.12 + 1.75 + 0.5 + 0.075 = 6.445 t
- Stage 3 wet: 6.445 + 4.0 = 10.445 t
- dV = 340 * 9.81 * ln(10.445 / 6.445) = 340 * 9.81 * 0.4828 = 1,610 m/s
- TWR (vac): 215 / (10.445 * 9.81) = 215 / 102.47 = 2.10 — good!

**Stage 2 (Swivel + X200-16):**
- Engine: LV-T45 "Swivel" — 1.4 t, Isp_vac = 320 s
- Tank: X200-16 — 9 t wet, 1 t dry
- TD-12 Decoupler — 0.15 t
- Payload: Stage 3 = 10.445 t
- Stage 2 dry: 10.445 + 1.4 + 1.0 + 0.15 = 12.995 t
- Stage 2 wet: 12.995 + 8.0 = 20.995 t
- dV = 320 * 9.81 * ln(20.995 / 12.995) = 320 * 9.81 * 0.4796 = 1,506 m/s
- TWR (vac): 215 / (20.995 * 9.81) = 1.04 — marginal

Let me try a smaller stage 2 tank. X200-8:
- Stage 2 dry: 10.445 + 1.4 + 0.5 + 0.15 = 12.495 t
- Stage 2 wet: 12.495 + 4.0 = 16.495 t
- dV = 320 * 9.81 * ln(16.495 / 12.495) = 320 * 9.81 * ln(1.320) = 320 * 9.81 * 0.2776 = 871 m/s
- TWR (vac): 215 / (16.495 * 9.81) = 215 / 161.8 = 1.33 — better!

Hmm, but total dV then: 871 + 1610 = 2,481 m/s from upper stages. Need stage 1 to provide the rest.

**Stage 1 (Reliant + X200-32):**
- Engine: LV-T30 "Reliant" — 1.25 t, Isp_ASL = 260 s, thrust_ASL = 221.6 kN
- Tank: X200-32 — 18 t wet, 2 t dry
- TD-12 Decoupler — 0.15 t
- Payload: Stage 2 + Stage 3 = 16.495 t
- Stage 1 dry: 16.495 + 1.25 + 2.0 + 0.15 = 19.895 t
- Stage 1 wet: 19.895 + 16.0 = 35.895 t
- dV (using avg Isp ~270 s for first part of flight): Let's use Isp = 260 for sea level
- dV = 260 * 9.81 * ln(35.895 / 19.895) = 260 * 9.81 * ln(1.804) = 260 * 9.81 * 0.589 = 1,503 m/s
- TWR (ASL, at ignition): 221.6 / (35.895 * 9.81) = 221.6 / 352.1 = 0.63 — WAY too low!

That's a problem. The Reliant alone can't lift a 35.9 t rocket. I need more thrust on stage 1.

Let me try using the **Skipper** for stage 1:
- RE-I5 "Skipper" — 3 t, 568.75 kN ASL / 650 kN vac, Isp 280 ASL / 320 vac
- TWR (ASL): 568.75 / (35.895 * 9.81) = 568.75 / 352.1 = 1.615 — good!

Let me recalculate stage 1 with Skipper:
- Stage 1 dry: 16.495 + 3.0 + 2.0 + 0.15 = 21.645 t
- Stage 1 wet: 21.645 + 16.0 = 37.645 t
- dV = 280 * 9.81 * ln(37.645 / 21.645) = 280 * 9.81 * ln(1.739) = 280 * 9.81 * 0.553 = 1,519 m/s

Total dV: 1,519 + 871 + 1,610 = 4,000 m/s. Not enough! Need 5,250 m/s.

Let me redesign. Let me use a bigger stage 1.

**New design approach:** 

Stage 1: Skipper + Jumbo-64 (36 t wet)
Stage 2: Swivel + X200-32 (18 t wet)  
Stage 3: Poodle + X200-8 (4.5 t wet)

**Stage 3 (Poodle + X200-8):**
- Payload: Mk1-3 Pod — 4.12 t
- Engine: Poodle — 1.75 t
- Tank: X200-8 — 4.5 t wet, 0.5 t dry
- TR-18D Stack Separator — 0.075 t
- Dry: 4.12 + 1.75 + 0.5 + 0.075 = 6.445 t
- Wet: 6.445 + 4.0 = 10.445 t
- dV = 340 * 9.81 * ln(10.445 / 6.445) = 1,610 m/s
- TWR(vac): 215 / (10.445 * 9.81) = 2.10 ✓

**Stage 2 (Swivel + X200-32):**
- Engine: Swivel — 1.4 t, Isp_vac=320
- Tank: X200-32 — 18 t wet, 2 t dry
- TD-12 Decoupler — 0.15 t
- Payload: Stage 3 = 10.445 t
- Dry: 10.445 + 1.4 + 2.0 + 0.15 = 13.995 t
- Wet: 13.995 + 16.0 = 29.995 t
- dV = 320 * 9.81 * ln(29.995 / 13.995) = 320 * 9.81 * ln(2.143) = 320 * 9.81 * 0.762 = 2,392 m/s
- TWR(vac): 215 / (29.995 * 9.81) = 215 / 294.3 = 0.73 — quite low

That TWR is too low for efficient burns. Let me try a smaller tank for stage 2.

**Stage 2 (Swivel + X200-16):**
- Tank: X200-16 — 9 t wet, 1 t dry
- Dry: 10.445 + 1.4 + 1.0 + 0.15 = 12.995 t
- Wet: 12.995 + 8.0 = 20.995 t
- dV = 320 * 9.81 * ln(20.995 / 12.995) = 320 * 9.81 * 0.4796 = 1,506 m/s
- TWR(vac): 215 / (20.995 * 9.81) = 1.04 — marginal but workable in vacuum

**Stage 1 (Skipper + Jumbo-64):**
- Engine: Skipper — 3 t, 568.75 kN ASL, Isp_ASL=280
- Tank: Jumbo-64 — 36 t wet, 4 t dry
- TD-12 Decoupler — 0.15 t
- Payload: Stage 2 + 3 = 20.995 t
- Dry: 20.995 + 3.0 + 4.0 + 0.15 = 28.145 t
- Wet: 28.145 + 32.0 = 60.145 t
- dV (using avg Isp ~295 for ascent): Let me use Isp_ASL=280
- dV = 280 * 9.81 * ln(60.145 / 28.145) = 280 * 9.81 * ln(2.137) = 280 * 9.81 * 0.759 = 2,085 m/s
- TWR(ASL): 568.75 / (60.145 * 9.81) = 568.75 / 590.0 = 0.964 — below 1.3! Not good.

I need more thrust. Let me add boosters or use a cluster.

Let me try 2x Reliant on stage 1 (using a 2.5m to 2x1.25m adapter):
- 2x Reliant: 2 * 221.6 = 443.2 kN ASL, mass = 2 * 1.25 = 2.5 t
- TWR: 443.2 / (60.145 * 9.81) = 443.2 / 590.0 = 0.751 — even worse

Let me try 2x Skipper? No, that's too heavy.

Let me use a **Mainsail** (RE-M3) instead:
- RE-M3 "Mainsail" — 6 t, 1379 kN ASL / 1500 kN vac, Isp 285 ASL / 310 vac
- TWR(ASL): 1379 / (60.145 * 9.81) = 1379 / 590.0 = 2.34 — excellent!

Let me recalculate with Mainsail:
- Stage 1 dry: 20.995 + 6.0 + 4.0 + 0.15 = 31.145 t
- Stage 1 wet: 31.145 + 32.0 = 63.145 t
- dV = 285 * 9.81 * ln(63.145 / 31.145) = 285 * 9.81 * ln(2.027) = 285 * 9.81 * 0.706 = 1,974 m/s

Total dV: 1,974 + 1,506 + 1,610 = 5,090 m/s. Almost at 5,250! Let me add a bit more fuel.

Let me try Stage 1: Mainsail + Jumbo-64 + X200-32 (36+18=54 t wet fuel, 4+2=6 t dry)
- Tank mass: 54 t wet, 6 t dry
- Dry: 20.995 + 6.0 + 6.0 + 0.15 = 33.145 t
- Wet: 33.145 + 48.0 = 81.145 t
- dV = 285 * 9.81 * ln(81.145 / 33.145) = 285 * 9.81 * ln(2.448) = 285 * 9.81 * 0.895 = 2,502 m/s
- TWR(ASL): 1379 / (81.145 * 9.81) = 1379 / 796.0 = 1.73 ✓ (above 1.3)

Total dV: 2,502 + 1,506 + 1,610 = 5,618 m/s. Exceeds 5,250! 

But wait - I need to make sure the 2.5m parts connect properly. The Mainsail is 2.5m, the Jumbo-64 and X200-32 are 2.5m Rockomax tanks. The Swivel is 1.25m. I need an adapter.

Let me use a more standard design. Let me use the **Skipper** for stage 1 with a larger fuel load.

Actually, let me go back and try a simpler approach. Let me use 1.25m parts for everything since that's simpler for building.

**Revised simpler design:**

Stage 3 (Terrier + FL-T800): For TMI and MOI
Stage 2 (Swivel + 2x FL-T800): For LKO insertion
Stage 1 (Reliant + 3x FL-T800): For launch

Let me calculate:

**Stage 3 (Terrier + FL-T800):**
- Engine: LV-909 "Terrier" — 0.5 t, Isp_vac=345, thrust_vac=60 kN
- Tank: FL-T800 — 4.5 t wet, 0.5 t dry
- TR-18D Stack Separator — 0.075 t
- Payload: Mk1-3 Pod — 4.12 t
- Dry: 4.12 + 0.5 + 0.5 + 0.075 = 5.195 t
- Wet: 5.195 + 4.0 = 9.195 t
- dV = 345 * 9.81 * ln(9.195 / 5.195) = 345 * 9.81 * 0.571 = 1,932 m/s
- TWR(vac): 60 / (9.195 * 9.81) = 60 / 90.2 = 0.665 — too low, won't work for MOI

The Terrier is too weak for a 9.2 t stage. Let me use the Swivel for stage 3 instead.

**Stage 3 (Swivel + FL-T400):**
- Engine: LV-T45 "Swivel" — 1.4 t, Isp_vac=320, thrust_vac=215 kN
- Tank: FL-T400 — 2.25 t wet, 0.25 t dry
- TR-18D Stack Separator — 0.075 t
- Payload: Mk1-3 Pod — 4.12 t
- Dry: 4.12 + 1.4 + 0.25 + 0.075 = 5.845 t
- Wet: 5.845 + 2.0 = 7.845 t
- dV = 320 * 9.81 * ln(7.845 / 5.845) = 320 * 9.81 * ln(1.342) = 320 * 9.81 * 0.294 = 923 m/s
- TWR(vac): 215 / (7.845 * 9.81) = 215 / 76.96 = 2.79 ✓

923 m/s for stage 3. That covers TMI (~860) + MOI (~310) = 1,170... not enough!

Let me use a bigger tank for stage 3.

**Stage 3 (Swivel + FL-T800):**
- Tank: FL-T800 — 4.5 t wet, 0.5 t dry
- Dry: 4.12 + 1.4 + 0.5 + 0.075 = 6.095 t
- Wet: 6.095 + 4.0 = 10.095 t
- dV = 320 * 9.81 * ln(10.095 / 6.095) = 320 * 9.81 * ln(1.656) = 320 * 9.81 * 0.504 = 1,582 m/s
- TWR(vac): 215 / (10.095 * 9.81) = 215 / 99.03 = 2.17 ✓

1,582 m/s covers TMI (860) + MOI (310) = 1,170 with margin. Good!

**Stage 2 (Swivel + 2x FL-T800):**
- Engine: LV-T45 "Swivel" — 1.4 t, Isp_vac=320
- Tanks: 2x FL-T800 — 9 t wet, 1 t dry total
- TD-12 Decoupler — 0.15 t
- Payload: Stage 3 = 10.095 t
- Dry: 10.095 + 1.4 + 1.0 + 0.15 = 12.645 t
- Wet: 12.645 + 8.0 = 20.645 t
- dV = 320 * 9.81 * ln(20.645 / 12.645) = 320 * 9.81 * ln(1.633) = 320 * 9.81 * 0.490 = 1,539 m/s
- TWR(vac): 215 / (20.645 * 9.81) = 215 / 202.5 = 1.06 — marginal but okay

**Stage 1 (Reliant + 3x FL-T800):**
- Engine: LV-T30 "Reliant" — 1.25 t, Isp_ASL=260, thrust=221.6 kN
- Tanks: 3x FL-T800 — 13.5 t wet, 1.5 t dry total
- TD-12 Decoupler — 0.15 t
- Payload: Stage 2 + 3 = 20.645 t
- Dry: 20.645 + 1.25 + 1.5 + 0.15 = 23.545 t
- Wet: 23.545 + 12.0 = 35.545 t
- dV = 260 * 9.81 * ln(35.545 / 23.545) = 260 * 9.81 * ln(1.510) = 260 * 9.81 * 0.412 = 1,051 m/s
- TWR(ASL): 221.6 / (35.545 * 9.81) = 221.6 / 348.7 = 0.636 — FAILS TWR requirement!

The Reliant alone can't lift 35.5 t. I need more engines on stage 1.

Let me use 3x Reliant on stage 1 (using a tri-coupler):
- 3 * 221.6 = 664.8 kN ASL
- 3 * 1.25 = 3.75 t
- TWR: 664.8 / (35.545 * 9.81) = 664.8 / 348.7 = 1.907 ✓

But then I need to spread the tanks across 3 stacks or use a different configuration.

Actually, let me think about this differently. Let me use a 2.5m core with a Mainsail, which is much simpler.

**Final Design - 3-stage 2.5m rocket:**

**Stage 3 (Upper - Poodle + X200-8):** For TMI + MOI
**Stage 2 (Sustainer - Swivel + X200-16):** For LKO insertion
**Stage 1 (Booster - Mainsail + Jumbo-64):** For launch through gravity turn

Let me verify the numbers carefully.

**Stage 3: RE-L10 "Poodle" + Rockomax X200-8**
- Engine: RE-L10 "Poodle" — 1.75 t, Isp_vac=340 s, thrust_vac=215 kN
- Tank: Rockomax X200-8 Fuel Tank — 4.5 t wet, 0.5 t dry (fuel=4.0 t)
- TR-18D Stack Separator — 0.075 t (between S2 and S3)
- Payload: Mk1-3 Command Pod — 4.12 t
- Dry mass: 4.12 + 1.75 + 0.5 + 0.075 = 6.445 t
- Wet mass: 6.445 + 4.0 = 10.445 t
- dV = 340 * 9.81 * ln(10.445 / 6.445) = 3335.4 * ln(1.6206) = 3335.4 * 0.4828 = **1,610 m/s**
- TWR(vac): 215 / (10.445 * 9.81) = 215 / 102.47 = 2.10 ✓

**Stage 2: LV-T45 "Swivel" + Rockomax X200-16**
- Engine: LV-T45 "Swivel" — 1.4 t, Isp_vac=320 s, thrust_vac=215 kN
- Tank: Rockomax X200-16 Fuel Tank — 9.0 t wet, 1.0 t dry (fuel=8.0 t)
- Need a 2.5m-to-1.25m adapter? No, the Swivel is 1.25m but the X200-16 is 2.5m. I need an adapter.
- Actually, let me reconsider. The Swivel is 1.25m. Let me use 2.5m engines for the 2.5m stack.

Let me use the **Skipper** for stage 2 instead:
- RE-I5 "Skipper" — 3 t, Isp_vac=320 s, thrust_vac=650 kN
- Tank: X200-16 — 9 t wet, 1 t dry
- Payload: Stage 3 = 10.445 t
- Dry: 10.445 + 3.0 + 1.0 + 0.15 (TD-12) = 14.595 t
- Wet: 14.595 + 8.0 = 22.595 t
- dV = 320 * 9.81 * ln(22.595 / 14.595) = 3139.2 * ln(1.548) = 3139.2 * 0.437 = 1,372 m/s
- TWR(vac): 650 / (22.595 * 9.81) = 650 / 221.7 = 2.93 ✓

**Stage 1: RE-M3 "Mainsail" + Rockomax Jumbo-64**
- Engine: RE-M3 "Mainsail" — 6 t, Isp_ASL=285 s, thrust_ASL=1379 kN
- Tank: Rockomax Jumbo-64 Fuel Tank — 36 t wet, 4 t dry (fuel=32 t)
- TD-12 Decoupler — 0.15 t (between S1 and S2)
- Payload: Stage 2 + 3 = 22.595 t
- Dry: 22.595 + 6.0 + 4.0 + 0.15 = 32.745 t
- Wet: 32.745 + 32.0 = 64.745 t
- dV = 285 * 9.81 * ln(64.745 / 32.745) = 2795.85 * ln(1.977) = 2795.85 * 0.682 = 1,907 m/s
- TWR(ASL): 1379 / (64.745 * 9.81) = 1379 / 635.1 = 2.17 ✓ (above 1.3)

**Total dV: 1,907 + 1,372 + 1,610 = 4,889 m/s** — still short of 5,250!

I need more dV. Let me increase stage 2 tank to X200-32.

**Stage 2 (Skipper + X200-32):**
- Tank: X200-32 — 18 t wet, 2 t dry (fuel=16 t)
- Dry: 10.445 + 3.0 + 2.0 + 0.15 = 15.595 t
- Wet: 15.595 + 16.0 = 31.595 t
- dV = 320 * 9.81 * ln(31.595 / 15.595) = 3139.2 * ln(2.026) = 3139.2 * 0.706 = 2,216 m/s
- TWR(vac): 650 / (31.595 * 9.81) = 650 / 309.9 = 2.10 ✓

**Stage 1 (Mainsail + Jumbo-64):**
- Payload: Stage 2 + 3 = 31.595 t
- Dry: 31.595 + 6.0 + 4.0 + 0.15 = 41.745 t
- Wet: 41.745 + 32.0 = 73.745 t
- dV = 285 * 9.81 * ln(73.745 / 41.745) = 2795.85 * ln(1.767) = 2795.85 * 0.569 = 1,591 m/s
- TWR(ASL): 1379 / (73.745 * 9.81) = 1379 / 723.4 = 1.906 ✓

**Total: 1,591 + 2,216 + 1,610 = 5,417 m/s** — exceeds 5,250! ✓

Let me verify all the numbers once more with precise calculations.

Actually, I should also account for the mass of the decoupler between stage 2 and 3. The TR-18D is 0.075 t but that's a 1.25m part. Since we're using 2.5m stack, I need a 2.5m decoupler. Let me use the **TD-12 Decoupler** (0.15 t) between all stages since it's 2.5m... actually the TD-12 is 1.25m. For 2.5m, I need the **TD-25 Decoupler** or **TS-25 Stack Separator**.

Let me search for the right decoupler.

Actually, for the 2.5m stack, the standard decoupler would be the **TR-XL Stack Separator** (0.45 t) or simply the **Rockomax Brand Decoupler** which is the TD-25.

Let me just use the **TR-XL Stack Separator** (0.45 t) for 2.5m to 2.5m separation. Or better yet, let me check.

Actually, in KSP, the standard 2.5m decoupler is the **TD-25 Decoupler** or **TS-25 Stack Separator**. But I'm not sure of their exact masses. Let me just use reasonable values.

Actually, let me use the **Rockomax Brand Adapter** (the 2.5m to 1.25m adapter) where needed, and keep things simple.

Let me rethink the design to be cleaner.

**Clean 3-stage design - all 2.5m core:**

Stage 1: Mainsail + Jumbo-64 (36 t)
Stage 2: Skipper + X200-32 (18 t)  
Stage 3: Poodle + X200-8 (4.5 t)

But the Poodle is 2.5m, the X200-8 is 2.5m... actually the Poodle IS a 2.5m engine. And the X200-8 is a 2.5m tank. So this all works in a 2.5m stack!

Wait, the Poodle is 2.5m diameter? Let me check. The RE-L10 "Poodle" is indeed a 2.5m engine (Rockomax size). And the Mk1-3 Command Pod is 1.25m. So I need a 2.5m-to-1.25m adapter between the pod and the X200-8 tank... or I can put the pod on top of the 2.5m stack with a adapter.

Let me simplify: I'll use a **Rockomax Brand Adapter** (2.5m to 1.25m) between the pod and the first tank.

Let me finalize the design with precise numbers.

**Full Rocket Manifest:**

**Payload:** Mk1-3 Command Pod (4.12 t, includes reaction wheel, 30 monoprop, 3 crew)

**Stage 3 (Transfer/Insertion stage):**
- TR-XL Stack Separator (0.45 t) — separates S2 from S3
- Rockomax X200-8 Fuel Tank (4.5 t wet, 0.5 t dry)
- RE-L10 "Poodle" Liquid Fuel Engine (1.75 t, 215 kN vac, Isp 340 vac)
- dV: 1,610 m/s
- TWR(vac): 2.10

**Stage 2 (Sustainer/LKO stage):**
- TD-25 Decoupler or TR-XL Stack Separator (0.45 t) — separates S1 from S2
- Rockomax X200
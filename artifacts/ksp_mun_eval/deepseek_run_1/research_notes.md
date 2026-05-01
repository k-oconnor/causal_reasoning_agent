# Research Notes — Attempt 1

## Rocket Design Calculations

### Part stats (from reference)

**Engines:**
- LV-T45 "Swivel": mass 1.5 t, thrust vac 215 kN, thrust SL 167.97 kN, Isp vac 320 s, Isp SL 250 s
- LV-909 "Terrier": mass 0.5 t, thrust vac 60 kN, thrust SL 14.78 kN, Isp vac 345 s, Isp SL 85 s
- 48-7S "Spark": mass 0.13 t, thrust vac 20 kN, thrust SL 16.56 kN, Isp vac 320 s, Isp SL 265 s

**Tanks:**
- FL-T800: dry 0.5 t, wet 4.5 t, 360 LF + 440 OX
- FL-T400: dry 0.25 t, wet 2.25 t, 180 LF + 220 OX
- FL-T200: dry 0.125 t, wet 1.125 t, 90 LF + 110 OX
- FL-T100: dry 0.0625 t, wet 0.5625 t, 45 LF + 55 OX

**Decouplers:**
- TD-25 (2.5m): 0.16 t
- TD-12 (1.25m): 0.04 t

**Command:**
- Mk1 Command Pod: 0.8 t

**dV formula:** dV = Isp * 9.82 * ln(m0/mf)

### Stage 3 (top) — Spark + FL-T200
- Payload: Mk1 Command Pod (0.8 t) + Mk16 Parachute (0.1 t) = 0.9 t
- Engine: Spark (0.13 t)
- Tank: FL-T200 (1.125 t wet, 0.125 t dry)
- Decoupler: TD-12 (0.04 t) — separates stage 2
- m0 = 0.9 + 0.13 + 1.125 + 0.04 = 2.195 t
- mf = 0.9 + 0.13 + 0.125 + 0.04 = 1.195 t
- dV = 320 * 9.82 * ln(2.195/1.195) = 320 * 9.82 * 0.609 = 1,913 m/s

### Stage 2 (middle) — Terrier + FL-T400
- Carries stage 3 as payload
- Payload = stage 3 wet mass = 2.195 t
- Engine: Terrier (0.5 t)
- Tank: FL-T400 (2.25 t wet, 0.25 t dry)
- Decoupler: TD-12 (0.04 t) — separates stage 1
- m0 = 2.195 + 0.5 + 2.25 + 0.04 = 4.985 t
- mf = 2.195 + 0.5 + 0.25 + 0.04 = 2.985 t
- dV = 345 * 9.82 * ln(4.985/2.985) = 345 * 9.82 * 0.513 = 1,738 m/s

### Stage 1 (bottom) — Swivel + 2x FL-T800
- Carries stages 2+3 as payload
- Payload = stage 2 wet mass = 4.985 t
- Engine: Swivel (1.5 t)
- Tanks: 2x FL-T800 (2 * 4.5 = 9.0 t wet, 2 * 0.5 = 1.0 t dry)
- Decoupler: TD-25 (0.16 t) — on launchpad
- m0 = 4.985 + 1.5 + 9.0 + 0.16 = 15.645 t
- mf = 4.985 + 1.5 + 1.0 + 0.16 = 7.645 t
- dV vac = 320 * 9.82 * ln(15.645/7.645) = 320 * 9.82 * 0.716 = 2,250 m/s
- dV SL = 250 * 9.82 * ln(15.645/7.645) = 250 * 9.82 * 0.716 = 1,758 m/s

### TWR at launch (Stage 1, sea level)
- Thrust SL = 167.97 kN
- Weight = 15.645 * 9.81 = 153.5 kN
- TWR = 167.97 / 153.5 = 1.094 — TOO LOW! Need ≥ 1.3.

### Problem: TWR too low. Need more thrust or less mass.

Options:
1. Use LV-T30 "Reliant" (240 kN vac / 205.16 kN SL, Isp 310 vac / 265 SL, 1.25 t) — no gimbal but higher thrust
2. Add SRBs
3. Use a Mainsail or Skipper

Let me try the Reliant:
- Thrust SL = 205.16 kN
- TWR = 205.16 / 153.5 = 1.336 — meets ≥ 1.3!
- But no gimbal — need SAS/reaction wheels for control.

Actually, the Swivel has gimbal (3°) which is useful for control. Let me try adding SRBs instead.

Or use the Swivel with a smaller rocket. Let me reduce tank size.

Actually, let me try the Reliant + Swivel approach. Or better: use the "Twin-Boar" as a single-stage booster? No, that's overkill.

Let me redesign with the Reliant for stage 1 and add a small probe core for SAS control.

Actually, the Mk1 Command Pod has built-in reaction wheels. Combined with the Reliant (no gimbal), the reaction wheel should provide enough control for a gravity turn.

Wait — let me check: the Mk1 Command Pod has torque of what? From reference: Mk1 Command Pod mass 0.8 t. It has reaction wheels. The exact torque isn't listed but in KSP it's typically 10-15 kN·m, which is enough for a 15 t rocket.

Let me try: Stage 1: Reliant + 2x FL-T800.

### Revised Stage 1 — Reliant + 2x FL-T800
- Payload = 4.985 t (stages 2+3)
- Engine: Reliant (1.25 t, 240 kN vac / 205.16 kN SL, Isp 310 vac / 265 SL)
- Tanks: 2x FL-T800 (9.0 t wet, 1.0 t dry)
- Decoupler: TD-25 (0.16 t)
- m0 = 4.985 + 1.25 + 9.0 + 0.16 = 15.395 t
- mf = 4.985 + 1.25 + 1.0 + 0.16 = 7.395 t
- dV vac = 310 * 9.82 * ln(15.395/7.395) = 310 * 9.82 * 0.734 = 2,235 m/s
- dV SL = 265 * 9.82 * ln(15.395/7.395) = 265 * 9.82 * 0.734 = 1,910 m/s
- TWR SL = 205.16 / (15.395 * 9.81) = 205.16 / 151.0 = 1.359 ✓

### Total dV (vacuum):
Stage 1: 2,235 m/s
Stage 2: 1,738 m/s
Stage 3: 1,913 m/s
Total: 5,886 m/s ✓ (≥ 5,250)

But these are vacuum numbers. Stage 1 operates mostly in atmosphere. Let me use an average Isp for stage 1.

Actually, the standard approach is to compute total vacuum dV and note that atmospheric losses reduce effective dV by ~1,000-1,500 m/s. With 5,886 m/s vacuum dV, we should have ~4,400-4,800 m/s effective — enough for the mission.

### Final design

**Stage 3 (top):**
- Mk1 Command Pod (0.8 t)
- Mk16 Parachute (0.1 t)
- TD-12 Decoupler (0.04 t) — activates to separate from stage 2
- FL-T200 Fuel Tank (90 LF + 110 OX)
- 48-7S "Spark" Liquid Fuel Engine (0.13 t)

**Stage 2 (middle):**
- TD-12 Decoupler (0.04 t) — activates to separate from stage 1
- FL-T400 Fuel Tank (180 LF + 220 OX)
- LV-909 "Terrier" Liquid Fuel Engine (0.5 t)

**Stage 1 (bottom):**
- TD-25 Decoupler (0.16 t) — on launchpad
- 2x FL-T800 Fuel Tank (360 LF + 440 OX each)
- LV-T30 "Reliant" Liquid Fuel Engine (1.25 t)

Total vacuum dV: ~5,886 m/s ✓
First stage TWR at SL: 1.36 ✓

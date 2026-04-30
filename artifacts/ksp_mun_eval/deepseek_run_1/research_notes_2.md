# Research Notes — Attempt 2 Design

## Key Insight from Attempt 1
- Terrier at 19 km: still too low. Vacuum engines get 90% Isp at ~10 km, but thrust is also reduced at low altitude (14.78 kN SL vs 60 kN vac). Need to stage higher.
- First stage (Reliant + 2x FL-T800) only lasted 101 seconds to 19 km. Need much more first-stage dV.

## New Design Strategy
Use a **Skipper** (650 kN vac / 568.75 kN SL, Isp 320/280) or **Mainsail** (1500 kN vac / 1379 kN SL, Isp 310/285) for stage 1 with more fuel.

Actually, the Reliant is fine — the issue is I only had 2x FL-T800. Let me add more tanks.

### Option A: Reliant + 4x FL-T800 (2x stacked pairs)
- 4x FL-T800: 4 * 4.5 = 18.0 t wet, 4 * 0.5 = 2.0 t dry
- Payload: Let me recalculate with the same upper stages.

Stage 3 (top): Mk1 Pod + Parachute + Spark + FL-T200 = 2.195 t wet
Stage 2 (middle): TD-12 + Terrier + FL-T400 = 0.04 + 0.5 + 2.25 = 2.79 t wet (not counting payload)
Actually, let me keep stage 2+3 the same: 4.985 t wet payload.

### Option A: Reliant + 4x FL-T800
- Payload: 4.985 t
- Engine: Reliant (1.25 t)
- Tanks: 4x FL-T800 (18.0 t wet, 2.0 t dry)
- Decoupler: TD-25 (0.16 t)
- m0 = 4.985 + 1.25 + 18.0 + 0.16 = 24.395 t
- mf = 4.985 + 1.25 + 2.0 + 0.16 = 8.395 t
- dV vac = 310 * 9.82 * ln(24.395/8.395) = 310 * 9.82 * 1.066 = 3,245 m/s
- dV SL = 265 * 9.82 * 1.066 = 2,774 m/s
- TWR SL = 205.16 / (24.395 * 9.81) = 205.16 / 239.3 = 0.857 — TOO LOW!

OK, the Reliant can't lift 4x FL-T800 with a TWR of only 0.86. Need a bigger engine.

### Option B: Skipper + Rockomax X200-32 (or Jumbo-64)
Skipper: 650 kN vac / 568.75 kN SL, Isp 320/280, mass 3.0 t

Let me try Skipper + Jumbo-64 (2,880 LF + 3,520 OX, 36 t wet / 4 t dry):

Payload: 4.985 t
Engine: Skipper (3.0 t)
Tank: Jumbo-64 (36.0 t wet, 4.0 t dry)
Decoupler: TD-25 (0.16 t)
m0 = 4.985 + 3.0 + 36.0 + 0.16 = 44.145 t
mf = 4.985 + 3.0 + 4.0 + 0.16 = 12.145 t
dV vac = 320 * 9.82 * ln(44.145/12.145) = 320 * 9.82 * 1.291 = 4,056 m/s
dV SL = 280 * 9.82 * 1.291 = 3,549 m/s
TWR SL = 568.75 / (44.145 * 9.81) = 568.75 / 433.1 = 1.313 ✓ (≥ 1.3)

That works! The Skipper + Jumbo-64 gives excellent TWR and massive dV.

But total vacuum dV would be:
Stage 1: 4,056 m/s (Skipper + Jumbo-64)
Stage 2: 1,738 m/s (Terrier + FL-T400)
Stage 3: 1,913 m/s (Spark + FL-T200)
Total: 7,707 m/s — way more than needed. This gives huge margin.

Actually, let me check: with 4,056 m/s vacuum dV on stage 1 (3,549 SL equiv), the first stage should easily push us above 30 km with plenty of speed. The Terrier can then take over in near-vacuum.

### Option C: Skipper + Rockomax X200-32 (smaller tank)
X200-32: 18 t wet, 2 t dry, 1440 LF + 1760 OX

m0 = 4.985 + 3.0 + 18.0 + 0.16 = 26.145 t
mf = 4.985 + 3.0 + 2.0 + 0.16 = 10.145 t
dV vac = 320 * 9.82 * ln(26.145/10.145) = 320 * 9.82 * 0.947 = 2,976 m/s
TWR SL = 568.75 / (26.145 * 9.81) = 568.75 / 256.5 = 2.218 ✓

Total: 2,976 + 1,738 + 1,913 = 6,627 m/s — still plenty.

Let me go with **Option B (Skipper + Jumbo-64)** for maximum margin. The extra dV means we can afford a less efficient ascent and still complete the mission.

Actually, let me think about this more carefully. With the Jumbo-64, stage 1 has 36 t of fuel. At 568.75 kN SL thrust and average mass ~28 t, the burn time would be roughly:

Mass flow = thrust / (Isp * g0) = 568.75 / (280 * 9.82) = 0.207 t/s at SL... no, that's not right.

Mass flow rate:
mdot = F / (Isp * g0) where F is in kN, Isp in seconds
mdot = 568.75 / (280 * 9.82) = 0.207 t/s at sea level

Fuel mass = 36 t (tank) - 4 t (dry) = 32 t of fuel
Burn time ≈ 32 / 0.207 ≈ 154 seconds

That's much longer than the Reliant's 101 seconds, with much more thrust. The Skipper should push us well above 30 km.

Let me also consider: should I replace the Terrier with something else? At 30+ km, the Terrier gets ~90% of its vacuum Isp (345 * 0.9 = 310.5s) and thrust of ~0.9 * 60 = 54 kN. That's workable.

Actually, let me keep the Terrier. The key fix is a much bigger first stage.

### Revised rocket design

**Stage 3 (top):** Same as before
- Mk1 Command Pod (0.8 t)
- Mk16 Parachute (0.1 t)
- TD-12 Decoupler (0.04 t)
- FL-T200 Fuel Tank (1.125 t wet)
- 48-7S "Spark" (0.13 t)
- Wet: 2.195 t, Dry: 1.195 t, dV: 1,913 m/s

**Stage 2 (middle):** Same as before
- TD-12 Decoupler (0.04 t)
- FL-T400 Fuel Tank (2.25 t wet)
- LV-909 "Terrier" (0.5 t)
- Wet: 4.985 t (incl stage 3), Dry: 2.985 t, dV: 1,738 m/s

**Stage 1 (bottom):** Bigger!
- TD-25 Decoupler (0.16 t)
- Rockomax Jumbo-64 Fuel Tank (36 t wet, 4 t dry)
- RE-I5 "Skipper" (3.0 t, 650 kN vac / 568.75 kN SL)
- Wet: 44.145 t (incl stages 2+3), Dry: 12.145 t
- dV vac: 4,056 m/s, TWR SL: 1.313 ✓

**Total vacuum dV: 7,707 m/s** ✓ (≥ 5,250)

This gives us enormous margin. Even with atmospheric losses of ~1,500 m/s, we'd have ~6,200 m/s effective — well over the 4,570 m/s needed.

### Staging fix
Need to fix the endless staging loop bug. The `stage_if_depleted()` function should check that there are actually stages remaining before firing decouplers.

```python
def stage_if_depleted():
    if vessel.control.current_stage <= 0:
        return False
    # ... rest of logic
```

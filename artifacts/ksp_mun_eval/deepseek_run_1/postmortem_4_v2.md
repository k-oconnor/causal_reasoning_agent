# Postmortem — Attempt 4 (clean run)

## Evidence Table

| Metric | Predicted | Observed | Δ | Status |
|---|---|---|---|---|
| Starting ALT | 80 m (pad) | 80 m | — | ✓ |
| Skipper burned to depletion | yes | yes (T+155s) | — | ✓ |
| ALT at Skipper depletion | > 60 km | 62 km | — | ✓ |
| AP at Skipper depletion | 50-200 km | 726 km | +526 km | WARN |
| SPD at Skipper depletion | 2,000-2,500 m/s | 2,618 m/s | +118 m/s | WARN |
| Circularization dV | positive, < 500 | -315.7 m/s | — | FAIL |

## What Happened

The Skipper burned to depletion at T+155s (ALT=62 km, SPD=2,618 m/s, AP=726 km). The vessel was already on a highly elliptical orbit with AP=726 km.

**The immediate circularization attempt computed dV = -315.7 m/s.** This is negative because at the current position (r=666 km from Kerbin centre), the vessel's speed (2,618 m/s) was already HIGHER than the circular orbit speed at that altitude. The vessel needed to **slow down** (retrograde burn), not speed up.

This makes sense: the Skipper pushed the vessel to 2,618 m/s at 62 km altitude. For a circular orbit at 62 km altitude (r = 600,000 + 62,000 = 662,000 m), the required speed is:
- v_circ = sqrt(μ / r) = sqrt(3.5316e12 / 662,000) ≈ 2,310 m/s

So the vessel was going 2,618 m/s — about 308 m/s FASTER than circular speed. A retrograde burn of ~308 m/s would circularize.

**The fix:** The `circ_dv` calculation is wrong for this case. The formula `v_needed = sqrt(mu * (2/r_now - 1/a_new))` with `a_new = (r_now + target_radius)/2` gives a speed that raises the periapsis to `target_radius`. But if the vessel is already going faster than circular speed, this formula gives a value lower than current speed, resulting in negative dV.

**The real issue is deeper:** The Skipper + Jumbo-64 is too powerful for a 3-stage rocket going to the Mun. It pushes the vessel to escape velocity before staging. The Terrier then can't circularize because the vessel is already going too fast.

## Revised Root Cause

**The Skipper + Jumbo-64 combination provides too much dV in the first stage.** With 4,056 m/s vacuum dV, the Skipper accelerates the vessel to 2,618 m/s at 62 km — well above orbital speed. By the time the first stage depletes, the vessel is already on an escape trajectory (AP=726 km and climbing).

The problem is not the ascent logic — it's the **engine selection**. The Skipper is a 650 kN engine designed for heavy lift, but with the Jumbo-64 tank it gives too much dV for a Mun mission. The vessel reaches orbital velocity before leaving the atmosphere.

## New Design Direction

Go back to a smaller first stage that provides just enough dV to reach LKO, then use the upper stages for TMI and MOI. The Reliant from Attempt 1 was actually the right size — it just needed more fuel to stage higher.

**New design: Reliant + 3x FL-T800** (instead of 2x)
- TWR SL: 205.16 / (4.985 + 1.25 + 13.5 + 0.16) * 9.81 = 205.16 / 194.5 = 1.055 — TOO LOW

**Alternative: Swivel + 3x FL-T800**
- Swivel: 215 kN vac / 167.97 kN SL, Isp 320/250, mass 1.5 t
- TWR SL: 167.97 / (4.985 + 1.5 + 13.5 + 0.16) * 9.81 = 167.97 / 197.6 = 0.85 — TOO LOW

**Alternative: Use 2x Thumper SRBs as boosters + Reliant center core**
SRBs provide the extra thrust at launch, then drop away.

Or: **Use the Twin-Boar** as a single-stage booster. The Twin-Boar is a 2.5m engine with integrated tank (10.5 t dry, 2000 kN thrust, Isp 300/280, 640 LF + 780 OX integrated). With a payload of ~5 t:
- m0 = 5 + 10.5 = 15.5 t (but Twin-Boar wet mass is... let me check)

Actually, the Twin-Boar (LFB KR-1x2) has wet mass 10.5 t (it's an integrated engine+tank). Let me look up the exact numbers.

From reference: LFB KR-1x2 "Twin-Boar" Liquid Fuel Engine: mass 10.500 t, thrust 2000 kN vac / 1866.67 kN SL, Isp 300/280.

So it's 10.5 t total (engine + fuel integrated). Fuel capacity is... I need to look this up.

Let me search for the Twin-Boar fuel capacity.

Actually, I recall the Twin-Boar has 640 LF + 780 OX = 1,420 units of propellant. At 5 kg per unit, that's 7.1 t of propellant. So dry mass = 10.5 - 7.1 = 3.4 t. Wait, that doesn't match the 10.5 t listed.

The reference says: LFB KR-1x2 "Twin-Boar" Liquid Fuel Engine: mass 10.500 t. This is the WET mass (with fuel). The dry mass isn't listed explicitly.

Let me look at this differently. Let me go back to a simpler approach.

**New approach: Use the Reliant with enough fuel to reach orbit, but with SRB boosters for TWR.**

Or even simpler: **Use the Skipper with a SMALLER tank** — the Rockomax X200-32 (18 t wet, 2 t dry).

Skipper + X200-32:
- Payload: 4.985 t (stages 2+3)
- Engine: Skipper (3.0 t)
- Tank: X200-32 (18 t wet, 2 t dry)
- Decoupler: TD-25 (0.16 t)
- m0 = 4.985 + 3.0 + 18.0 + 0.16 = 26.145 t
- mf = 4.985 + 3.0 + 2.0 + 0.16 = 10.145 t
- dV vac = 320 * 9.82 * ln(26.145/10.145) = 320 * 9.82 * 0.947 = 2,976 m/s
- TWR SL = 568.75 / (26.145 * 9.81) = 568.75 / 256.5 = 2.22 ✓

This gives 2,976 m/s on stage 1 — enough to reach near-orbit without overshooting. Then the Terrier (1,738 m/s) circularizes and does TMI. The Spark (1,913 m/s) does MOI.

Total: 2,976 + 1,738 + 1,913 = 6,627 m/s — still plenty.

Let me estimate the Skipper burnout with X200-32:
- Fuel mass: 18 - 2 = 16 t
- mdot = F / (Isp * g0) = 568.75 / (280 * 9.82) = 0.207 t/s
- Burn time ≈ 16 / 0.207 ≈ 77 seconds

With 77 seconds of burn at TWR 2.22, the Skipper should push the vessel to ~40-50 km altitude with AP around 80-100 km — a much better staging point.

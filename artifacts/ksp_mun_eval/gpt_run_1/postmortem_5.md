## Evidence table — attempt 5

| Metric / prediction | Predicted | Observed | Δ / note | Status |
|---|---|---|---|---|
| Earlier/flatter ascent should keep trajectory bounded while continuing upward after SRB separation | Yes | No | Altitude plateaued around 9.7 km and never progressed to orbital ascent | FAIL |
| Post-SRB stage should keep accelerating effectively | Yes | Weakly / inadequately | Speed rose from 211.9 to 318.0 m/s, but AP only rose from 8.26 to 9.78 km over 77 s | FAIL |
| Script should reach apoapsis-coast and circularization phases | Yes | No | Never reached `APOAPSIS_COAST_START` | FAIL |
| New ascent logic should avoid previous hyperbolic overshoot | Yes | Trivially yes | It failed much earlier than that | N/A |

## Computed observations

### Event sequence
Observed events:
1. T+0 s `SCRIPT_START`
2. T+2 s `LAUNCH`
3. T+2 s `STAGE_1 DETAIL=liftoff`
4. T+2 s `VESSEL_REFRESH DETAIL=post_launch`
5. T+16 s `GRAVITY_TURN_START`
6. T+48 s `STAGE_0 DETAIL=srb_separation`
7. T+48 s `VESSEL_REFRESH DETAIL=after_srb_sep`
8. Then a kRPC RPCError while reading `vessel.surface_reference_frame`

### Telemetry diagnosis
Key rows after SRB separation:
- T+48 s: ALT=7,535 m, SPD=211.9 m/s, AP=8,262 m, FUEL=98.6%, STAGE=0
- T+80 s: ALT=9,582 m, SPD=238.6 m/s, AP=9,612 m, FUEL=89.3%, STAGE=0
- T+100 s: ALT=9,756 m, SPD=281.6 m/s, AP=9,756 m, FUEL=83.2%, STAGE=0
- T+125 s: ALT=9,775 m, SPD=318.0 m/s, AP=9,783 m, FUEL=75.8%, STAGE=0

### Arithmetic
From T+48 s to T+125 s:
- ALT increased from 7,535 m to 9,775 m: **+2,240 m** over 77 s
- AP increased from 8,262 m to 9,783 m: **+1,521 m** over 77 s
- SPD increased from 211.9 to 318.0 m/s: **+106.1 m/s**
- Fuel dropped from 98.6% to 75.8%: **-22.8 percentage points**

Interpretation:
- The upper stage was burning fuel and producing thrust.
- However, the vehicle was pitched far too low, far too early. It built some speed but almost no climb margin; apoapsis stayed under 10 km.
- Thus the attempt did not fail because of insufficient thrust alone; it failed because the revised gravity turn was now too aggressive for this rocket.

### Software failure
The script then crashed with:
- `krpc.error.RPCError: string[] string.Split(char,System.StringSplitOptions)`
- at `surf = vessel.flight(vessel.surface_reference_frame)`

This is the same odd server-side kRPC error family previously seen in logging. It occurred after the mission was already unrecoverable from a guidance standpoint, but it still means the script did not degrade gracefully when the vessel state became abnormal.

## Hypothesis verdict

- H1 from attempt 5 (flatter turn + earlier MECO would fix ascent): **ELIMINATED**. The flatter turn was too aggressive; the rocket essentially leveled off around 10 km and impacted the ocean.
- H2: **CONFIRMED**. Earlier MECO / flatter ascent alone did not solve the ascent problem.
- H3/H4 (later mission stack viability): **UNRESOLVED** because LKO was never reached.
- New hypothesis H10: **CONFIRMED** — the attempt-5 gravity turn was overly aggressive for this vehicle, causing inadequate vertical energy after SRB separation and keeping apoapsis below 10 km.

## Root cause
The final attempt’s gravity turn was too aggressive too early: after SRB separation the vehicle remained around 7.5–9.8 km altitude while burning substantial fuel, indicating that horizontal acceleration had been prioritized before sufficient vertical climb energy was established.

## What would be the targeted fix if more attempts existed
If another attempt were allowed, the next change would be:
1. Revert toward the attempt-4 ascent profile but keep the lower MECO target.
2. Turn less aggressively before ~15 km, then flatten later.
3. Add dynamic pitch logic based on time-to-apoapsis and vertical speed rather than altitude alone.
4. Wrap all `vessel.flight(vessel.surface_reference_frame)` calls with a retry / vessel-refresh guard to survive the intermittent kRPC `string.Split` server bug.

Mechanistic reason:
- This would balance the two opposing failures observed in attempts 4 and 5: attempt 4 stayed too vertical and escaped; attempt 5 flattened too early and splashed down.

## Cross-attempt summary

| Attempt | Final BODY | Final AP (km) | Final PE (km) | Root cause |
|---|---|---:|---:|---|
| 1 | Kerbin | 0.08 | -598.4 | Invalid engine attribute access during SRB check |
| 2 | Kerbin | 90.1 | -135.4 | Stale vessel/autopilot reference after final stage separation |
| 3 | Kerbin | 22.3 | -597.8 | Incorrect staging/build ambiguity; core detached, next stage did not ignite |
| 4 | Kerbin/Sun escape trajectory | hyperbolic after 89 km cutoff | +58.4 before escape | Ascent cutoff too late; apoapsis overshot into escape |
| 5 | Kerbin | 9.8 | -594.6 | Gravity turn too aggressive too early; splashed into ocean |

## Mission outcome
Mission **not achieved** within the 5 available attempts. No telemetry shows stable Mun orbit, stable LKO, or even a completed circularization burn in the final attempt.

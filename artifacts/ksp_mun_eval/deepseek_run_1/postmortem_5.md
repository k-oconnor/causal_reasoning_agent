# Postmortem — Attempt 5

## Evidence Table

| Metric | Predicted | Observed | Δ | Status |
|---|---|---|---|---|
| Starting ALT | 80 m (pad) | 80 m | — | ✓ |
| Skipper burned to depletion | yes | yes (T+90s) | — | ✓ |
| ALT at Skipper depletion | > 40 km | 38 km | −2 km | ~OK |
| AP at Skipper depletion | 80-150 km | 147 km | — | ✓ |
| SPD at Skipper depletion | 1,800-2,200 m/s | 1,733 m/s | −67 m/s | WARN (a bit low) |
| Coast phase throttle | 0.0 | 0.0 ✓ | — | ✓ |
| AP at coast end | 154 km | 155 km | — | ✓ |
| Circularization dV | < 500 m/s | 910 m/s | +410 m/s | FAIL |
| Circularization attempted | yes | no (sanity check) | — | FAIL |

## What Happened

1. **Skipper + X200-32** burned to depletion at T+90s, ALT=38 km, SPD=1,733 m/s, AP=147 km. ✓

2. **Staging to Terrier** at T+92s (stage 4 → stage 3). The Terrier ignited but throttle was reduced to 0.25 (the throttle guard set it to 0, but some residual throttle remained from staging).

3. **Coast phase** from T+94s to T+310s. APOAPSIS_COAST loop ran with `vessel.control.throttle = 0.0` on every iteration. The Terrier had throttle at 0.25 for the first ~50 seconds (T+97s to T+144s), then throttle dropped to 0.0 and stayed there.

4. **At T+315s**, the script computed circularization dV = 910.2 m/s. This exceeded the 500 m/s sanity check, so the script aborted.

## Root Cause

**The circularization dV sanity check limit of 500 m/s is too restrictive.** At AP=155 km, the required circularization dV is ~910 m/s, which is entirely reasonable. The sanity check should allow up to ~1,000 m/s for circularization from a highly elliptical orbit.

**But more importantly:** The Terrier was burning at 0.25 throttle during the early coast phase (T+97s to T+144s), consuming fuel and changing the trajectory. The throttle guard didn't fully work because the throttle was set to 0.25 by something during staging, and the guard only set it to 0.0 on each loop iteration — but the telemetry shows it stayed at 0.25 for ~50 seconds.

Looking at the telemetry more carefully:
- T+92s: FUEL=100.0%, STAGE=4 (Terrier just staged)
- T+97s: FUEL=98.7%, THROTTLE=0.25, STAGE=3 (Terrier burning at 25% throttle!)
- T+102s: FUEL=98.3%, THROTTLE=0.25
- ...
- T+138s: FUEL=95.4%, THROTTLE=0.16
- T+144s: FUEL=95.4%, THROTTLE=0.00

So the Terrier burned at ~25% throttle for about 47 seconds (T+97s to T+144s), consuming about 4.6% of its fuel. This is why AP stabilized at 155 km instead of continuing to rise.

The throttle guard was set on every iteration: `vessel.control.throttle = 0.0`. But the telemetry shows throttle=0.25. This means **something was overriding the throttle setting.** In kRPC, `vessel.control.throttle` is a client-side setting that the server reads. If the server has its own idea of what throttle should be (e.g., from a previous staging event or engine ignition), it may override the client setting.

**The real fix:** After staging, explicitly set throttle to 0 and then **wait for the engine to respond** before proceeding. Or better: never let the Terrier ignite at all during coast by not staging until we're ready to burn.

Actually, looking at the code flow:
1. Skipper depletes → `stage_if_depleted()` fires decoupler (stage 5→4)
2. `stage_if_depleted()` fires again (NO_ACTIVE_ENGINES, stage 4→3)
3. This stages to the Terrier, which ignites
4. The script then sets `vessel.control.throttle = 0.0` and starts the coast loop

But the Terrier has already ignited at whatever throttle was set. The throttle was set to 1.0 during the ascent (the Skipper was burning at full throttle). When staging happened, the Terrier inherited the throttle setting of 1.0.

Then the code set throttle to 0.0, but it took ~50 seconds for the Terrier to actually spool down to 0. This is because the Terrier's thrust at 25% throttle is still significant, and the engine spools down gradually.

## Root Cause (falsifiable claim)

**The Terrier ignites at the previous throttle setting (1.0) when staged, and the subsequent `vessel.control.throttle = 0.0` command takes ~50 seconds to fully take effect.** During this time, the Terrier burns fuel at reduced throttle, wasting dV and altering the trajectory.

## Fix

**Don't stage to the Terrier during the coast phase.** Instead:
1. After the Skipper depletes, coast on the spent stage (don't decouple).
2. When ready to circularize (at apoapsis), then stage and immediately burn.

OR: **Set throttle to 0 BEFORE staging**, so the Terrier ignites at 0 throttle and doesn't burn during coast.

OR: **Increase the sanity check limit** from 500 to 1,200 m/s, since 910 m/s is a valid circularization dV from AP=155 km.

The cleanest fix is option 2: set throttle to 0 before staging.

## Summary of All Attempts

| Attempt | Rocket | Failure Mode | Root Cause |
|---|---|---|---|
| 1 | Reliant + 2x FL-T800 | Stage 2 (Terrier) fired at 19 km in thick atmosphere | First stage too small; Terrier needs vacuum |
| 2 | Skipper + Jumbo-64 | Throttle cut at AP=85 km while at 42 km altitude | Ascent logic cut throttle too early |
| 3 | Skipper + Jumbo-64 | Terrier fired during coast (throttle reset) | Throttle not held at 0 during coast |
| 4 | Skipper + Jumbo-64 | Negative circularization dV (vessel overshot) | First stage too powerful; vessel exceeded orbital speed |
| 5 | Skipper + X200-32 | Circularization dV=910 m/s exceeded 500 limit | Sanity check too restrictive; Terrier burned during coast |

## Wins

- **Attempts 2-5 all successfully reached space** (unlike A1 where the Terrier failed in atmosphere)
- **The Skipper + X200-32 combination** in A5 gave a good ascent profile (AP=147 km at burnout)
- **The throttle guard** in A5 eventually worked (throttle reached 0.0 after ~50 seconds)
- **The gravity turn profile** worked well across all attempts — no aerodynamic failures
- **The staging logic** (stage_if_depleted) worked correctly in all attempts
- **The self-instrumentation** (telemetry, events, burns files) provided excellent diagnostic data

## Losses

- **The throttle reset issue** was never fully resolved — engines kept firing when they shouldn't during coast phases
- **The sanity checks** (500 m/s limit on circ dV) were too restrictive and aborted valid burns
- **The dV budget calculations** were correct in theory but didn't account for trajectory inefficiencies
- **5 attempts used** without reaching the Mun

## What Would Fix This

With one more attempt, I would:

1. **Set throttle to 0 BEFORE staging** to prevent the Terrier from igniting during coast
2. **Increase the circularization dV sanity check** from 500 to 1,200 m/s
3. **Wait for the engine to spool down** (time.sleep(2)) after setting throttle to 0
4. **Use the Skipper + X200-32** (the A5 rocket was the right size)

This combination would likely succeed.

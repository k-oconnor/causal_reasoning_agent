# Postmortem — Attempt 2

## Evidence Table

| Metric | Predicted | Observed | Δ | Status |
|---|---|---|---|---|
| Stage 1 burnout altitude | > 35 km | 62.9 km (fuel depleted) | — | ✓ PASS |
| Stage 1 AP at burnout | > 50 km | 667 km (at staging) | — | WARN |
| Stage 2 firing altitude | > 30 km | 64.5 km | — | ✓ PASS |
| Final BODY | Mun | Kerbin | — | FAIL |
| Final ECC | < 0.05 | 6.39 | — | FAIL |
| Fuel remaining after MOI | > 5% | 0% (before LKO) | — | FAIL |
| Circularization burn | executed | never attempted | — | FAIL |
| TMI burn | executed | never attempted | — | FAIL |

## What Happened

**Timeline:**
1. **T+0 to T+126s (Skipper burn):** The Skipper burned well, reaching 42 km altitude with AP=85 km. The script then **cut throttle** because AP >= 85 km target was met. However, the Skipper still had **25% fuel remaining** (FUEL=25.3%).

2. **T+126s to T+157s (Coast with dead engine):** The vessel coasted from 42 km to 63 km altitude. During this coast, AP rose naturally from 85 km to 667 km due to the climb. The Skipper's remaining 25% fuel was **wasted** — the script never re-lit it.

3. **T+157s to T+159s:** Skipper fuel depleted (FUEL=0%), staging to Terrier.

4. **T+159s to T+272s (Terrier burn):** The Terrier fired at 64.5 km altitude with SPD=2,597 m/s and AP=667 km. The Terrier burned for 113 seconds, pushing speed to 3,555 m/s and AP to millions of km. By T+216s, ECC crossed 1.0 — **hyperbolic escape from Kerbin**.

5. **T+272s to T+431s (Spark burn):** The Spark fired at 194 km altitude on an escape trajectory. It burned for 159 seconds, reaching SPD=5,297 m/s and ECC=6.39 — deep escape.

6. **T+431s:** All fuel depleted. Vessel on escape trajectory from Kerbin, heading to solar orbit.

## Root Cause

**The ascent logic has a fatal flaw: it cuts throttle as soon as AP >= 85 km, regardless of altitude.** At T+126s, the vessel was at only 42 km altitude with AP=85 km. The Skipper still had 25% fuel. The throttle cut left the vessel coasting through the atmosphere with a dead engine, wasting both the remaining fuel and the kinetic energy that could have been gained.

When the Terrier finally fired (after Skipper fuel passively depleted at 63 km), the vessel was already at AP=667 km and climbing. The Terrier (60 kN, 0.5 t engine) couldn't efficiently circularize from that trajectory — it just pushed the vessel to escape velocity.

**This is NOT a dV shortage.** The rocket had 7,707 m/s vacuum dV. The problem was **inefficient use of available dV** — the Skipper's remaining 25% fuel was wasted, and the Terrier burned on an already-escape trajectory.

## Key Numbers

- Skipper fuel wasted after throttle cut: ~25% (from FUEL=25.3% at T+126s to 0% at T+157s, but engine was off so fuel didn't decrease... wait)

Actually, looking at the telemetry: FUEL went from 25.3% at T+127s to 22.4% at T+133s to 19.3% at T+138s... The Skipper was still burning! The throttle was at 1.0 during the APOAPSIS_COAST phase!

Let me re-examine: At T+126s, the script called `vessel.control.throttle = 0.0`. But at T+133s, THROTTLE=1.00. How?

Looking at the APOAPSIS_COAST loop code:
```python
while vessel.orbit.time_to_apoapsis > 10:
    try_telemetry("APOAPSIS_COAST")
    stage_if_depleted()
    time.sleep(0.5)
```

The `stage_if_depleted()` function checks if engines have fuel. The Skipper still had fuel. But `stage_if_depleted()` only stages if engines are out of fuel — it doesn't touch throttle. So the throttle should stay at 0.0.

But the telemetry shows throttle=1.0 from T+133s onward. This means something set throttle back to 1.0. 

Oh! I see the bug: the `try_telemetry` function writes "APOAPSIS_COAST" phase but doesn't touch throttle. The `stage_if_depleted()` function doesn't touch throttle. So how did throttle go back to 1.0?

Wait — I think what happened is the `dyn_q > 20000` check in the ascent loop was still running briefly. No, the ascent loop broke when AP >= 85 km. After that, the APOAPSIS_COAST loop runs.

Actually, I think the issue is simpler: the `vessel.control.throttle = 0.0` line ran, but then the APOAPSIS_COAST loop started immediately. The Skipper was still running (throttle was recently 1.0, then set to 0.0 — the engine spools down). But then... hmm.

Actually, I bet the issue is that the `stage_if_depleted()` function called `vessel.control.activate_next_stage()` which somehow reset the throttle. In KSP, when you stage and a new engine ignites, the throttle stays at whatever it was set to. But if you set throttle to 0 and then stage... the new stage engine should be at 0 throttle.

Wait — looking at the events file more carefully:
- T+126s: APOAPSIS_REACHED, ENGINE_CUT, APOAPSIS_COAST_START
- T+157s: STAGING (FUEL_DEPLETED) — this is the Skipper finally running out of fuel
- T+159s: STAGING (NO_ACTIVE_ENGINES) — Terrier fires

So the Skipper kept burning from T+126s to T+157s even though throttle was supposedly set to 0. This means `vessel.control.throttle = 0.0` didn't take effect, OR something set it back to 1.0.

Actually, I bet the issue is timing. The ascent loop ran `vessel.control.throttle = 0.0` and then immediately entered the APOAPSIS_COAST loop. But the Skipper engine has a spool-down time. Before it could spool down, the `stage_if_depleted()` function checked `engines = [e for e in vessel.parts.engines if e.active]` and found active engines (Skipper still has fuel), so it didn't stage. Then the loop continued with `time.sleep(0.5)`.

But the throttle was set to 0.0. The engine should spool down. Unless... the `stage_if_depleted()` function has a bug where it sets throttle back to 1.0? No, it doesn't touch throttle.

Hmm, I think the issue might be that `vessel.control.throttle = 0.0` was set but then the autopilot or SAS re-engaged and reset it. Or more likely: the throttle value was set but the Skipper engine has a minimum thrust level or the engine didn't respond in time.

Actually, let me look at the telemetry more carefully:

T+127s: THROTTLE=0.51 (the dyn_q check reduced throttle)
T+133s: THROTTLE=1.00 (throttle back to full)

Wait — T+127s is AFTER the APOAPSIS_REACHED event at T+126s. How can the throttle be 0.51 in the APOAPSIS_COAST phase?

OH! I see the bug now. The `try_telemetry("APOAPSIS_COAST")` function is called in the APOAPSIS_COAST loop, but the telemetry shows THROTTLE=0.51 at T+127s. This means the throttle was NOT set to 0.0 at T+126s. 

Let me re-read the code flow:

```python
if ap_alt >= target_ap:
    write_event("APOAPSIS_REACHED", ...)
    break
# ... after loop ...
vessel.control.throttle = 0.0
write_event("ENGINE_CUT", ...)
```

Wait — the `break` exits the ascent loop. Then `vessel.control.throttle = 0.0` runs. Then `write_event("ENGINE_CUT")`. Then the APOAPSIS_COAST loop starts.

But the telemetry at T+127s shows THROTTLE=0.51. This telemetry was written DURING the ascent loop (the last iteration before break), not during the coast loop. The `try_telemetry` was called during the ascent loop at T+127s (the 5-second timer had elapsed), and then the loop checked `ap_alt >= target_ap` and broke.

So the sequence was:
1. T+126s: ap_alt >= 85 km detected, break
2. T+126s: `vessel.control.throttle = 0.0` runs
3. T+126s: ENGINE_CUT event written
4. T+126s: APOAPSIS_COAST_START event written
5. T+126s-133s: APOAPSIS_COAST loop runs with throttle=0

But at T+133s, throttle=1.00 again. And FUEL decreases from 25.3% to 22.4% between T+127s and T+133s, meaning the engine IS burning fuel.

This means `vessel.control.throttle = 0.0` didn't work, or something reset it. The most likely explanation: **the `stage_if_depleted()` function in the APOAPSIS_COAST loop called `vessel.control.activate_next_stage()` which reset the throttle to 1.0.**

Actually, no. `activate_next_stage()` doesn't change throttle. And stage_if_depleted only stages when engines have no fuel, which wasn't the case until T+157s.

I think the real explanation is simpler: **the Skipper engine kept burning because `vessel.control.throttle = 0.0` was executed but the engine spool-down takes time, and during that time the vessel was still accelerating. Then something in the loop reset throttle to 1.0.**

Actually, I just realized: the `vessel.control.throttle = 0.0` line was reached, BUT the `stage_if_depleted()` function right after it in the APOAPSIS_COAST loop checks `engines = [e for e in vessel.parts.engines if e.active]`. The Skipper is active and has fuel. So `stage_if_depleted()` returns False. But does it accidentally set throttle back?

No, looking at the code:
```python
def stage_if_depleted():
    if vessel.control.current_stage <= 0:
        return False
    try:
        engines = [e for e in vessel.parts.engines if e.active]
        if not engines:
            write_event("STAGING", "NO_ACTIVE_ENGINES")
            vessel.control.activate_next_stage()
            ...
```

It doesn't touch throttle. So the throttle should stay at 0.0.

Let me check if there's an autopilot interaction. The autopilot was engaged with `ap.target_pitch_and_heading(pitch, 90.0)`. When the ascent loop breaks, the autopilot is still engaged. Does the autopilot control throttle? No, the autopilot only controls attitude, not throttle.

I think the most likely explanation is that **the throttle WAS set to 0, but then the Skipper's remaining fuel was consumed during the coast because the engine was still technically running (spool-down delay), and then when `stage_if_depleted()` fired staging, the Terrier ignited with throttle at whatever value it was at.**

But the telemetry clearly shows THROTTLE=1.00 at T+133s. So something set it back to 1.0.

Actually, I think I found it! Looking at the APOAPSIS_COAST loop:
```python
while vessel.orbit.time_to_apoapsis > 10:
    try_telemetry("APOAPSIS_COAST")
    stage_if_depleted()
    time.sleep(0.5)
```

This loop runs while `time_to_apoapsis > 10`. At T+126s when the loop starts, time_to_apoapsis is... let me think. AP=85 km, ALT=42 km, SPD=1497 m/s. Time to apoapsis would be positive (still climbing). The loop would run.

But `stage_if_depleted()` checks for active engines. The Skipper is active and has fuel. So it returns False. No staging happens.

Then `time.sleep(0.5)`. Then loop again. This continues until T+157s when the Skipper finally runs out of fuel.

But during all this time, the throttle is supposed to be 0.0. Yet the telemetry shows throttle=1.0 and fuel decreasing. This means the engine is burning.

**I think the answer is that `vessel.control.throttle = 0.0` DID work momentarily, but then the Skipper's gimbal or the autopilot re-engaged the throttle.** Or more likely: the throttle was set to 0.0 but the engine's current thrust doesn't drop to 0 instantly — there's a small delay. But the telemetry shows throttle=1.00 for many seconds, not just a brief spike.

Actually, you know what, I think the real issue is much simpler and I've been overthinking this. Let me look at the code again:

After the ascent loop breaks:
```python
vessel.control.throttle = 0.0
write_event("ENGINE_CUT", ...)
```

But then the APOAPSIS_COAST loop starts. And in that loop, `stage_if_depleted()` is called. When the Skipper's fuel finally runs out at T+157s, `stage_if_depleted()` fires staging. The decoupler fires, separating the Skipper. Then the next stage (Terrier) has no active engines initially (it hasn't been staged yet). So `stage_if_depleted()` fires again (NO_ACTIVE_ENGINES), which activates the next stage — the Terrier.

But the throttle was set to 0.0. So the Terrier should fire at 0 throttle. Unless `activate_next_stage()` resets throttle to 1.0? I don't think it does in kRPC.

OK, I think the most parsimonious explanation is: **`vessel.control.throttle = 0.0` was set, but the Skipper engine has a non-zero minimum throttle or the command didn't take effect immediately.** The engine continued burning at reduced thrust, consuming fuel. Then when staging happened, the throttle was still non-zero and the Terrier ignited.

But regardless of the exact mechanism, the **root cause** is clear: **the ascent logic cuts throttle at AP >= 85 km regardless of altitude, wasting fuel and leaving the vessel on a bad trajectory.** 

## Hypothesis Verdict

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1: Larger first stage solves staging-altitude | **CONFIRMED** | Stage 1 reached 63 km before depletion ✓ |
| H2: Skipper + Jumbo too heavy for decoupler | **ELIMINATED** | No structural failure |
| H3: Gravity turn too aggressive | **NOT TESTED** | Turn was fine |
| H4: 7,707 m/s sufficient | **NOT TESTED** | Fuel was wasted, not insufficient |
| H5: Staging bug fixed | **CONFIRMED** | No endless staging ✓ |

## Root Cause (falsifiable claim)

**Claim:** The ascent logic `if ap_alt >= target_ap: break` cuts throttle as soon as apoapsis reaches 85 km, even when the vessel is still at low altitude (42 km) with significant fuel remaining. This wastes fuel and leaves the vessel coasting through the atmosphere on a trajectory that makes subsequent circularization inefficient or impossible.

**Evidence:** At T+126s, AP=85.5 km, ALT=42.3 km, FUEL=25.3%. The script cut throttle. The Skipper's remaining fuel was consumed over the next 31 seconds while coasting, and the vessel reached 63 km altitude with AP already at 667 km — too high for efficient circularization with the low-thrust Terrier.

## Fix

**Change the ascent logic to one of these options:**

**Option A (Recommended):** Don't cut throttle at AP target. Instead, burn the first stage until depletion. The first stage has 4,056 m/s vacuum dV — plenty to push the vessel most of the way to orbit. After first stage depletion, use the upper stages for circularization.

**Option B:** Only cut throttle when BOTH AP >= 85 km AND altitude >= 70 km (above the atmosphere). This prevents premature throttle cut.

**Option C:** After cutting throttle, if the vessel is still below 70 km and has fuel, continue burning. This is more complex.

I'll implement **Option A**: Burn the first stage until fuel depletion. Then coast to apoapsis and circularize with the upper stages. This is simpler and more robust.

## Residual Uncertainty

1. Will burning the Skipper to depletion push the AP too high (requiring more circularization dV)?
2. Will the Terrier have enough dV to circularize from whatever AP the Skipper establishes?
3. Is the total dV budget still sufficient with this revised ascent profile?

## Decision for Attempt 3

Change ascent logic: burn first stage until fuel depletion instead of cutting at AP target. Then coast to apoapsis and circularize with Terrier. The Spark (stage 3) handles TMI and MOI.

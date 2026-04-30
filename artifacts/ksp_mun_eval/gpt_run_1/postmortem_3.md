## Evidence table — attempt 3

| Metric / prediction | Predicted | Observed | Δ / note | Status |
|---|---|---|---|---|
| Vehicle-handle refresh should prevent post-staging autopilot failure | Yes | No later autopilot exception observed, but mission failed earlier in ascent due to wrong stage firing sequence | Different failure mode | UNRESOLVED for H1/H2 |
| Ascent should continue after SRB separation with liquid sustainer thrust | Yes | No | After SRB separation, AP stalled near 22.3 km and altitude eventually decreased to impact | FAIL |
| Fuel percentage after SRB separation should decline if active liquid stage is burning | Yes | No | FUEL stayed 100.0% from T+45 s to impact | FAIL |
| Stage sequence should preserve active thrusting engine on attached vessel | Yes | No | Operator observed “first swivel detached with fuel remaining; second swivel did not fire” | FAIL |

## Computed observations

### Event sequence
Observed events:
1. T+0 s `SCRIPT_START`
2. T+2 s `LAUNCH`
3. T+2 s `STAGE_4 DETAIL=liftoff`
4. T+2 s `VESSEL_REFRESH DETAIL=post_launch`
5. T+15 s `GRAVITY_TURN_START`
6. T+45 s `STAGE_3 DETAIL=srb_separation`
7. T+45 s `VESSEL_REFRESH DETAIL=after_srb_sep`

No later stage events were logged. This means the script did not intentionally perform another stage activation before impact.

### Telemetry diagnosis of the failure
Key rows:
- T+45 s: ALT=9,619 m, SPD=442.2 m/s, AP=17,243 m, FUEL=100.0%, STAGE=3
- T+60 s: ALT=14,454 m, SPD=355.1 m/s, AP=18,602 m, FUEL=100.0%, THROTTLE=1.00, STAGE=3
- T+86 s: ALT=20,592 m, SPD=293.5 m/s, AP=22,335 m, FUEL=100.0%, THROTTLE=1.00, STAGE=3
- T+106 s: ALT=22,324 m, SPD=231.4 m/s, AP=22,327 m, FUEL=100.0%, THROTTLE=1.00, STAGE=3
- T+121 s: ALT=21,188 m, SPD=271.3 m/s, AP=22,324 m, FUEL=100.0%, THROTTLE=1.00, STAGE=3
- T+146 s: ALT=14,791 m, SPD=424.3 m/s, AP=21,748 m, FUEL=100.0%, THROTTLE=1.00, STAGE=3
- T+181 s: ALT=1,191 m, SPD=399.2 m/s, AP=7,167 m, FUEL=100.0%, THROTTLE=0.65, STAGE=3
- T+187 s: ALT=-5 m, SPD=386.7 m/s, AP=5,515 m, FUEL=0.0%, STAGE=0

### Arithmetic and interpretation
1. **AP stagnation after SRB separation**
   - AP at T+45 s: 17,243 m
   - Peak AP observed: about 22,327 m at T+96 to T+111 s
   - Gain after SRB separation: only ~5,084 m
   This is far too small for a functioning sustainer stage.

2. **Speed collapse after SRB separation**
   - SPD at T+45 s: 442.2 m/s
   - SPD at T+60 s: 355.1 m/s
   - Net change over 15 s immediately after SRB separation: **-87.1 m/s** despite THROTTLE=1.00
   A correctly firing sustainer should have continued accelerating, not decelerating strongly.

3. **Fuel non-consumption**
   - FUEL remained exactly **100.0%** from T+45 s through T+181 s.
   Since fuel percentage is computed from attached LiquidFuel + Oxidizer on the active vessel, a constant 100.0% with THROTTLE=1.00 implies the currently controlled craft was not burning any LFO at all.

These three observations strongly support a staging/build mismatch: after SRB separation, the active vessel did not have a functioning ignited liquid sustainer attached.

### Operator observation vs telemetry
Operator report: “First swivel detached with fuel remaining. Second swivel did not fire.”
This matches the telemetry pattern exactly:
- a useful liquid engine/core was likely separated off prematurely;
- the surviving craft retained full fuel but no active propulsion.

## Hypothesis verdict

- H1/H2 from attempt 3 (stale vessel handle after staging): **UNRESOLVED**. The new failure occurred earlier than the previously observed circularization crash. There was no new autopilot exception because the mission never reached orbit.
- New hypothesis H8: **CONFIRMED** — the manifest/staging description allowed an incorrect VAB staging arrangement in which the lower Swivel/core detached prematurely at or shortly after SRB separation, and the next propulsion stage did not ignite.
- H3 from prior attempt set (vehicle can reach target AP with proper staging): **still supported by attempt 2**, but attempt 3 did not test it due to build/staging configuration failure.

## Root cause
The rocket’s actual staging/build configuration was incorrect: after SRB separation, the active vessel had throttle but no functioning liquid propulsion because the core Swivel stage detached prematurely and the next Swivel stage did not ignite, leaving the surviving craft to coast and fall back to Kerbin.

## Targeted fix and mechanistic reason
Fix for attempt 4:
1. Replace the ambiguous multi-Swivel stack with a **simpler, unambiguous 2-liquid-stage design** so the operator cannot accidentally cross-wire stage order.
2. Make the launch stack a single liquid core with two radial SRBs; after SRB separation, the same core engine continues burning until its own fuel is exhausted.
3. Use a single upper Terrier stage above one clearly specified decoupler for orbital insertion/TMI/MOI.
4. In the manifest, specify exact top-to-bottom stack order and exact stage actions per stage number semantically (launch, SRB decouple, core decouple + Terrier ignite).
5. In the script, stop relying on ambiguous automatic staging assumptions; explicitly wait for core fuel depletion before commanding upper-stage separation/ignition.

Mechanistic reason:
- Reducing the number of liquid stages during ascent removes the failure mode where the wrong Swivel detaches or the wrong stage remains unignited. A single continuing core after booster drop is much easier for the operator to build correctly and for the script to manage.

## What attempt 4 will specifically prove or disprove
Attempt 4 will test whether the simplified launcher architecture eliminates the staging/build ambiguity.

Predictions if H8 is correct and the redesign works:
- After SRB separation, telemetry will show continued acceleration and declining fuel percentage on the active craft.
- AP should continue rising well beyond 22 km and reach 80–100 km.
- Events should show a later, explicit core-separation event followed by successful circularization.

Predictions if H8 is wrong:
- Even with the simplified two-liquid-stage architecture, post-SRB acceleration will again collapse or the wrong vessel will remain active, implying a script-side control issue rather than a build-manifest ambiguity.

## Cross-attempt summary

| Attempt | Final BODY | Final AP (km) | Final PE (km) | Root cause |
|---|---|---:|---:|---|
| 1 | Kerbin | 0.08 | -598.4 | Invalid engine attribute access during SRB check |
| 2 | Kerbin | 90.1 | -135.4 | Stale vessel/autopilot reference after final stage separation |
| 3 | Kerbin | 22.3 | -597.8 | Incorrect staging/build: core Swivel detached, next stage did not ignite |

## Residual uncertainty
- Attempt 3 does not tell us whether the stale-vessel fix works at circularization because ascent never reached orbit.
- The exact VAB staging arrangement used by the operator may have differed from my intent because the previous manifest was too ambiguous for a two-Swivel ascent stack.

## Decision for attempt 4
Redesign the launcher for simplicity and clarity: one Swivel core with two Thumper boosters plus one Terrier upper stage. The next experiment will explicitly test whether removing ascent-stage ambiguity restores reliable ascent and allows the stale-vessel-handle fix to be evaluated at orbit insertion.

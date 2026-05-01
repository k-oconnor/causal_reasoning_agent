# Postmortem Writing: Hypothesis Documents and Post-Experiment Analysis

## Why These Documents Exist

A hypothesis document written *before* an experiment proves the agent had a
falsifiable prediction. A postmortem written *after* proves it updated on
evidence. Together they form the audit trail of the scientific method.

Without these two documents, the agent is guessing and hoping. With them,
each attempt narrows the uncertainty.

---

## Hypothesis Document — `hypotheses_N.md`

Write this *before* writing the flight script. It must contain:

### Required sections

**1. Current belief state**

What do you believe to be true about the mission at this point? Reference
prior evidence (postmortems) where possible.

```markdown
## Current belief state (attempt N)

Based on postmortem_N-1.md:
- The TMI burn is delivering the correct dV (confirmed, attempt 3).
- The MOI burn overshoots consistently by ~30 m/s.
- Cause is suspected stale `remaining_delta_v` after stage-2 decoupler fires.
```

**2. Competing hypotheses**

List every live hypothesis. Number them. You must have at least one testable
hypothesis before writing the experiment.

```markdown
## Competing hypotheses

H1: `node.remaining_delta_v` goes stale after staging mid-burn because the
    node dV was computed with pre-staging mass. The burn controller never
    reaches the target and runs indefinitely.

H2: The burn controller has a logic bug that applies 100% throttle even
    after the target dV is reached (off-by-one in the loop condition).

H3: The circularization node dV is over-estimated due to incorrect orbit
    speed measurement.
```

**3. Predictions**

For each hypothesis, state what the telemetry would show if that hypothesis
is correct. Be specific — include numbers, column names, and timing.

```markdown
## Predictions

If H1 is correct:
- `burns_attempt_N.txt` will show `RDV` decreasing to some floor value
  (> 0) and then flatline rather than reaching 0.
- `RDV` will jump to a new non-zero value immediately after the staging
  event (STAGE column changes) mid-burn.
- The burn will continue at THROTTLE=1.00 indefinitely.

If H2 is correct:
- `RDV` will reach approximately 0 but THROTTLE will not drop to 0.
- Burn continues for several seconds after RDV ≈ 0.

If H3 is correct:
- `SPD` at the start of the TMI burn will differ from the expected
  orbital speed at LKO by > 50 m/s.
```

**4. Experiment design**

What change does this attempt test? Be explicit about what is different from
the prior attempt.

```markdown
## Experiment design

Change from attempt N-1:
- Added velocity-fallback stop: if `vessel.orbit.speed - start_speed >= target_dv * 0.98`,
  cut throttle regardless of `remaining_delta_v`.
- Added `RDV_AT_STAGING` event write at every staging event during a burn.

This directly tests H1. If H1 is correct, the fallback will fire and the
burn will stop correctly. If H2 is correct, we will see RDV≈0 but THROTTLE≠0
in the burns file and the fallback will also fire (since SPD delta will
exceed target).
```

---

## Postmortem — `postmortem_N.md`

Write this *after* reading all three data files. Do not write it until you
have computed specific numbers.

### Required sections

**1. Evidence table**

A table comparing every prediction against the observation.

```markdown
## Evidence table — attempt N

| Metric                   | Predicted        | Observed        | Δ         | Status   |
|--------------------------|------------------|-----------------|-----------|----------|
| Final BODY               | Mun              | Mun             | —         | ✓ PASS   |
| Final AP (km)            | 100.0            | 102.3           | +2.3      | ✓ PASS   |
| Final PE (km)            | 30.0             | 28.7            | −1.3      | ✓ PASS   |
| ECC at orbit confirmed   | < 0.05           | 0.018           | —         | ✓ PASS   |
| MOI burn duration (s)    | ~42              | 45              | +3        | ~ WARN   |
| RDV at staging (m/s)     | any              | 48.2            | —         | recorded |
| Fallback fired           | yes (H1 correct) | yes             | —         | ✓ PASS   |
| Fuel at orbit confirmed  | > 5%             | 12.4%           | —         | ✓ PASS   |
```

**2. Hypothesis verdict**

State which hypotheses are confirmed, eliminated, or still unresolved.

```markdown
## Hypothesis verdict

H1 CONFIRMED: Burns file shows RDV jumped from 5.2 → 51.4 m/s at T+847s
  when STAGE changed from 1 → 0. Without the fallback, the burn would have
  continued. The velocity fallback fired at SPD delta = 271.8 m/s ≈ target_dv.

H2 ELIMINATED: RDV did reach 0 (well, 0.3) at the end of the burn after
  the fallback fired — no indefinite overrun was observed post-fix.

H3 ELIMINATED: SPD at TMI start was 2347.2 m/s, within 12 m/s of the
  theoretical LKO speed of 2359.0 m/s. No systematic measurement error.
```

**3. Root cause**

One clear sentence naming the mechanism.

```markdown
## Root cause

`node.remaining_delta_v` resets to a larger stale value after the staging
decoupler fires during the MOI burn, because the node was sized at pre-staging
mass. The burn controller then could never reach `RDV < 0.5` without the
velocity fallback.
```

**4. Fix applied (or to apply)**

What was changed, and whether it worked.

```markdown
## Fix applied

Added velocity-fallback stop condition in `execute_node()`:
```python
if speed_delta >= target_dv * 0.98:
    break
```
This fix resolved the overshoot. Orbit confirmed at attempt N.
```

**5. Residual uncertainty**

What remains unknown after this attempt.

```markdown
## Residual uncertainty

- MOI burn ended 3 s longer than predicted. Cause unclear — may be engine
  spool-down time or a 2% velocity-fallback margin being too conservative.
  Not a failure mode but worth tightening in a future attempt.
- Fuel budget at MOI was 12.4%. The design has ~8% margin. This is
  acceptable but narrow if additional correction burns are needed.
```

**6. Decision for next attempt**

If the mission succeeded, state it explicitly. If it failed, state exactly
what hypothesis the next experiment targets.

```markdown
## Decision

Mission SUCCEEDED. Mun orbit confirmed at 102×29 km, ECC 0.018.
No further attempts required. Calling plan_complete.
```

OR:

```markdown
## Decision for attempt N+1

H1 is confirmed. Fix: add velocity-fallback stop in execute_node().
New uncertainty: will this fix work when staging occurs in the first
25% of a burn (early staging, large RDV jump)? New hypothesis to test:
H4: Early staging (first 50% of burn) with RDV jump > 100 m/s still
overshoots with the 2% fallback margin.
Prediction: If H4, SPD delta at fallback fire will exceed target_dv by > 5%.
```

---

## Quality Gate

A postmortem that cannot answer these six questions is incomplete:

1. What was the final BODY, AP, PE, and ECC?
2. Which predictions were confirmed and which were violated?
3. What is the single most likely root cause?
4. What specific code change would fix it?
5. Is the mission done? If not, what is the next hypothesis?
6. What residual uncertainty remains unresolved?

Do not proceed to the next attempt without answering all six.

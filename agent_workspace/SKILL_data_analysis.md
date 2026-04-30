# Data Analysis: Extracting Conclusions from Experiment Logs

## Principle

The agent's job after every experiment is to transform raw log lines into
a falsification verdict: which hypotheses were supported, which were
eliminated, what new uncertainty remains. Vague prose ("the orbit seemed
unstable") is not analysis. Specific numbers against specific predictions
("AP reached 127,842 m, predicted 100,000 m; PE was −3,200 m, predicted
30,000 m → MOI burn overshot by ~33 m/s") is analysis.

## Reading Log Files Back

After `read_file("telemetry_attempt_N.txt")`, the content arrives as a
plain string. Parse it in the reasoning step, not in generated code.

### Telemetry row format

Each row produced by the self-instrumentation template has the form:
```
[T+420s] ALT=84231m SPD=2347.2m/s AP=85120m PE=81400m ECC=0.0021 BODY=Kerbin FUEL=61.4% PHASE=APOAPSIS_COAST STAGE=1
```

Parse each field as a key=value pair. Key fields to extract per row:
- `T+` — mission elapsed time (s)
- `ALT` — altitude (m)
- `SPD` — orbital speed (m/s)
- `AP` / `PE` — apoapsis/periapsis altitude (m)
- `ECC` — eccentricity
- `BODY` — current SOI body
- `FUEL` — fuel remaining (%)
- `PHASE` — flight phase label
- `STAGE` — current stage

### Burn row format

```
UT=85234.12 RDV=47.30 SPD=2802.15 THROTTLE=1.00 STAGE=0
```

Key fields: `UT`, `RDV` (remaining delta-v), `SPD`, `THROTTLE`, `STAGE`.

### Event row format

```
[T+600s] EVENT=BURN_END:TMI BODY=Kerbin ALT=85000m
```

Key fields: `EVENT` tag, `BODY`, `ALT`.

## What to Compute for Each Attempt

Work through every telemetry file systematically. Calculate:

### 1. Eccentricity at key milestones

- At circularization burn end: ECC should be < 0.05 for a "circular" orbit.
- If ECC ≥ 1.0 at any row: hyperbolic escape confirmed. Find the first row
  where ECC crossed 1.0 and note the corresponding time, phase, and ALT.

### 2. Final orbit quality

- Final AP: difference from target (e.g., 100 km = 100,000 m).
- Final PE: difference from target.
- Final BODY: must be "Mun" not "Kerbin" or "Sun".
- Pass criterion: |AP − target| < 10,000 m AND |PE − target| < 10,000 m
  AND ECC < 0.05 AND BODY = "Mun".

### 3. Burn overshoot analysis (from burns file)

Compute speed delivered:
```
speed_delta = last_SPD_in_burn - first_SPD_in_burn
target_dv   = first_RDV_in_burn
overshoot   = speed_delta - target_dv
```
Negative overshoot = under-burn. Large positive overshoot = burn ran too long.

Look for the THROTTLE column dropping from 1.0 → 0 to confirm the burn
actually ended. If THROTTLE stays at 1.0 until the last row, the burn
ran until the script crashed or fuel ran out.

### 4. Staging events

From the events file, list all `STAGE_N` events. For each, note:
- The MET at staging.
- Whether the burn continued correctly after staging.
- Whether `SPD` in the subsequent telemetry rows is sensible.

Any `SPD=0.0` row is a sentinel: either `orbit.speed` was not used (bug),
or the vessel is sitting on the launchpad. If SPD=0 appears during flight,
the script used the wrong speed attribute.

### 5. Fuel budget

Plot (mentally) fuel% over time using the `FUEL` column.
- What fuel% was remaining at MOI burn start?
- Did fuel run out during a burn? Look for `FUEL=0.0%` rows mid-burn.

### 6. Phase sequence

From the events file, verify the mission hit these events in order:
`LAUNCH` → `GRAVITY_TURN_START` → `APOAPSIS_COAST_START` →
`BURN_START:CIRCULARIZE` → `BURN_END:CIRCULARIZE` →
`BURN_START:TMI` → `BURN_END:TMI` → `SOI_CHANGE:Mun` →
`BURN_START:MOI` → `BURN_END:MOI` → `ORBIT_CONFIRMED`

Any gap or out-of-order event is a failure mode worth naming explicitly.

## Forming a Verdict

After computing the above, write a verdict in this format for the postmortem:

```markdown
## Analysis verdict — attempt N

| Metric              | Predicted     | Observed      | Δ        | Result |
|---------------------|---------------|---------------|----------|--------|
| Final AP (km)       | 100.0         | 127.8         | +27.8    | FAIL   |
| Final PE (km)       | 30.0          | −3.2          | −33.2    | FAIL   |
| Final ECC           | < 0.05        | 1.23          | —        | FAIL   |
| Final BODY          | Mun           | Kerbin        | —        | FAIL   |
| MOI overshoot (m/s) | 0             | +33.4         | —        | FAIL   |
| Fuel at MOI (%)     | > 20%         | 45.2%         | —        | PASS   |
| SPD=0 during flight | 0 occurrences | 0 occurrences | —        | PASS   |

Root cause: MOI node `remaining_delta_v` went stale after stage-2 decoupler
fired at T+847s mid-burn. Velocity-fallback condition was absent; burn
continued until vessel reached escape velocity.

Hypothesis H2 ("stale RDV after staging causes burn overshoot") is
**CONFIRMED**.
```

## Comparing Across Attempts

Maintain a summary table in `postmortem_attempt_N.md` covering all attempts
so far. This lets the agent see whether each fix actually improved things.

| Attempt | Final BODY | Final AP (km) | Final PE (km) | ECC   | Root cause |
|---------|------------|---------------|---------------|-------|------------|
| 1       | Kerbin     | N/A           | N/A           | N/A   | No TMI burn |
| 2       | Sun        | —             | —             | 2.1   | Burn ran until escape |
| 3       | Mun        | 127.8         | −3.2          | 1.23  | MOI stale RDV after staging |
| 4       | ...        | ...           | ...           | ...   | ... |

A root cause that appears in more than one attempt but is not in the
fix list is an unresolved systematic error. Prioritise it.

## Anti-Patterns

- **"The orbit looked correct."** Not analysis. Read the telemetry and
  provide numbers.
- **"The script probably had a bug."** Not analysis. Name the specific line,
  the specific wrong value, and the mechanism.
- **Skipping the burns file.** Burn overshoot is invisible in telemetry alone.
  Always read all three files.
- **Only reading the last N lines.** Failures often manifest mid-flight.
  Read the full file or at least check every phase transition.
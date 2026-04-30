# Workspace Workflow: External Memory, File Naming, and State Recovery

## The Workspace as External Memory

The agent's context window resets or grows stale. The workspace does not.
Everything the agent has learned across all attempts lives in `agent_workspace/`.
Treat it as your lab notebook: write to it constantly, read from it at the
start of every new attempt.

The workspace path is revealed by `list_files()`. It appears as the first
line of the response:
```
Workspace: C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace
  flight_attempt_1.py  (3,241 bytes)
  hypotheses_1.md      (812 bytes)
  ...
```

**Extract and embed this absolute path in every generated script before
calling `save_file`.** Do not guess or construct the path — read it from
`list_files()` output.

## File Naming Convention

Use versioned, descriptive names. The attempt number N comes from the count
of previous `flight_attempt_*.py` files in the workspace.

| File | Purpose |
|---|---|
| `hypotheses_N.md` | Written *before* the experiment. Records what you believe and why. |
| `manifest_attempt_N.md` | Rocket design, staging, dV budget, burn plan. If the stack is unchanged from attempt N−1, save a **stub**: cite prior manifest by filename and note script-only fixes — never omit the file (gaps look like missing data). |
| `flight_attempt_N.py` | The executable flight script for this attempt. |
| `telemetry_attempt_N.txt` | Row-per-5s telemetry written by the script. |
| `burns_attempt_N.txt` | Row-per-0.25s burn data written by the script. |
| `events_attempt_N.txt` | Milestone events written by the script. |
| `postmortem_N.md` | Written *after* analysis. Records what you found and what to fix. |

Never reuse a number. Never name a file `flight.py` or `telemetry.txt`
(no version → overwrites prior evidence → cannot compare across attempts).

## Session Start Procedure

At the start of every planning session or new attempt, call `list_files()`
and `read_file()` on the most recent versions of:

1. `hypotheses_N.md` — what was believed going in
2. `postmortem_N.md` — what was found and what the fix was
3. `telemetry_attempt_N.txt` — raw evidence (at least the last 20 rows)
4. `events_attempt_N.txt` — the sequence of milestones

This is not optional. Context accumulated in prior turns may be gone.
The workspace is ground truth.

## Writing Artifacts in the Correct Order

Within a single attempt, always write in this order:

```
1. hypotheses_N.md      ← before any code is written
2. manifest_attempt_N.md
3. flight_attempt_N.py  ← embed workspace path from list_files()
4. [notify operator, await execution]
5. [read telemetry_attempt_N.txt, burns_attempt_N.txt, events_attempt_N.txt]
6. postmortem_N.md      ← after analysis, before incrementing N
```

Never skip step 1 or step 6. The hypothesis document proves the agent
had a falsifiable prediction *before* the experiment. The postmortem proves
it updated on the evidence.

## Embedding the Workspace Path in a Generated Script

```python
# 1. Call list_files() and parse the first line:
#    "Workspace: C:\Users\kevin\...\agent_workspace"
# 2. Extract the path string after "Workspace: "
# 3. Embed it literally in the script:

WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
N = 4   # attempt number

import os
TEL_FILE    = os.path.join(WORKSPACE, f"telemetry_attempt_{N}.txt")
BURNS_FILE  = os.path.join(WORKSPACE, f"burns_attempt_{N}.txt")
EVENTS_FILE = os.path.join(WORKSPACE, f"events_attempt_{N}.txt")
```

Use a raw string (`r"..."`) on Windows to avoid backslash escaping issues.

## Reconstructing State After a Crash or Timeout

If the planning loop restarts mid-attempt:

1. `list_files()` — identify the highest N present.
2. Check for `flight_attempt_N.py` without a corresponding
   `telemetry_attempt_N.txt` — that attempt may be mid-flight or failed
   before the script ran. Ask the operator via `human_ask`.
3. If `postmortem_N.md` exists, the analysis is complete; move to attempt N+1.
4. If `telemetry_attempt_N.txt` exists but `postmortem_N.md` does not,
   the script ran but analysis was not done; read all data files and write
   the postmortem before proceeding.

## File Size Limits

`read_file` returns the full content. Large telemetry files (thousands of
rows) will consume context window. Strategies:

- For telemetry analysis, identify the phase boundaries from the PHASE column
  and focus reads on transition rows rather than steady-state cruise rows.
- Always read `events_attempt_N.txt` first (smallest file, highest signal).
- Only read the full `burns_attempt_N.txt` when diagnosing a burn anomaly.

## Using the Workspace as a Scratchpad

The agent is not limited to the prescribed files. Additional files are
encouraged:

| File | Use |
|---|---|
| `research_notes.md` | Findings from `web_search` / `fetch_page` that should persist |
| `delta_v_budget.md` | Calculated dV values for the current rocket design |
| `anomaly_log.md` | Running list of bugs found, their root causes, and fixes applied |
| `mission_log.md` | One-line-per-attempt summary table for the operator |

The workspace is unlimited. Write more, not less. The cost of an unwritten
finding is having to rediscover it next attempt.

## Checklist Before `plan_complete`

Before calling `plan_complete`, verify:

- [ ] `events_attempt_N.txt` contains `ORBIT_CONFIRMED`.
- [ ] The telemetry file shows final BODY=Mun, ECC < 0.05, AP and PE
  within 10 km of target.
- [ ] The operator has confirmed the flight succeeded (via `human_ask`).
- [ ] `postmortem_N.md` has been written even for the successful attempt
  (records what worked and why, for future reference).

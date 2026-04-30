# KSP Mun orbit eval — archived runs

Frozen snapshots of agent attempts against the same Mun-orbit mission spec (kRPC flight scripts + operator-in-the-loop).

| Folder | Model | Notes |
|--------|-------|--------|
| `deepseek_run_1/` | DeepSeek | Five attempts; reached strong elliptical profile (~155 km AP); failures dominated by throttle inheritance after staging and an overly tight circularization dV cap. |
| `gpt_run_1/` | GPT (OpenAI) — session 1 | Five attempts; SRB + dual-Swivel ascent stacks; staging/build ambiguity (wrong stage active after booster drop); strong telemetry-led diagnosis by attempt 3. |
| `gpt_run_2/` | GPT (OpenAI) — session 2 | Five attempts; Making History parts (e.g. Cheetah, Bobcat); failures included total-vessel fuel % used as staging trigger (upper-stage fuel masked burnout). |

Each folder contains paired artifacts per attempt: `hypotheses_N.md`, `manifest_attempt_N.md`, `flight_attempt_N.py`, `telemetry_attempt_N.txt`, `burns_attempt_N.txt`, `events_attempt_N.txt`, and `postmortem_N.md` where written.

**Manifest numbering gaps:** Some attempts have no `manifest_attempt_N.md` because the agent carried the rocket design forward unchanged and only revised the flight script. That is an artifact of agent behaviour (omitting a duplicate manifest), not missing data. Going forward, eval instructions ask for a stub manifest every attempt even when the stack is unchanged.

**Spoken summary:** `PERFORMANCE_NARRATIVE.md` (~385 words, about **2¾–3 minutes** at conversational pace).

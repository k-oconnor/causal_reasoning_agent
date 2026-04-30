# Postmortem — Attempt 4

## Evidence Table

| Metric | Predicted | Observed | Δ | Status |
|---|---|---|---|---|
| Starting ALT | 0 m (sea level) | 701,763 m | +701,763 m | FAIL |
| Skipper burned to depletion | yes | yes (immediately) | — | WARN |
| Circularization dV | positive | -297.8 m/s | — | FAIL |

## What Happened

The script started at **702 km altitude** — already in space, not on the launchpad. The launch_ut was set at T+0s with ALT=701,763m. The Skipper was already depleted (STAGE=3 → 2 → 1 immediately). The vessel was on a suborbital trajectory with AP=718 km and PE=-47 km.

The script tried to circularize but computed `circ_dv = -297.8 m/s` (negative, meaning the vessel was already going faster than needed). The sanity check rejected this.

**The operator reverted to the last launch but the vessel was still in flight from a prior attempt.** The script ran on a vessel that was already in mid-flight.

## Root Cause

This attempt was not a clean start. The vessel was already in flight from a previous attempt (Attempt 3). The operator likely reverted to launch but the vessel state was not fully reset, or the launch was from the Tracking Station rather than the VAB.

This is not a script bug — it's a procedural issue. The attempt is void.

## Decision

Request a clean revert from the operator. The vessel must be on the launchpad at ALT=80m (sea level) before the script starts. This attempt does not count against the 5-attempt limit.

Proceed to Attempt 5 with the same rocket and script, but confirm the operator has performed a clean revert to launchpad before running.

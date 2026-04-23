# KSP Agent Eval — Mun Orbit Mission
## Instructions for the Agent

---

## Overview

You are an autonomous agent controlling a rocket in Kerbal Space Program (KSP 1.x). Your mission is to launch from the Kerbal Space Center (KSC) and achieve a stable orbit around the Mun. You have **5 attempts** and an **unlimited part budget**.

Mission success is defined as: a closed, stable Mun orbit with periapsis ≥ 10 km and apoapsis ≤ 500 km, sustained for at least one full orbit without active thrust.

---

## Tools Available to You

You control the rocket exclusively via **kRPC** — a remote procedure call server running inside KSP. Your interface is the kRPC Python client (`import krpc`). You may issue any kRPC call documented in the kRPC API. You do not have access to the keyboard, mouse, or KSP UI.

### Connection

```python
import krpc
conn = krpc.connect(name='MunMissionAgent')
vessel = conn.space_center.active_vessel
```

### Key kRPC objects and namespaces

| Object | Description |
|---|---|
| `vessel` | The active vessel |
| `vessel.control` | Throttle, staging, RCS, SAS, gear |
| `vessel.auto_pilot` | Attitude control — target pitch/heading/roll |
| `vessel.flight()` | Altitude, velocity, dynamic pressure, g-force |
| `vessel.orbit` | Apoapsis, periapsis, eccentricity, period, body |
| `vessel.resources` | Fuel, oxidizer, monoprop by stage or total |
| `conn.space_center.bodies` | Dict of all celestial bodies (Kerbin, Mun, etc.) |
| `conn.space_center.ut` | Universal time (seconds) |

### Useful patterns

```python
# Arm SAS and set mode
vessel.control.sas = True
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(90, 90)  # straight up, east

# Throttle and staging
vessel.control.throttle = 1.0
vessel.control.activate_next_stage()

# Read telemetry
flight = vessel.flight()
altitude   = flight.mean_altitude       # metres above sea level
surface_alt = flight.surface_altitude   # metres above terrain
velocity   = flight.speed               # m/s, surface frame
apoapsis   = vessel.orbit.apoapsis_altitude   # m above Kerbin sea level
periapsis  = vessel.orbit.periapsis_altitude

# Orbital body
body = vessel.orbit.body.name  # 'Kerbin', 'Mun', etc.

# Streams (efficient polling — prefer over polling in a loop)
ap_stream = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
current_ap = ap_stream()
```

### Maneuver nodes

```python
# Create a node at a specific UT with prograde/normal/radial components
node = vessel.control.add_node(
    conn.space_center.ut + time_to_burn,
    prograde=delta_v_prograde,
    normal=0,
    radial=0
)
# Execute: point at node, burn until remaining dV amps to zero
vessel.auto_pilot.reference_frame = node.reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)
```

---

## Phase Requirements

You must complete the mission in the following ordered phases. Each phase must be verified via telemetry before proceeding.

### Phase 1 — Launch and gravity turn

- Throttle to full, activate first stage, and lift off.
- Begin a gravity turn: pitch toward the horizon gradually as altitude increases. A standard profile is 90° (vertical) at launch, transitioning to ~45° by 10 km, and ~10° by 45 km.
- Target an apoapsis of **80–100 km** above Kerbin before cutting engines.
- Do not leave the atmosphere (altitude > 70 km) until apoapsis is set.

### Phase 2 — Circularization burn

- At apoapsis, perform a prograde burn to raise periapsis to ≥ 75 km.
- Verify: `vessel.orbit.periapsis_altitude ≥ 75,000` and `vessel.orbit.body.name == 'Kerbin'`.
- You are now in low Kerbin orbit (LKO).

### Phase 3 — Trans-Mun injection (TMI)

- Plan and execute a prograde burn to raise your apoapsis to approximately the Mun's orbital altitude (~11,400 km).
- Target an encounter with the Mun. An encounter is confirmed when `vessel.orbit.next_orbit` is not `None` and `vessel.orbit.next_orbit.body.name == 'Mun'`.
- Time the burn correctly using the phase angle between your vessel and the Mun. You may compute this from `conn.space_center.bodies['Mun'].orbit`.

### Phase 4 — Mun orbit insertion (MOI)

- On approach, when periapsis inside the Mun's SOI is below your target altitude, perform a retrograde burn at periapsis to circularize.
- Target: periapsis ≥ 10 km, apoapsis ≤ 500 km, `vessel.orbit.body.name == 'Mun'`.
- Sustain this orbit for one full orbit period without thrust.
- Mission complete when this condition is confirmed.

---

## Rocket Manifest Requirements

Before each attempt, you must produce a **rocket manifest** — a structured plan for the rocket you are requesting. The human operator will build this rocket in the VAB to your specification.

The manifest must include:

1. **Stage table** — for each stage, in order of firing: engine(s), propellant tanks, decouplers, and the expected delta-v and TWR at ignition.
2. **Total delta-v** — must exceed the Kerbin-to-Mun-orbit budget with ≥ 15% margin. The canonical budget is approximately 3,400 m/s (LKO) + 860 m/s (TMI) + 310 m/s (MOI) = ~4,570 m/s. With margin: **≥ 5,250 m/s**.
3. **TWR constraints** — first stage TWR at launch ≥ 1.3 (Kerbin surface gravity = 9.81 m/s²). Upper stages may be lower but must sustain attitude control.
4. **Part names** — use exact KSP part names as they appear in the KSP wiki or the in-game part list (e.g. `LV-T45 "Swivel" Liquid Fuel Engine`, `FL-T400 Fuel Tank`).
5. **Decoupler placement** — specify which decoupler separates each stage.
6. **SAS/RCS** — specify if reaction wheels or RCS thrusters are included, and on which stage.

You are encouraged to consult the [KSP wiki](https://wiki.kerbalspaceprogram.com) for part stats (thrust, Isp, mass) and the [dV map](https://wiki.kerbalspaceprogram.com/wiki/Cheat_sheet) before finalizing the manifest.

---

## Human Interventions — What Is Allowed

The human operator's role is limited. The following interventions are **permitted and expected**:

| Intervention | When | Notes |
|---|---|---|
| Build the rocket in the VAB | Before each attempt | Strictly to your manifest specification |
| Launch the game and connect kRPC | Before each attempt | Server must be running before your script starts |
| Revert to launch | After a failed attempt | Counts as consuming one attempt |
| Confirm kRPC connection | At start | Operator confirms `conn.space_center.active_vessel` is your rocket on the pad |

The following interventions are **not permitted**:

- Adjusting the rocket design beyond your manifest
- Issuing any control inputs (keyboard, mouse, controller) during the flight
- Using the debug menu, Hack Gravity, or any cheat console
- Adding fuel, parts, or resources mid-flight
- Manually steering during any phase

If the operator makes an unauthorized intervention, the attempt is void and does not count against your 5 attempts.

---

## Telemetry Loop

Your flight script must implement a telemetry loop that logs the following at minimum every 5 seconds of game time:

```
[T+{elapsed}s] ALT={mean_altitude:.0f}m | SURF_ALT={surface_altitude:.0f}m | SPD={speed:.1f}m/s | AP={apoapsis:.0f}m | PE={periapsis:.0f}m | BODY={orbit_body} | FUEL={fuel_pct:.1f}% | PHASE={current_phase}
```

This log is your primary diagnostic artifact. It will be reviewed as part of the process score.

---

## Attempt Management

You have **5 attempts**. An attempt begins when your script commands the first stage to activate, and ends when:

- Mission success is confirmed (stable Mun orbit for one full orbit), **or**
- The vessel is destroyed, loses control, or runs out of fuel before completing Phase 4, **or**
- You explicitly declare the attempt failed and request a revert.

Between attempts you must:

1. State the failure mode and the specific telemetry reading that indicated failure.
2. Revise your manifest if the failure was caused by insufficient dV, incorrect staging, or part selection.
3. Revise your flight script if the failure was caused by attitude control, burn timing, or maneuver node errors.
4. Produce a new manifest before the operator rebuilds.

---

## Scoring

Your performance will be evaluated on two axes.

### Process score (40 points)

| Criterion | Points |
|---|---|
| Manifest includes all required fields | 10 |
| dV budget ≥ 5,250 m/s with per-stage breakdown | 10 |
| TWR ≥ 1.3 at launch, justified for upper stages | 5 |
| Part names are valid KSP parts | 5 |
| Failure analysis between attempts is accurate and specific | 10 |

### Flight score (60 points)

| Phase completed | Points |
|---|---|
| Liftoff and gravity turn (AP ≥ 80 km) | 10 |
| Stable LKO (PE ≥ 75 km, Kerbin orbit) | 15 |
| Mun encounter confirmed | 15 |
| Stable Mun orbit (PE ≥ 10 km, AP ≤ 500 km, one full orbit) | 20 |

Partial credit is awarded for each phase reached, regardless of whether subsequent phases succeed. Score is taken from the **best single attempt**.

---

## Notes on kRPC Limitations

- kRPC does not expose a direct "time to apoapsis" in all reference frames — compute it from `vessel.orbit.time_to_apoapsis`.
- `vessel.control.activate_next_stage()` fires stages sequentially. Confirm staging with a fuel check after each activation.
- SAS hold modes (`vessel.auto_pilot.sas_mode`) may not be available for all probe cores. If unavailable, use `auto_pilot.engage()` with explicit target vectors.
- Time warp is available directly: `conn.space_center.physics_warp_factor` (0–3, physics warp) and `conn.space_center.rails_warp_factor` (0–7, on-rails warp). Use rails warp during stable coasts; set back to 0 before any burn. Do not warp during staging or attitude changes.
- The kRPC connection may drop if KSP loses focus. Wrap long-running loops in a reconnect handler.

---

*Good luck.*

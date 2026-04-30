# Spacecraft Control: Throttle, Staging, Autopilot, and Burn Execution

## Basic Controls

```python
control = vessel.control
control.throttle = 1.0    # 0.0–1.0
control.sas = True
control.rcs = False
```

## Autopilot

```python
ap = vessel.auto_pilot
ap.engage()

# Ascent — point by pitch and heading:
ap.target_pitch_and_heading(90.0, 90.0)   # straight up, east

# Maneuver node — point at node's burn direction:
ap.reference_frame = node.reference_frame
ap.target_direction = (0.0, 1.0, 0.0)     # prograde in node frame
ap.wait()   # blocks until pointing error < threshold

ap.disengage()
```

`ap.wait()` is more reliable than a fixed sleep. For nodes, always call it
before opening throttle.

## Gravity Turn Profile

Pitch transitions from 90° (vertical) to ~0° (horizontal) as altitude climbs:

```python
def gravity_turn_pitch(altitude):
    if altitude < 1_000:
        return 90.0
    elif altitude < 45_000:
        frac = (altitude - 1_000) / (45_000 - 1_000)
        return 90.0 - 90.0 * frac
    else:
        return 0.0
```

Apply `ap.target_pitch_and_heading(pitch, 90)` every loop iteration.
Throttle back to 0.5–0.8 when dynamic pressure exceeds 20,000 Pa.

## Staging

```python
control.activate_next_stage()
current_stage = control.current_stage   # counts down

# Safe staging check — enforce minimum 2 s between stage events:
def stage_depleted(vessel):
    engines = [e for e in vessel.parts.engines if e.active]
    if not engines:
        return True
    return all(not e.has_fuel for e in engines)
```

After staging, wait at least 2 s before staging again. Decouplers need
clearance time before the next engine fires.

**Important:** after a staging event during a burn, `node.remaining_delta_v`
may read stale or incorrect values because the node was created with the
pre-staging mass. See Burn Execution below for how to handle this.

## Thrust and Mass

```python
vessel.available_thrust   # N, at current throttle settings
vessel.thrust             # N, current actual thrust
vessel.mass               # kg, includes fuel
vessel.specific_impulse   # Isp in seconds (multiply by 9.82 for exhaust velocity)

# TWR at Kerbin surface:
twr = vessel.available_thrust / (vessel.mass * 9.81)
```

## Burn Execution — Correct Pattern

**Never rely solely on `node.remaining_delta_v` to stop a burn.**
After staging, the node dV tracker can give nonsense values or fail to
reach zero, causing the burn to run indefinitely.

Use a dual-condition stop: `remaining_delta_v` AND a velocity-magnitude
fallback computed before the burn starts.

```python
import math, time

def execute_node(conn, vessel, node, rdv_stream):
    """
    Execute a maneuver node safely.
    rdv_stream = conn.add_stream(getattr, node, 'remaining_delta_v')
    """
    ap = vessel.auto_pilot
    ap.reference_frame = node.reference_frame
    ap.target_direction = (0.0, 1.0, 0.0)
    ap.engage()
    ap.wait()

    # Compute expected dV and a velocity-based stop target
    target_dv    = node.delta_v           # m/s to deliver
    start_speed  = vessel.orbit.speed     # m/s before burn

    # Half-burn lead: start early so node is centred on optimal point
    isp    = vessel.specific_impulse * 9.82
    thrust = max(vessel.available_thrust, 1.0)
    m0     = vessel.mass
    mf     = m0 / math.exp(target_dv / isp)
    bt     = (m0 - mf) / (thrust / isp)
    burn_start_ut = node.ut - bt / 2.0

    # Warp to burn start
    lead = 10.0
    if conn.space_center.ut < burn_start_ut - lead:
        conn.space_center.warp_to(burn_start_ut - lead)
    while conn.space_center.ut < burn_start_ut:
        time.sleep(0.05)

    vessel.control.throttle = 1.0
    staged_during_burn = False

    while True:
        rdv = rdv_stream()
        speed_delta = abs(vessel.orbit.speed - start_speed)

        # Primary stop: remaining dV small
        if rdv < 0.5:
            break

        # Fallback stop: we have delivered the expected dV by velocity change
        if speed_delta >= target_dv * 0.98:
            break

        # Throttle down as we approach target to avoid overshoot
        if rdv < 5.0:
            vessel.control.throttle = 0.05
        elif rdv < 20.0:
            vessel.control.throttle = 0.15
        elif rdv < 50.0:
            vessel.control.throttle = 0.35

        time.sleep(0.05)

    vessel.control.throttle = 0.0
    node.remove()
    time.sleep(0.5)
```

## Fuel and Resource Checking

```python
res = vessel.resources
lf  = res.amount("LiquidFuel")
ox  = res.amount("Oxidizer")
lf_max = res.max("LiquidFuel")

fuel_pct = 100.0 * (lf + ox) / max(res.max("LiquidFuel") + res.max("Oxidizer"), 1)
```

## Telemetry Log Row

Log this every 5 s of game time. All values come from correct sources:

```python
def log_row(f, vessel, sc, launch_ut, phase):
    met   = sc.ut - launch_ut
    surf  = vessel.flight(vessel.surface_reference_frame)
    orbit = vessel.orbit
    res   = vessel.resources
    total     = res.max("LiquidFuel") + res.max("Oxidizer")
    remaining = res.amount("LiquidFuel") + res.amount("Oxidizer")
    fuel_pct  = 100.0 * remaining / max(total, 1.0)
    row = (
        f"[T+{met:.0f}s] ALT={surf.mean_altitude:.0f}m "
        f"SURF_ALT={surf.surface_altitude:.0f}m "
        f"SPD={orbit.speed:.1f}m/s "          # ← orbit.speed, not flight.speed
        f"AP={orbit.apoapsis_altitude:.0f}m "
        f"PE={orbit.periapsis_altitude:.0f}m "
        f"BODY={orbit.body.name} "
        f"FUEL={fuel_pct:.1f}% "
        f"PHASE={phase} "
        f"THROTTLE={vessel.control.throttle:.2f} "
        f"STAGE={vessel.control.current_stage}\n"
    )
    f.write(row)
    f.flush()
```

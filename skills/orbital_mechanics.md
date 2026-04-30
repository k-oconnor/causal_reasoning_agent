# Orbital Mechanics: Orbits, Burns, and Transfers

## Orbit Properties

```python
orbit = vessel.orbit

orbit.apoapsis_altitude      # m above sea level
orbit.periapsis_altitude     # m above sea level
orbit.apoapsis               # m from body centre
orbit.periapsis              # m from body centre
orbit.semi_major_axis        # m
orbit.speed                  # m/s orbital speed — USE THIS for telemetry
orbit.time_to_apoapsis       # s until apoapsis
orbit.time_to_periapsis      # s until periapsis
orbit.period                 # orbital period in s

orbit.body                   # CelestialBody currently orbiting
orbit.body.name              # "Kerbin", "Mun", etc.
orbit.eccentricity           # 0 = circular, <1 = elliptical, >=1 = hyperbolic
```

**Hyperbolic escape detection:**
```python
if orbit.eccentricity >= 1.0:
    # vessel is on escape trajectory — abort or correct immediately
```

An apoapsis that goes to millions of km or goes negative means you are
on a hyperbolic orbit. Stop burning immediately.

## Vis-Viva Equation

Speed at any point in an orbit:

```python
import math

def vis_viva(mu, r, a):
    """Speed at distance r from body centre, in orbit with semi-major axis a."""
    return math.sqrt(mu * (2.0 / r - 1.0 / a))
```

For a circular orbit `a = r`, giving `sqrt(mu / r)`.

## Circularization Delta-V

Burn at apoapsis to raise periapsis to apoapsis altitude:

```python
mu = vessel.orbit.body.gravitational_parameter
r  = vessel.orbit.apoapsis          # burn at apoapsis: r = apoapsis distance from centre
a1 = vessel.orbit.semi_major_axis   # current elliptical orbit
a2 = r                              # target circular orbit (a = r)

v1 = vis_viva(mu, r, a1)
v2 = vis_viva(mu, r, a2)           # = sqrt(mu / r) for circular
delta_v = v2 - v1                  # positive = prograde burn
```

Create the node at `sc.ut + vessel.orbit.time_to_apoapsis` with
`prograde=delta_v`.

**Sanity check before burning:** confirm `delta_v > 0` and `delta_v < 500`.
A value outside this range for a KSP Mun mission indicates a calculation
error — do not fire.

## Maneuver Nodes

```python
node = vessel.control.add_node(
    sc.ut + vessel.orbit.time_to_apoapsis,
    prograde=delta_v,
    normal=0.0,
    radial=0.0,
)

node.ut                  # UT of the burn
node.delta_v             # total magnitude at creation time
node.remaining_delta_v   # decreases during burn (use as stream)
node.orbit               # predicted orbit after this node
node.remove()            # always remove after burn completes
```

**Stream `remaining_delta_v` for burn control:**
```python
rdv_stream = conn.add_stream(getattr, node, "remaining_delta_v")
```

**Known limitation:** `remaining_delta_v` can give incorrect values after
a staging event during the burn (the node was sized for pre-staging mass).
Always use a velocity-fallback stop condition. See `spacecraft_control.md`.

## Burn Time Estimation

```python
def burn_time(vessel, delta_v):
    thrust = max(vessel.available_thrust, 1.0)
    isp    = vessel.specific_impulse * 9.82
    m0     = vessel.mass
    mf     = m0 / math.exp(delta_v / isp)
    return (m0 - mf) / (thrust / isp)
```

Start the burn `burn_time / 2` seconds before the node UT.

## SOI Transitions

```python
orbit.time_to_soi_change        # s until SOI change; math.isnan() if none
orbit.next_orbit                # orbit object in next SOI (None if no change)
orbit.next_orbit.body.name      # e.g. "Mun"
```

Wait for SOI entry:
```python
import math, time
while math.isnan(vessel.orbit.time_to_soi_change) or \
      vessel.orbit.time_to_soi_change > 60:
    t = vessel.orbit.time_to_soi_change
    if not math.isnan(t) and t > 120:
        sc.warp_to(sc.ut + t - 60)
    time.sleep(0.5)
# now in new SOI
while vessel.orbit.body.name != "Mun":
    time.sleep(0.1)
```

## Encounter Assessment

```python
closest = vessel.orbit.distance_at_closest_approach(mun.orbit)   # m
t_close = vessel.orbit.time_of_closest_approach(mun.orbit)       # UT

# Confirm encounter: next_orbit should exist and body should be Mun
if vessel.orbit.next_orbit and vessel.orbit.next_orbit.body.name == "Mun":
    # encounter confirmed
```

## Trans-Mun Injection (TMI) — Robust Pattern

Do not use a phase-angle wait loop. It is fragile and can stall indefinitely.
Instead: compute the Hohmann dV analytically, create the node at the next
apoapsis, then numerically search small perturbations for the best encounter.

```python
mu_k    = kerbin.gravitational_parameter
r_lko   = vessel.orbit.semi_major_axis           # LKO radius
r_mun   = mun.orbit.semi_major_axis              # Mun orbit radius

a_trans = 0.5 * (r_lko + r_mun)
v_lko   = math.sqrt(mu_k / r_lko)
v_trans = math.sqrt(mu_k * (2.0 / r_lko - 1.0 / a_trans))
tmi_dv  = v_trans - v_lko

# Place node at next apoapsis
node = vessel.control.add_node(
    sc.ut + vessel.orbit.time_to_apoapsis,
    prograde=tmi_dv
)

# Refine: sweep small deltas around nominal values to maximise encounter
best_score = float("inf")
best_dv    = tmi_dv
best_dt    = 0.0
for dt in range(-120, 121, 30):
    for ddv in range(-80, 81, 20):
        node.ut       = sc.ut + vessel.orbit.time_to_apoapsis + dt
        node.prograde = tmi_dv + ddv
        try:
            nxt = node.orbit.next_orbit
            if nxt and nxt.body.name == "Mun":
                score = abs(nxt.periapsis_altitude - 30_000)
            else:
                score = vessel.orbit.distance_at_closest_approach(mun.orbit)
        except Exception:
            score = float("inf")
        if score < best_score:
            best_score, best_dv, best_dt = score, tmi_dv + ddv, dt

node.ut       = sc.ut + vessel.orbit.time_to_apoapsis + best_dt
node.prograde = best_dv
```

## Reference Frames Quick Reference

| Frame | Use |
|---|---|
| `body.non_rotating_reference_frame` | Vector maths, phase angles, inertial positions/velocities |
| `vessel.surface_reference_frame` | Altitude, vertical/horizontal speed, dynamic pressure |
| `node.reference_frame` | Pointing toward a node's burn direction |
| `body.reference_frame` | Body-fixed, surface-relative work |

**Never mix frames.** Passing a surface-frame position vector to a
non-rotating-frame function gives silent wrong answers.

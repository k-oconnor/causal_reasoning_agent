# Mission Planning: Hohmann Transfers, Phase Angles, and Corrections

## Hohmann Transfer Overview

A Hohmann transfer moves a spacecraft from one circular orbit to another
using two burns:

1. **Departure burn** (prograde) at the lower orbit raises apoapsis to the target.
2. **Capture burn** (retrograde) at the target orbit circularizes.

Transfer orbit semi-major axis:
```
a_transfer = (r_departure + r_target) / 2
```

Transfer time (half the transfer ellipse period):
```
t_transfer = π * sqrt(a_transfer³ / μ)
```

## Phase Angle for a Transfer Window

```python
import math

def required_phase_angle(mu, r_departure, r_target):
    a_transfer = 0.5 * (r_departure + r_target)
    t_transfer = math.pi * math.sqrt(a_transfer**3 / mu)
    target_angular_rate = math.sqrt(mu / r_target**3)
    return math.pi - target_angular_rate * t_transfer  # radians ahead of vessel
```

**For Mun transfers, do not wait for a phase angle.** The Mun is always
reachable within one KSP orbit (~34 minutes at 100 km LKO). Instead, compute
the Hohmann dV analytically, place the node at the next apoapsis, then
numerically sweep small perturbations to find the best encounter. See
`orbital_mechanics.md` for the full robust pattern.

## Measuring Current Phase Angle

```python
frame = parent_body.non_rotating_reference_frame
vessel_pos = vessel.position(frame)
target_pos = target_body.position(frame)
```

Use vector maths to find the signed angle from `vessel_pos` to `target_pos`
around the orbit normal:
- Orbit normal ≈ `cross(vessel_pos, vessel_velocity)`
- Signed angle accounts for prograde/retrograde direction.

## Waiting for a Window (only when phase angle is necessary)

```python
vessel_mean_motion = math.sqrt(mu / r_departure**3)
target_mean_motion = math.sqrt(mu / r_target**3)
relative_rate = vessel_mean_motion - target_mean_motion   # rad/s (positive if inner orbit)

phase_error  = (required_phase - current_phase) % (2 * math.pi)
wait_time_s  = phase_error / relative_rate
```

Then warp to `sc.ut + wait_time_s - some_lead_time`.

## Transfer Delta-V

```python
def transfer_delta_v(mu, r_departure, r_target):
    a_transfer = 0.5 * (r_departure + r_target)
    v_circular = math.sqrt(mu / r_departure)
    v_transfer = math.sqrt(mu * (2.0 / r_departure - 1.0 / a_transfer))
    return v_transfer - v_circular   # departure burn only
```

## Capture Burn (Orbit Insertion)

At the target periapsis:

```python
mu_target = target_body.gravitational_parameter
r_peri    = target_body.equatorial_radius + target_periapsis_altitude

v_hyperbolic = vis_viva(mu_target, r_peri, vessel.orbit.semi_major_axis)
v_circular   = math.sqrt(mu_target / r_peri)
delta_v      = v_hyperbolic - v_circular   # retrograde (use prograde=-delta_v in node)
```

Add the node at `sc.ut + vessel.orbit.time_to_periapsis`.

## Sanity Checks — Run Before Every Burn

1. `orbit.eccentricity < 1.0` — confirm you are not already on an escape trajectory.
2. `orbit.body.name == expected_body` — confirm SOI has not changed unexpectedly.
3. `delta_v > 0 and delta_v < 1000` — sanity-check computed dV magnitude.
4. `orbit.apoapsis_altitude < 1e9` — apoapsis going to millions of km means hyperbolic orbit.

If any check fails, abort the burn, log the failure with `write_event`, and
return control so the agent can diagnose.

## Midcourse Correction

After the transfer burn, if `vessel.orbit.distance_at_closest_approach(mun.orbit)`
is still large, apply a small correction burn at roughly half the remaining
flight time to the closest approach:

```python
best = {"score": float("inf"), "dv": (0.0, 0.0, 0.0)}
t_correct = sc.ut + 0.5 * vessel.orbit.time_of_closest_approach(mun.orbit)

for dp in range(-20, 21, 5):
    for dn in range(-20, 21, 5):
        node.ut       = t_correct
        node.prograde = dp
        node.normal   = dn
        try:
            sep = vessel.orbit.distance_at_closest_approach(mun.orbit)
        except Exception:
            sep = float("inf")
        if sep < best["score"]:
            best = {"score": sep, "dv": (dp, dn, 0.0)}

node.prograde = best["dv"][0]
node.normal   = best["dv"][1]
```

## Reference Frames Cheat Sheet

| Frame | Use |
|---|---|
| `body.non_rotating_reference_frame` | Inertial positions/velocities, phase angles, vector maths |
| `vessel.surface_reference_frame` | Flight instruments: alt, vertical speed, dynamic pressure |
| `node.reference_frame` | Pointing toward a node's burn direction |
| `body.reference_frame` | Body-fixed, surface-relative work |

**Never mix frames.** A position vector from one frame is meaningless if
passed to a function that expects a different frame.

## Typical Mun Mission dV Budget

| Phase | Typical dV |
|---|---|
| Launch to 80 km LKO | 3 200–3 600 m/s |
| Trans-Mun Injection (TMI) | 860–900 m/s |
| Mun Orbit Insertion (MOI) at 30 km | 270–290 m/s |
| Total | ~4 400–4 800 m/s |

Design your rocket with at least 4 800 m/s vacuum dV plus a 10% margin.
A vessel arriving at Mun with > 1 000 m/s remaining has plenty for MOI.
A vessel arriving with < 100 m/s has no margin for corrections.

# kRPC Basics: Connecting, Vessels, and Sensing

## Connecting

```python
import krpc

conn = krpc.connect(name="MunMissionAgent")
sc = conn.space_center
vessel = sc.active_vessel
```

## Celestial Bodies

```python
bodies = sc.bodies          # dict[str, CelestialBody]
kerbin = bodies["Kerbin"]
mun    = bodies["Mun"]

body.gravitational_parameter   # μ in m³/s²
body.equatorial_radius         # m
body.surface_gravity           # m/s²
body.sphere_of_influence       # SOI radius in m
body.non_rotating_reference_frame  # inertial frame centred on body
```

## Universal Time

```python
ut = sc.ut          # float, seconds since epoch
vessel.met          # mission elapsed time in seconds
```

Always prefer streams for values you read in a loop (see below).

## Speed — Correct Patterns

**CRITICAL: `Flight.speed` is not a reliable attribute. Do not use it.**
Use the patterns below instead.

```python
# Orbital speed (most useful for burn planning and telemetry):
orbital_speed = vessel.orbit.speed          # m/s in orbital frame

# Surface-relative speed components (for ascent guidance):
surf_flight = vessel.flight(vessel.surface_reference_frame)
vertical_speed    = surf_flight.vertical_speed    # m/s, + = ascending
horizontal_speed  = surf_flight.horizontal_speed  # m/s, surface-relative

# Total surface speed (if needed):
import math
total_surface_speed = math.sqrt(
    surf_flight.vertical_speed**2 + surf_flight.horizontal_speed**2
)
```

For telemetry logging, use `vessel.orbit.speed` for the SPD field. It is
always valid and reflects what the physics engine is actually doing.

## Altitude and Atmospheric Data

```python
surf = vessel.flight(vessel.surface_reference_frame)

surf.mean_altitude      # m above sea level
surf.surface_altitude   # m above terrain
surf.vertical_speed     # m/s (positive = ascending)
surf.horizontal_speed   # m/s (surface-relative)
surf.dynamic_pressure   # Pa (aerodynamic pressure, "Q")
surf.mach_number
```

## Streams (High-Frequency Polling)

Use streams for any value read more than once per second. Each stream call
is evaluated in the game server — far cheaper than an RPC round-trip.

```python
ut_stream    = conn.add_stream(getattr, sc, "ut")
alt_stream   = conn.add_stream(getattr, surf, "mean_altitude")
spd_stream   = conn.add_stream(getattr, vessel.orbit, "speed")   # ← correct
apo_stream   = conn.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
pe_stream    = conn.add_stream(getattr, vessel.orbit, "periapsis_altitude")
body_stream  = conn.add_stream(lambda: vessel.orbit.body.name)

current_alt = alt_stream()   # call like a function
```

Create streams once before your control loop, not inside it.

## Vessel Position and Velocity (Inertial Frame)

```python
frame = body.non_rotating_reference_frame
pos = vessel.position(frame)   # (x, y, z) in metres from body centre
vel = vessel.velocity(frame)   # (x, y, z) in m/s
```

Use `non_rotating_reference_frame` for vector maths (phase angles,
transfer windows). Use `surface_reference_frame` only for flight
instrument readings.

## Vessel Situation

```python
str(vessel.situation).lower()
# "pre_launch", "landed", "splashed", "flying", "sub_orbital",
# "orbiting", "escaping", "docked"
```

## Time Warp

```python
sc.warp_to(target_ut)        # warps to just before target_ut
sc.physics_warp_factor = 0   # cancel physics warp (set before any burn)
sc.rails_warp_factor = 0     # cancel rails warp
```

Always set both warp factors to 0 before issuing any control input.

## Writing Data to Disk from the Flight Script

The flight script runs on the operator's machine. Write telemetry to an
absolute path in the agent workspace — get this path from the agent before
generating the script.

```python
import os

WORKSPACE = r"C:\path\to\agent_workspace"   # injected by agent at write time
TEL_FILE  = os.path.join(WORKSPACE, "telemetry_attempt_1.txt")

with open(TEL_FILE, "a") as f:
    f.write(f"[T+{met:.0f}s] ALT={alt:.0f} ...\n")
    f.flush()
```

Wrap all file writes in try/except so a write failure never kills the flight.
Use try/finally to guarantee the file is closed and flushed on exception.

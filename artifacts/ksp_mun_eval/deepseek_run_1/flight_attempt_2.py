"""
KSP Mun Mission — Attempt 2
3-stage rocket: Skipper (stage 1) → Terrier (stage 2) → Spark (stage 3)
Target: Stable Mun orbit (PE >= 10 km, AP <= 500 km)
Key fix from A1: Much larger first stage (Skipper + Jumbo-64) to stage above 30 km
"""

import krpc
import math
import time
import os
import sys

# === CONFIGURATION ===
WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
N = 2

TEL_FILE    = os.path.join(WORKSPACE, f"telemetry_attempt_{N}.txt")
BURNS_FILE  = os.path.join(WORKSPACE, f"burns_attempt_{N}.txt")
EVENTS_FILE = os.path.join(WORKSPACE, f"events_attempt_{N}.txt")

# === CONNECTION ===
try:
    conn = krpc.connect(name=f"flight_attempt_{N}")
except Exception as e:
    print(f"FATAL: Could not connect to kRPC: {e}")
    sys.exit(1)

sc = conn.space_center
vessel = sc.active_vessel

# === FILE SETUP ===
tf = open(TEL_FILE, "w")
bf = open(BURNS_FILE, "w")
ef = open(EVENTS_FILE, "w")

def write_telemetry(phase):
    """Write one telemetry row. Called at most every 5 seconds."""
    try:
        surf = vessel.flight(vessel.surface_reference_frame)
        orbit = vessel.orbit
        res = vessel.resources
        total = res.max("LiquidFuel") + res.max("Oxidizer")
        remaining = res.amount("LiquidFuel") + res.amount("Oxidizer")
        fuel_pct = 100.0 * remaining / max(total, 1.0)
        met = sc.ut - launch_ut
        row = (
            f"[T+{met:.0f}s] ALT={surf.mean_altitude:.0f}m "
            f"SURF_ALT={surf.surface_altitude:.0f}m "
            f"SPD={orbit.speed:.1f}m/s "
            f"AP={orbit.apoapsis_altitude:.0f}m "
            f"PE={orbit.periapsis_altitude:.0f}m "
            f"ECC={orbit.eccentricity:.4f} "
            f"BODY={orbit.body.name} "
            f"FUEL={fuel_pct:.1f}% "
            f"PHASE={phase} "
            f"THROTTLE={vessel.control.throttle:.2f} "
            f"STAGE={vessel.control.current_stage}\n"
        )
        tf.write(row)
        tf.flush()
    except Exception as exc:
        tf.write(f"[TEL ERROR] {exc}\n")
        tf.flush()

_last_tel_time = [0.0]
def try_telemetry(phase):
    """Write telemetry if at least 5 seconds have passed."""
    global _last_tel_time
    if sc.ut - _last_tel_time[0] >= 5.0:
        _last_tel_time[0] = sc.ut
        write_telemetry(phase)

def write_event(tag, extra=""):
    """Write a milestone event."""
    try:
        met = sc.ut - launch_ut
        orbit = vessel.orbit
        alt = vessel.flight(vessel.surface_reference_frame).mean_altitude
        ef.write(
            f"[T+{met:.0f}s] EVENT={tag} "
            f"BODY={orbit.body.name} "
            f"ALT={alt:.0f}m "
            f"STAGE={vessel.control.current_stage} "
            f"{extra}\n"
        )
        ef.flush()
    except Exception as exc:
        ef.write(f"[EVENT ERROR] {exc}\n")
        ef.flush()

def write_burn_row(node):
    """Write a burn data row. Called every 0.25s during burns."""
    try:
        bf.write(
            f"UT={sc.ut:.2f} "
            f"RDV={node.remaining_delta_v:.2f} "
            f"SPD={vessel.orbit.speed:.2f} "
            f"THROTTLE={vessel.control.throttle:.2f} "
            f"STAGE={vessel.control.current_stage}\n"
        )
        bf.flush()
    except Exception as exc:
        bf.write(f"[BURN ERROR] {exc}\n")
        bf.flush()

# === UTILITY FUNCTIONS ===

def gravity_turn_pitch(altitude):
    """Return target pitch for given altitude (metres)."""
    if altitude < 1000:
        return 90.0
    elif altitude < 45000:
        frac = (altitude - 1000) / (45000 - 1000)
        return 90.0 - 90.0 * frac
    else:
        return 10.0

def vis_viva(mu, r, a):
    """Orbital speed from vis-viva equation."""
    return math.sqrt(mu * (2.0 / r - 1.0 / a))

def estimate_burn_time(target_dv):
    """Estimate burn time in seconds for a given dV."""
    isp = vessel.specific_impulse * 9.82
    thrust = max(vessel.available_thrust, 1.0)
    m0 = vessel.mass
    mf = m0 / math.exp(target_dv / isp)
    return (m0 - mf) / (thrust / isp)

def execute_node(node, target_dv):
    """
    Execute a maneuver node with dual-condition stop:
    1. remaining_delta_v < 0.5
    2. speed_delta >= target_dv * 0.98 (fallback for stale RDV)
    """
    ap = vessel.auto_pilot
    ap.reference_frame = node.reference_frame
    ap.target_direction = (0.0, 1.0, 0.0)
    ap.engage()
    ap.wait()

    start_speed = vessel.orbit.speed
    rdv_stream = conn.add_stream(getattr, node, "remaining_delta_v")

    # Estimate burn time for lead calculation
    bt = estimate_burn_time(target_dv)
    burn_start_ut = node.ut - bt / 2.0

    # Warp to burn start
    lead = 10.0
    if sc.ut < burn_start_ut - lead:
        sc.warp_to(burn_start_ut - lead)
    while sc.ut < burn_start_ut:
        time.sleep(0.05)

    vessel.control.throttle = 1.0
    write_event(f"BURN_START", f"TARGET_DV={target_dv:.1f}")

    while True:
        rdv = rdv_stream()
        speed_delta = abs(vessel.orbit.speed - start_speed)

        # Write burn data
        write_burn_row(node)
        try_telemetry("BURNING")

        # Primary stop
        if rdv < 0.5:
            break

        # Fallback stop (handles stale RDV after staging)
        if speed_delta >= target_dv * 0.98:
            write_event("BURN_STOP_FALLBACK", f"SPEED_DELTA={speed_delta:.1f} TARGET_DV={target_dv:.1f}")
            break

        # Throttle modulation near end to reduce overshoot
        if rdv < 5.0:
            vessel.control.throttle = 0.05
        elif rdv < 20.0:
            vessel.control.throttle = 0.15
        elif rdv < 50.0:
            vessel.control.throttle = 0.35

        time.sleep(0.05)

    vessel.control.throttle = 0.0
    node.remove()
    write_event("BURN_END", f"SPEED_DELTA={abs(vessel.orbit.speed - start_speed):.1f}")
    time.sleep(0.5)

def stage_if_depleted():
    """Stage if current stage engines have no fuel. FIXED: guards against endless staging."""
    if vessel.control.current_stage <= 0:
        return False
    try:
        engines = [e for e in vessel.parts.engines if e.active]
        if not engines:
            write_event("STAGING", "NO_ACTIVE_ENGINES")
            vessel.control.activate_next_stage()
            time.sleep(1.0)
            return True
        if all(not e.has_fuel for e in engines):
            write_event("STAGING", "FUEL_DEPLETED")
            vessel.control.activate_next_stage()
            time.sleep(1.0)
            return True
    except Exception as exc:
        write_event("STAGING_ERROR", str(exc))
    return False

# === MAIN MISSION LOOP ===

try:
    launch_ut = sc.ut
    write_event("LAUNCH")

    # ============================================================
    # PHASE 1: LAUNCH AND GRAVITY TURN
    # ============================================================
    print("=== PHASE 1: LAUNCH ===")

    # SAS on, engage autopilot pointing straight up
    vessel.control.sas = True
    ap = vessel.auto_pilot
    ap.engage()
    ap.target_pitch_and_heading(90.0, 90.0)

    # Throttle up and stage
    vessel.control.throttle = 1.0
    time.sleep(0.5)
    vessel.control.activate_next_stage()
    write_event("LIFTOFF")

    # Ascent loop
    target_ap = 85000  # 85 km target apoapsis

    while True:
        surf = vessel.flight(vessel.surface_reference_frame)
        orbit = vessel.orbit
        alt = surf.mean_altitude
        ap_alt = orbit.apoapsis_altitude
        dyn_q = surf.dynamic_pressure

        try_telemetry("ASCENT")

        # Gravity turn
        pitch = gravity_turn_pitch(alt)
        ap.target_pitch_and_heading(pitch, 90.0)

        # Check for staging
        stage_if_depleted()

        # Throttle back at high dynamic pressure
        if dyn_q > 20000:
            vessel.control.throttle = max(0.5, vessel.control.throttle * 0.95)

        # Check if we've reached target apoapsis
        if ap_alt >= target_ap:
            write_event("APOAPSIS_REACHED", f"AP={ap_alt:.0f}m")
            break

        # Safety: don't leave atmosphere before apoapsis is set
        if alt > 68000 and ap_alt < target_ap:
            vessel.control.throttle = 1.0

        time.sleep(0.1)

    # Cut engines
    vessel.control.throttle = 0.0
    write_event("ENGINE_CUT", f"AP={vessel.orbit.apoapsis_altitude:.0f}m ALT={surf.mean_altitude:.0f}m")

    # Coast to apoapsis
    print("=== COASTING TO APOAPSIS ===")
    write_event("APOAPSIS_COAST_START")

    while vessel.orbit.time_to_apoapsis > 10:
        try_telemetry("APOAPSIS_COAST")
        stage_if_depleted()
        time.sleep(0.5)

    # ============================================================
    # PHASE 2: CIRCULARIZATION BURN
    # ============================================================
    print("=== PHASE 2: CIRCULARIZATION ===")

    # Compute circularization dV
    mu_k = vessel.orbit.body.gravitational_parameter
    r_ap = vessel.orbit.apoapsis  # distance from body centre at apoapsis
    a1 = vessel.orbit.semi_major_axis
    a2 = r_ap  # target circular orbit

    v1 = vis_viva(mu_k, r_ap, a1)
    v2 = vis_viva(mu_k, r_ap, a2)  # = sqrt(mu / r) for circular
    circ_dv = v2 - v1

    write_event("CIRC_DV_COMPUTED", f"dV={circ_dv:.1f}m/s")

    if circ_dv < 0 or circ_dv > 500:
        write_event("CIRC_DV_SANITY_FAIL", f"dV={circ_dv:.1f}")
        raise RuntimeError(f"Circularization dV out of range: {circ_dv:.1f}")

    circ_node = vessel.control.add_node(
        sc.ut + vessel.orbit.time_to_apoapsis,
        prograde=circ_dv,
        normal=0.0,
        radial=0.0
    )

    execute_node(circ_node, circ_dv)

    # Verify circularization
    pe = vessel.orbit.periapsis_altitude
    ap = vessel.orbit.apoapsis_altitude
    ecc = vessel.orbit.eccentricity
    body = vessel.orbit.body.name
    write_event("CIRC_VERIFY", f"AP={ap:.0f}m PE={pe:.0f}m ECC={ecc:.4f} BODY={body}")

    if pe < 70000:
        write_event("CIRC_FAIL", f"PE too low: {pe:.0f}m")
        raise RuntimeError(f"Circularization failed: PE={pe:.0f}m < 70,000m")

    print(f"=== LKO ACHIEVED: AP={ap:.0f}m PE={pe:.0f}m ECC={ecc:.4f} ===")
    write_event("LKO_ACHIEVED")

    # ============================================================
    # PHASE 3: TRANS-MUN INJECTION (TMI)
    # ============================================================
    print("=== PHASE 3: TMI ===")

    mu_k = vessel.orbit.body.gravitational_parameter
    r_lko = vessel.orbit.semi_major_axis
    mun = sc.bodies["Mun"]
    r_mun = mun.orbit.semi_major_axis

    # Hohmann transfer dV
    a_trans = 0.5 * (r_lko + r_mun)
    v_lko = math.sqrt(mu_k / r_lko)
    v_trans = math.sqrt(mu_k * (2.0 / r_lko - 1.0 / a_trans))
    tmi_dv = v_trans - v_lko

    write_event("TMI_DV_COMPUTED", f"dV={tmi_dv:.1f}m/s")

    if tmi_dv < 100 or tmi_dv > 1500:
        write_event("TMI_DV_SANITY_FAIL", f"dV={tmi_dv:.1f}")
        raise RuntimeError(f"TMI dV out of range: {tmi_dv:.1f}")

    # Place TMI node at next apoapsis
    tmi_node = vessel.control.add_node(
        sc.ut + vessel.orbit.time_to_apoapsis,
        prograde=tmi_dv,
        normal=0.0,
        radial=0.0
    )

    # Refine: sweep nearby values for best encounter
    best_score = float("inf")
    best_dv = tmi_dv
    best_dt = 0.0

    for dt in range(-120, 121, 60):
        for ddv in range(-80, 81, 20):
            tmi_node.ut = sc.ut + vessel.orbit.time_to_apoapsis + dt
            tmi_node.prograde = tmi_dv + ddv
            try:
                nxt = tmi_node.orbit.next_orbit
                if nxt and nxt.body.name == "Mun":
                    score = abs(nxt.periapsis_altitude - 30000)
                else:
                    score = vessel.orbit.distance_at_closest_approach(mun.orbit)
            except Exception:
                score = float("inf")
            if score < best_score:
                best_score = score
                best_dv = tmi_dv + ddv
                best_dt = dt

    tmi_node.ut = sc.ut + vessel.orbit.time_to_apoapsis + best_dt
    tmi_node.prograde = best_dv
    write_event("TMI_NODE_REFINED", f"dV={best_dv:.1f}m/s dt={best_dt:.0f}s score={best_score:.0f}")

    # Execute the TMI burn
    execute_node(tmi_node, best_dv)

    # Wait for Mun encounter
    print("=== WAITING FOR MUN ENCOUNTER ===")
    write_event("TMI_COMPLETE")

    # Coast to Mun SOI
    encountered = False
    for i in range(600):  # up to 600 * 0.5 = 300 seconds polling
        try_telemetry("TMI_COAST")
        stage_if_depleted()

        # Check for Mun encounter
        nxt = vessel.orbit.next_orbit
        if nxt is not None and nxt.body.name == "Mun":
            encountered = True
            write_event("MUN_ENCOUNTER_CONFIRMED",
                        f"PE={nxt.periapsis_altitude:.0f}m AP={nxt.apoapsis_altitude:.0f}m")
            break

        # Use time warp during long coast
        t_soi = vessel.orbit.time_to_soi_change
        if not math.isnan(t_soi) and t_soi > 60:
            sc.warp_to(sc.ut + t_soi - 30)
            time.sleep(0.5)

        time.sleep(0.5)

    if not encountered:
        write_event("MUN_ENCOUNTER_FAIL", "No Mun encounter detected after TMI")
        raise RuntimeError("Failed to achieve Mun encounter")

    # Wait for SOI change
    print("=== WAITING FOR SOI CHANGE TO MUN ===")
    write_event("SOI_CHANGE_WAIT")

    while vessel.orbit.body.name != "Mun":
        try_telemetry("SOI_TRANSIT")
        t_soi = vessel.orbit.time_to_soi_change
        if not math.isnan(t_soi) and t_soi > 30:
            sc.warp_to(sc.ut + t_soi - 10)
        time.sleep(0.5)

    write_event("SOI_CHANGE_MUN", f"BODY={vessel.orbit.body.name}")

    # ============================================================
    # PHASE 4: MUN ORBIT INSERTION (MOI)
    # ============================================================
    print("=== PHASE 4: MOI ===")

    # Coast to Mun periapsis
    while vessel.orbit.time_to_periapsis > 30:
        try_telemetry("MOI_APPROACH")
        stage_if_depleted()
        t_peri = vessel.orbit.time_to_periapsis
        if not math.isnan(t_peri) and t_peri > 120:
            sc.warp_to(sc.ut + t_peri - 60)
        time.sleep(0.5)

    # Compute MOI dV at periapsis
    mu_mun = vessel.orbit.body.gravitational_parameter
    r_peri = vessel.orbit.periapsis  # distance from Mun centre at periapsis
    a_hyper = vessel.orbit.semi_major_axis
    target_pe = 30000  # 30 km target periapsis for MOI

    v_hyper = vis_viva(mu_mun, r_peri, a_hyper)
    r_circ = vessel.orbit.body.equatorial_radius + target_pe
    v_circ = math.sqrt(mu_mun / r_circ)
    moi_dv = v_hyper - v_circ  # retrograde

    write_event("MOI_DV_COMPUTED", f"dV={moi_dv:.1f}m/s r_peri={r_peri:.0f}m")

    if moi_dv < 10 or moi_dv > 2000:
        write_event("MOI_DV_SANITY_FAIL", f"dV={moi_dv:.1f}")
        raise RuntimeError(f"MOI dV out of range: {moi_dv:.1f}")

    # Create MOI node at periapsis
    moi_node = vessel.control.add_node(
        sc.ut + vessel.orbit.time_to_periapsis,
        prograde=-moi_dv,  # retrograde
        normal=0.0,
        radial=0.0
    )

    execute_node(moi_node, moi_dv)

    # Verify Mun orbit
    pe = vessel.orbit.periapsis_altitude
    ap = vessel.orbit.apoapsis_altitude
    ecc = vessel.orbit.eccentricity
    body = vessel.orbit.body.name
    write_event("MOI_VERIFY", f"AP={ap:.0f}m PE={pe:.0f}m ECC={ecc:.4f} BODY={body}")

    if body != "Mun":
        write_event("MOI_BODY_FAIL", f"Body is {body}, not Mun")
        raise RuntimeError(f"Not in Mun orbit: body={body}")

    if pe < 10000:
        write_event("MOI_PE_FAIL", f"PE too low: {pe:.0f}m")
        raise RuntimeError(f"MOI PE too low: {pe:.0f}m")

    if ap > 500000:
        write_event("MOI_AP_FAIL", f"AP too high: {ap:.0f}m")
        raise RuntimeError(f"MOI AP too high: {ap:.0f}m")

    print(f"=== MUN ORBIT ACHIEVED: AP={ap:.0f}m PE={pe:.0f}m ECC={ecc:.4f} ===")
    write_event("MUN_ORBIT_ACHIEVED")

    # ============================================================
    # PHASE 5: ORBIT CONFIRMATION (one full orbit, no thrust)
    # ============================================================
    print("=== PHASE 5: ORBIT CONFIRMATION ===")

    orbit_period = vessel.orbit.period
    orbit_start_ut = sc.ut
    vessel.control.throttle = 0.0

    while sc.ut - orbit_start_ut < orbit_period:
        try_telemetry("ORBIT_CONFIRM")
        time.sleep(5.0)

        # Verify we're still in Mun orbit
        body = vessel.orbit.body.name
        pe = vessel.orbit.periapsis_altitude
        ap = vessel.orbit.apoapsis_altitude
        throttle = vessel.control.throttle

        if body != "Mun":
            write_event("ORBIT_FAIL", f"Left Mun SOI: body={body}")
            raise RuntimeError(f"Left Mun SOI during confirmation: {body}")
        if pe < 10000:
            write_event("ORBIT_FAIL", f"PE decayed: {pe:.0f}m")
            raise RuntimeError(f"PE decayed during confirmation: {pe:.0f}m")
        if ap > 500000:
            write_event("ORBIT_FAIL", f"AP increased: {ap:.0f}m")
            raise RuntimeError(f"AP increased during confirmation: {ap:.0f}m")
        if throttle > 0.01:
            write_event("ORBIT_FAIL", f"Thrust detected: {throttle:.2f}")
            raise RuntimeError(f"Thrust detected during confirmation: {throttle:.2f}")

    write_event("ORBIT_CONFIRMED",
                f"AP={vessel.orbit.apoapsis_altitude:.0f}m PE={vessel.orbit.periapsis_altitude:.0f}m "
                f"BODY={vessel.orbit.body.name} PERIOD={vessel.orbit.period:.0f}s")

    print("=== MISSION COMPLETE ===")
    print(f"Final orbit: AP={vessel.orbit.apoapsis_altitude:.0f}m "
          f"PE={vessel.orbit.periapsis_altitude:.0f}m "
          f"ECC={vessel.orbit.eccentricity:.4f} "
          f"BODY={vessel.orbit.body.name}")

except Exception as e:
    write_event("ABORT", str(e))
    print(f"ABORT: {e}")
    vessel.control.throttle = 0.0
    raise

finally:
    tf.close()
    bf.close()
    ef.close()
    print("Data files closed.")

import os
import math
import time
import traceback
import krpc

WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
N = 4
TEL_FILE = os.path.join(WORKSPACE, f"telemetry_attempt_{N}.txt")
BURNS_FILE = os.path.join(WORKSPACE, f"burns_attempt_{N}.txt")
EVENTS_FILE = os.path.join(WORKSPACE, f"events_attempt_{N}.txt")

_last_tel_t = [-1e9]


def safe_write(f, text):
    try:
        f.write(text)
        f.flush()
    except Exception:
        pass


def refresh_vessel(sc):
    return sc.active_vessel


def total_lfo(vessel):
    try:
        res = vessel.resources
        total = res.max('LiquidFuel') + res.max('Oxidizer')
        left = res.amount('LiquidFuel') + res.amount('Oxidizer')
        return left, total
    except Exception:
        return 0.0, 1.0


def write_event(f, sc, launch_ut, tag, extra=""):
    try:
        vessel = refresh_vessel(sc)
        met = sc.ut - launch_ut
        alt = vessel.flight(vessel.surface_reference_frame).mean_altitude
        body = vessel.orbit.body.name
        safe_write(f, f"[T+{met:.0f}s] EVENT={tag} DETAIL={extra} BODY={body} ALT={alt:.0f}m\n")
    except Exception as exc:
        safe_write(f, f"[EVENT ERROR] {exc}\n")


def write_telemetry(f, sc, launch_ut, phase):
    try:
        if sc.ut - _last_tel_t[0] < 5.0:
            return
        _last_tel_t[0] = sc.ut
        vessel = refresh_vessel(sc)
        surf = vessel.flight(vessel.surface_reference_frame)
        orbit = vessel.orbit
        left, total = total_lfo(vessel)
        fuel_pct = 100.0 * left / max(total, 1.0)
        met = sc.ut - launch_ut
        row = (
            f"[T+{met:.0f}s] ALT={surf.mean_altitude:.0f}m SURF_ALT={surf.surface_altitude:.0f}m "
            f"SPD={orbit.speed:.1f}m/s AP={orbit.apoapsis_altitude:.0f}m PE={orbit.periapsis_altitude:.0f}m "
            f"BODY={orbit.body.name} FUEL={fuel_pct:.1f}% PHASE={phase} THROTTLE={vessel.control.throttle:.2f} "
            f"STAGE={vessel.control.current_stage}\n"
        )
        safe_write(f, row)
    except Exception as exc:
        safe_write(f, f"[TEL ERROR] {exc}\n")


def write_burn_row(f, sc, phase, rdv, start_speed):
    try:
        vessel = refresh_vessel(sc)
        ap = vessel.orbit.apoapsis_altitude
        pe = vessel.orbit.periapsis_altitude
        speed_delta = vessel.orbit.speed - start_speed
        row = (
            f"[T+{vessel.met:.0f}s] PHASE={phase} THROTTLE={vessel.control.throttle:.2f} "
            f"REMAINING_DV={rdv:.2f}m/s AP={ap:.0f}m PE={pe:.0f}m SPD_DELTA={speed_delta:.2f} STAGE={vessel.control.current_stage}\n"
        )
        safe_write(f, row)
    except Exception as exc:
        safe_write(f, f"[BURN ERROR] {exc}\n")


def burn_time_estimate(vessel, delta_v):
    thrust = max(vessel.available_thrust, 1.0)
    isp = max(vessel.specific_impulse * 9.82, 1.0)
    m0 = max(vessel.mass, 1.0)
    try:
        mf = m0 / math.exp(delta_v / isp)
    except OverflowError:
        mf = m0
    flow = thrust / isp
    return max((m0 - mf) / max(flow, 1e-6), 0.1)


def wait_with_telemetry(tf, sc, launch_ut, phase, target_ut):
    while sc.ut < target_ut:
        write_telemetry(tf, sc, launch_ut, phase)
        time.sleep(0.1)


def coast_until(tf, sc, launch_ut, phase, predicate, timeout=3600):
    t0 = sc.ut
    while not predicate():
        write_telemetry(tf, sc, launch_ut, phase)
        if sc.ut - t0 > timeout:
            raise RuntimeError(f"Timeout in phase {phase}")
        time.sleep(0.2)


def set_pitch_for_ascent(ap, altitude):
    if altitude < 1000:
        pitch = 90.0
    elif altitude < 45000:
        frac = (altitude - 1000.0) / 44000.0
        pitch = 90.0 - 88.0 * frac
    else:
        pitch = 2.0
    ap.target_pitch_and_heading(pitch, 90)
    return pitch


def active_srb_engines(vessel):
    srbs = []
    try:
        for e in vessel.parts.engines:
            if e.active and 'Thumper' in e.part.title:
                srbs.append(e)
    except Exception:
        return []
    return srbs


def active_non_srb_engines(vessel):
    engines = []
    try:
        for e in vessel.parts.engines:
            if e.active and 'Thumper' not in e.part.title:
                engines.append(e)
    except Exception:
        return []
    return engines


def stage_decouple_srbs(sc, ef, launch_ut):
    vessel = refresh_vessel(sc)
    vessel.control.activate_next_stage()
    time.sleep(1.0)
    write_event(ef, sc, launch_ut, f"STAGE_{refresh_vessel(sc).control.current_stage}", 'srb_separation')
    write_event(ef, sc, launch_ut, 'VESSEL_REFRESH', 'after_srb_sep')


def stage_to_upper(sc, ef, launch_ut):
    vessel = refresh_vessel(sc)
    vessel.control.activate_next_stage()
    time.sleep(1.5)
    vessel = refresh_vessel(sc)
    vessel.control.throttle = max(vessel.control.throttle, 0.0)
    write_event(ef, sc, launch_ut, f"STAGE_{vessel.control.current_stage}", 'core_sep_upper_ignite')
    write_event(ef, sc, launch_ut, 'VESSEL_REFRESH', 'after_core_sep')


def orient_to_node(sc, node):
    vessel = refresh_vessel(sc)
    ap = vessel.auto_pilot
    ap.reference_frame = node.reference_frame
    ap.target_direction = (0, 1, 0)
    ap.engage()
    time.sleep(0.5)
    return vessel, ap


def execute_node(conn, sc, tf, bf, ef, launch_ut, node, phase_name):
    vessel = refresh_vessel(sc)
    rdv_stream = conn.add_stream(getattr, node, 'remaining_delta_v')
    vessel, ap = orient_to_node(sc, node)
    target_dv = max(node.delta_v, 0.1)
    start_speed = vessel.orbit.speed
    bt = burn_time_estimate(vessel, target_dv)
    burn_start_ut = node.ut - bt / 2.0

    sc.rails_warp_factor = 0
    sc.physics_warp_factor = 0
    if sc.ut < burn_start_ut - 20:
        sc.warp_to(burn_start_ut - 15)
    wait_with_telemetry(tf, sc, launch_ut, f"{phase_name}_COAST", burn_start_ut)

    vessel, ap = orient_to_node(sc, node)
    write_event(ef, sc, launch_ut, 'VESSEL_REFRESH', f'before_{phase_name}')
    write_event(ef, sc, launch_ut, f'BURN_START:{phase_name}', f'target_dv={target_dv:.2f}')
    vessel.control.throttle = 1.0
    last_burn_log = sc.ut - 1.0

    try:
        while True:
            vessel = refresh_vessel(sc)
            rdv = rdv_stream()
            speed_delta = abs(vessel.orbit.speed - start_speed)
            write_telemetry(tf, sc, launch_ut, phase_name)
            if sc.ut - last_burn_log >= 0.25:
                write_burn_row(bf, sc, phase_name, rdv, start_speed)
                last_burn_log = sc.ut

            if rdv < 0.5:
                break
            if speed_delta >= target_dv * 0.98:
                write_event(ef, sc, launch_ut, f'BURN_STOP_FALLBACK:{phase_name}', f'speed_delta={speed_delta:.2f}')
                break
            if vessel.orbit.eccentricity >= 1.0 and phase_name in ('TMI', 'MOI', 'CIRCULARIZE'):
                write_event(ef, sc, launch_ut, f'ABORT_HYPERBOLIC:{phase_name}', f'ecc={vessel.orbit.eccentricity:.4f}')
                break

            if rdv < 5.0:
                vessel.control.throttle = 0.05
            elif rdv < 20.0:
                vessel.control.throttle = 0.15
            elif rdv < 50.0:
                vessel.control.throttle = 0.35
            else:
                vessel.control.throttle = 1.0
            time.sleep(0.05)
    finally:
        vessel = refresh_vessel(sc)
        vessel.control.throttle = 0.0
        write_burn_row(bf, sc, phase_name, 0.0, start_speed)
        write_event(ef, sc, launch_ut, f'BURN_END:{phase_name}')
        try:
            node.remove()
            write_event(ef, sc, launch_ut, f'NODE_REMOVED:{phase_name}')
        except Exception:
            pass


def circularization_dv(orbit):
    mu = orbit.body.gravitational_parameter
    r = orbit.apoapsis
    a1 = orbit.semi_major_axis
    a2 = r
    v1 = math.sqrt(mu * (2.0 / r - 1.0 / a1))
    v2 = math.sqrt(mu / r)
    return max(v2 - v1, 0.0)


def tmi_nominal_dv(orbit, mun):
    mu = orbit.body.gravitational_parameter
    r1 = orbit.semi_major_axis
    r2 = mun.orbit.semi_major_axis
    a = 0.5 * (r1 + r2)
    v1 = math.sqrt(mu / r1)
    vt = math.sqrt(mu * (2.0 / r1 - 1.0 / a))
    return max(vt - v1, 0.0)


def plan_tmi_node(sc, mun, ef, launch_ut):
    vessel = refresh_vessel(sc)
    nominal = tmi_nominal_dv(vessel.orbit, mun)
    base_ut = sc.ut + vessel.orbit.time_to_apoapsis
    node = vessel.control.add_node(base_ut, prograde=nominal)
    best_score = 1e30
    best_ut = base_ut
    best_dv = nominal
    for dt in range(-180, 181, 30):
        for ddv in range(-120, 121, 20):
            node.ut = base_ut + dt
            node.prograde = max(nominal + ddv, 10.0)
            try:
                nxt = node.orbit.next_orbit
                if nxt and nxt.body.name == 'Mun':
                    score = abs(nxt.periapsis_altitude - 30000.0)
                else:
                    score = 1e29
            except Exception:
                score = 1e30
            if score < best_score:
                best_score = score
                best_ut = node.ut
                best_dv = node.prograde
    node.ut = best_ut
    node.prograde = best_dv
    write_event(ef, sc, launch_ut, 'NODE_CREATED:TMI', f'best_dv={best_dv:.2f} score={best_score:.2f}')
    return node


def plan_moi_node(sc, ef, launch_ut, target_pe_alt=30000.0):
    vessel = refresh_vessel(sc)
    body = vessel.orbit.body
    mu = body.gravitational_parameter
    r_p = body.equatorial_radius + target_pe_alt
    try:
        a = vessel.orbit.semi_major_axis
        v_current = math.sqrt(mu * (2.0 / r_p - 1.0 / a))
    except Exception:
        v_current = vessel.orbit.speed
    v_circ = math.sqrt(mu / r_p)
    dv = max(v_current - v_circ, 0.0)
    node = vessel.control.add_node(sc.ut + vessel.orbit.time_to_periapsis, prograde=-dv)
    write_event(ef, sc, launch_ut, 'NODE_CREATED:MOI', f'dv={dv:.2f}')
    return node


def plan_trim_node(sc, ef, launch_ut, target_ap_alt=100000.0):
    vessel = refresh_vessel(sc)
    body = vessel.orbit.body
    mu = body.gravitational_parameter
    r = body.equatorial_radius + max(vessel.orbit.periapsis_altitude, 10000.0)
    a1 = vessel.orbit.semi_major_axis
    a2 = 0.5 * (r + body.equatorial_radius + target_ap_alt)
    v1 = math.sqrt(mu * (2.0 / r - 1.0 / a1))
    v2 = math.sqrt(mu * (2.0 / r - 1.0 / a2))
    dv = v2 - v1
    node = vessel.control.add_node(sc.ut + vessel.orbit.time_to_periapsis, prograde=dv)
    write_event(ef, sc, launch_ut, 'NODE_CREATED:TRIM', f'dv={dv:.2f}')
    return node


def confirm_mun_orbit(tf, sc, ef, launch_ut):
    vessel = refresh_vessel(sc)
    period = vessel.orbit.period
    start = sc.ut
    write_event(ef, sc, launch_ut, 'ORBIT_CONFIRMATION_START', f'period={period:.1f}')
    while sc.ut - start < period:
        vessel = refresh_vessel(sc)
        write_telemetry(tf, sc, launch_ut, 'MUN_ORBIT_CONFIRM')
        if vessel.control.throttle > 0.001:
            raise RuntimeError('Throttle became non-zero during orbit confirmation')
        if vessel.orbit.body.name != 'Mun':
            raise RuntimeError('Left Mun SOI during orbit confirmation')
        if vessel.orbit.periapsis_altitude < 10000:
            raise RuntimeError(f'Periapsis dropped below limit: {vessel.orbit.periapsis_altitude}')
        if vessel.orbit.apoapsis_altitude > 500000:
            raise RuntimeError(f'Apoapsis above limit: {vessel.orbit.apoapsis_altitude}')
        time.sleep(1.0)
    write_event(ef, sc, launch_ut, 'ORBIT_CONFIRMED', f'AP={refresh_vessel(sc).orbit.apoapsis_altitude:.0f} PE={refresh_vessel(sc).orbit.periapsis_altitude:.0f}')


conn = None
launch_ut_main = None
try:
    conn = krpc.connect(name='flight_attempt_4')
    sc = conn.space_center

    with open(TEL_FILE, 'w') as tf, open(BURNS_FILE, 'w') as bf, open(EVENTS_FILE, 'w') as ef:
        launch_ut_main = sc.ut
        write_event(ef, sc, launch_ut_main, 'SCRIPT_START')
        write_telemetry(tf, sc, launch_ut_main, 'PRELAUNCH')

        vessel = refresh_vessel(sc)
        ap = vessel.auto_pilot
        ap.engage()
        ap.target_pitch_and_heading(90, 90)
        vessel.control.sas = False
        vessel.control.rcs = False
        vessel.control.throttle = 1.0
        time.sleep(1.0)

        vessel.control.activate_next_stage()
        write_event(ef, sc, launch_ut_main, 'LAUNCH')
        write_event(ef, sc, launch_ut_main, f'STAGE_{refresh_vessel(sc).control.current_stage}', 'liftoff')
        write_event(ef, sc, launch_ut_main, 'VESSEL_REFRESH', 'post_launch')

        gt_started = False
        srb_sep_done = False
        upper_stage_ignited = False
        target_ap = 90000.0

        while True:
            vessel = refresh_vessel(sc)
            surf = vessel.flight(vessel.surface_reference_frame)
            alt = surf.mean_altitude
            q = surf.dynamic_pressure
            ap = vessel.auto_pilot

            if alt > 1000 and not gt_started:
                gt_started = True
                write_event(ef, sc, launch_ut_main, 'GRAVITY_TURN_START')

            set_pitch_for_ascent(ap, alt)
            vessel.control.throttle = 0.65 if q > 20000 else 1.0

            if not srb_sep_done:
                srbs = active_srb_engines(vessel)
                if srbs and all((not e.has_fuel) for e in srbs):
                    stage_decouple_srbs(sc, ef, launch_ut_main)
                    srb_sep_done = True

            if srb_sep_done and not upper_stage_ignited:
                core_engines = active_non_srb_engines(refresh_vessel(sc))
                if core_engines and all((not e.has_fuel) for e in core_engines):
                    stage_to_upper(sc, ef, launch_ut_main)
                    upper_stage_ignited = True

            if refresh_vessel(sc).orbit.apoapsis_altitude >= target_ap:
                refresh_vessel(sc).control.throttle = 0.0
                write_event(ef, sc, launch_ut_main, 'APOAPSIS_COAST_START', f'AP={refresh_vessel(sc).orbit.apoapsis_altitude:.0f}')
                break

            if alt > 70000 and refresh_vessel(sc).orbit.apoapsis_altitude < 80000:
                raise RuntimeError('Left atmosphere before setting apoapsis target')

            write_telemetry(tf, sc, launch_ut_main, 'ASCENT')
            time.sleep(0.1)

        coast_until(tf, sc, launch_ut_main, 'TO_AP_FOR_CIRC', lambda: refresh_vessel(sc).orbit.time_to_apoapsis < 25, timeout=4000)
        vessel = refresh_vessel(sc)
        write_event(ef, sc, launch_ut_main, 'VESSEL_REFRESH', 'before_circularization_node')
        dv_circ = circularization_dv(vessel.orbit)
        if not (0 < dv_circ < 500):
            raise RuntimeError(f'Circularization dV sanity check failed: {dv_circ}')
        node = vessel.control.add_node(sc.ut + vessel.orbit.time_to_apoapsis, prograde=dv_circ)
        write_event(ef, sc, launch_ut_main, 'NODE_CREATED:CIRCULARIZE', f'dv={dv_circ:.2f}')
        execute_node(conn, sc, tf, bf, ef, launch_ut_main, node, 'CIRCULARIZE')

        vessel = refresh_vessel(sc)
        if vessel.orbit.body.name != 'Kerbin' or vessel.orbit.periapsis_altitude < 75000:
            raise RuntimeError(f'LKO not achieved: body={vessel.orbit.body.name} pe={vessel.orbit.periapsis_altitude}')
        write_event(ef, sc, launch_ut_main, 'LKO_CONFIRMED', f'AP={vessel.orbit.apoapsis_altitude:.0f} PE={vessel.orbit.periapsis_altitude:.0f}')

        mun = sc.bodies['Mun']
        node = plan_tmi_node(sc, mun, ef, launch_ut_main)
        execute_node(conn, sc, tf, bf, ef, launch_ut_main, node, 'TMI')

        vessel = refresh_vessel(sc)
        try:
            if vessel.orbit.next_orbit and vessel.orbit.next_orbit.body.name == 'Mun':
                write_event(ef, sc, launch_ut_main, 'ENCOUNTER_CONFIRMED', f'pe={vessel.orbit.next_orbit.periapsis_altitude:.0f}')
        except Exception:
            pass

        t0 = sc.ut
        while refresh_vessel(sc).orbit.body.name != 'Mun':
            write_telemetry(tf, sc, launch_ut_main, 'TMI_COAST')
            vessel = refresh_vessel(sc)
            try:
                t_soi = vessel.orbit.time_to_soi_change
                if not math.isnan(t_soi) and t_soi > 120:
                    sc.warp_to(sc.ut + t_soi - 60)
            except Exception:
                pass
            if sc.ut - t0 > 200000:
                raise RuntimeError('Timed out waiting for Mun SOI change')
            time.sleep(0.2)

        write_event(ef, sc, launch_ut_main, 'SOI_CHANGE:Mun')
        moi_node = plan_moi_node(sc, ef, launch_ut_main, target_pe_alt=30000.0)
        execute_node(conn, sc, tf, bf, ef, launch_ut_main, moi_node, 'MOI')

        vessel = refresh_vessel(sc)
        if vessel.orbit.body.name != 'Mun':
            raise RuntimeError('After MOI, body is not Mun')

        if vessel.orbit.periapsis_altitude < 10000 or vessel.orbit.apoapsis_altitude > 500000:
            trim_node = plan_trim_node(sc, ef, launch_ut_main, target_ap_alt=min(max(vessel.orbit.apoapsis_altitude, 30000.0), 120000.0))
            execute_node(conn, sc, tf, bf, ef, launch_ut_main, trim_node, 'TRIM')

        vessel = refresh_vessel(sc)
        if vessel.orbit.body.name != 'Mun':
            raise RuntimeError('Trim left Mun SOI unexpectedly')
        if vessel.orbit.periapsis_altitude < 10000 or vessel.orbit.apoapsis_altitude > 500000:
            raise RuntimeError(f'Mun orbit out of bounds: AP={vessel.orbit.apoapsis_altitude} PE={vessel.orbit.periapsis_altitude}')

        confirm_mun_orbit(tf, sc, ef, launch_ut_main)
        write_telemetry(tf, sc, launch_ut_main, 'MISSION_COMPLETE')

except Exception as exc:
    try:
        if conn is not None:
            sc = conn.space_center
            base_ut = launch_ut_main if launch_ut_main is not None else sc.ut
            with open(EVENTS_FILE, 'a') as ef:
                write_event(ef, sc, base_ut, 'SCRIPT_EXCEPTION', repr(exc))
                safe_write(ef, traceback.format_exc() + "\n")
            with open(TEL_FILE, 'a') as tf:
                write_telemetry(tf, sc, base_ut, 'EXCEPTION')
    except Exception:
        pass
    raise

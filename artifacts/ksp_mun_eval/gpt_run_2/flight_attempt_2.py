import os
import math
import time
import traceback
import krpc

WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
N = 2
TEL_FILE = os.path.join(WORKSPACE, f"telemetry_attempt_{N}.txt")
BURNS_FILE = os.path.join(WORKSPACE, f"burns_attempt_{N}.txt")
EVENTS_FILE = os.path.join(WORKSPACE, f"events_attempt_{N}.txt")

_last_tel = -1e9


def safe_write(f, text):
    try:
        f.write(text)
        f.flush()
    except Exception:
        pass


def get_vessel(sc):
    return sc.active_vessel


def total_lfo(vessel):
    try:
        res = vessel.resources
        left = res.amount('LiquidFuel') + res.amount('Oxidizer')
        cap = res.max('LiquidFuel') + res.max('Oxidizer')
        return left, cap
    except Exception:
        return 0.0, 1.0


def fuel_pct(vessel):
    left, cap = total_lfo(vessel)
    return 100.0 * left / max(cap, 1.0)


def write_event(ef, vessel, sc, launch_ut, event_type, detail=''):
    met = sc.ut - launch_ut
    try:
        alt = vessel.flight(vessel.surface_reference_frame).mean_altitude
    except Exception:
        alt = float('nan')
    try:
        body = vessel.orbit.body.name
    except Exception:
        body = 'UNKNOWN'
    safe_write(ef, f"[T+{met:.0f}s] EVENT={event_type} DETAIL={detail} BODY={body} ALT={alt:.0f}m\n")


def write_telemetry(tf, vessel, sc, launch_ut, phase):
    global _last_tel
    if sc.ut - _last_tel < 5.0:
        return
    _last_tel = sc.ut
    try:
        surf = vessel.flight(vessel.surface_reference_frame)
        orbit = vessel.orbit
        safe_write(tf, (
            f"[T+{sc.ut-launch_ut:.0f}s] ALT={surf.mean_altitude:.0f}m "
            f"SURF_ALT={surf.surface_altitude:.0f}m "
            f"SPD={orbit.speed:.1f}m/s "
            f"AP={orbit.apoapsis_altitude:.0f}m "
            f"PE={orbit.periapsis_altitude:.0f}m "
            f"BODY={orbit.body.name} "
            f"FUEL={fuel_pct(vessel):.1f}% "
            f"PHASE={phase} "
            f"THROTTLE={vessel.control.throttle:.2f} "
            f"STAGE={vessel.control.current_stage}\n"
        ))
    except Exception as exc:
        safe_write(tf, f"[TEL ERROR] {exc}\n")


def write_burn_row(bf, vessel, sc, launch_ut, phase, rdv):
    try:
        safe_write(bf, (
            f"[T+{sc.ut-launch_ut:.2f}s] PHASE={phase} THROTTLE={vessel.control.throttle:.2f} "
            f"REMAINING_DV={rdv:.2f} AP={vessel.orbit.apoapsis_altitude:.0f}m PE={vessel.orbit.periapsis_altitude:.0f}m\n"
        ))
    except Exception as exc:
        safe_write(bf, f"[BURN ERROR] {exc}\n")


def gravity_turn_pitch(altitude):
    if altitude < 1000:
        return 90.0
    if altitude < 12000:
        frac = (altitude - 1000.0) / 11000.0
        return 90.0 - 35.0 * frac
    if altitude < 35000:
        frac = (altitude - 12000.0) / 23000.0
        return 55.0 - 45.0 * frac
    return 10.0


def wait_for_pointing(ap, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if ap.error < 3.0:
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def estimate_burn_time(vessel, delta_v):
    thrust = max(vessel.available_thrust, 1.0)
    isp = max(vessel.specific_impulse, 1.0) * 9.82
    m0 = vessel.mass
    mf = m0 / math.exp(max(delta_v, 0.1) / isp)
    return max((m0 - mf) / (thrust / isp), 0.5)


def safe_zero_throttle(sc):
    try:
        sc.active_vessel.control.throttle = 0.0
    except Exception:
        pass


def stage_and_refresh(sc, ef, launch_ut, detail):
    vessel = sc.active_vessel
    vessel.control.activate_next_stage()
    time.sleep(1.5)
    vessel = sc.active_vessel
    write_event(ef, vessel, sc, launch_ut, 'STAGE', detail)
    return vessel


def execute_node(conn, sc, ef, tf, bf, launch_ut, node, phase):
    vessel = get_vessel(sc)
    vessel.control.throttle = 0.0
    ap = vessel.auto_pilot
    ap.reference_frame = node.reference_frame
    ap.target_direction = (0, 1, 0)
    ap.engage()
    wait_for_pointing(ap)

    target_dv = max(node.delta_v, 0.1)
    start_speed = vessel.orbit.speed
    burn_time = estimate_burn_time(vessel, target_dv)
    burn_start_ut = node.ut - burn_time / 2.0
    write_event(ef, vessel, sc, launch_ut, 'NODE_EXECUTE', f'{phase} target_dv={target_dv:.1f} burn_time={burn_time:.1f}')

    sc.rails_warp_factor = 0
    sc.physics_warp_factor = 0
    if sc.ut < burn_start_ut - 20:
        sc.warp_to(burn_start_ut - 10)
    while sc.ut < burn_start_ut:
        vessel = get_vessel(sc)
        safe_zero_throttle(sc)
        write_telemetry(tf, vessel, sc, launch_ut, phase + '_COAST')
        time.sleep(0.1)

    vessel = get_vessel(sc)
    rdv_stream = conn.add_stream(getattr, node, 'remaining_delta_v')
    vessel.control.throttle = 1.0
    write_event(ef, vessel, sc, launch_ut, 'BURN_START', phase)
    last_log = -1e9

    while True:
        vessel = get_vessel(sc)
        rdv = rdv_stream()
        delivered = abs(vessel.orbit.speed - start_speed)
        if sc.ut - last_log >= 0.25:
            write_burn_row(bf, vessel, sc, launch_ut, phase, rdv)
            last_log = sc.ut
        write_telemetry(tf, vessel, sc, launch_ut, phase)

        if rdv < 0.5:
            break
        if delivered >= target_dv * 0.98:
            write_event(ef, vessel, sc, launch_ut, 'BURN_FALLBACK_STOP', f'{phase} delivered={delivered:.1f} target={target_dv:.1f}')
            break

        if rdv < 5:
            vessel.control.throttle = 0.05
        elif rdv < 20:
            vessel.control.throttle = 0.15
        elif rdv < 50:
            vessel.control.throttle = 0.35
        else:
            vessel.control.throttle = 1.0
        time.sleep(0.05)

    safe_zero_throttle(sc)
    vessel = get_vessel(sc)
    write_event(ef, vessel, sc, launch_ut, 'BURN_END', phase)
    try:
        node.remove()
        write_event(ef, vessel, sc, launch_ut, 'NODE_REMOVED', phase)
    except Exception:
        pass
    time.sleep(0.5)


def main():
    conn = krpc.connect(name=f'flight_attempt_{N}')
    sc = conn.space_center
    kerbin = sc.bodies['Kerbin']
    mun = sc.bodies['Mun']
    vessel = get_vessel(sc)

    with open(TEL_FILE, 'w') as tf, open(BURNS_FILE, 'w') as bf, open(EVENTS_FILE, 'w') as ef:
        launch_ut = sc.ut
        write_event(ef, vessel, sc, launch_ut, 'SCRIPT_START', 'attempt_2')
        write_telemetry(tf, vessel, sc, launch_ut, 'INIT')

        vessel.auto_pilot.engage()
        vessel.auto_pilot.target_pitch_and_heading(90, 90)
        vessel.control.sas = False
        vessel.control.rcs = False
        vessel.control.throttle = 1.0
        vessel.control.activate_next_stage()
        write_event(ef, vessel, sc, launch_ut, 'LAUNCH', 'ignite_all')

        gravity_turn_logged = False
        boosters_sep = False
        core_sep = False
        upper_sep = False
        max_q = 0.0
        target_ap = 85000.0

        while True:
            vessel = get_vessel(sc)
            surf = vessel.flight(vessel.surface_reference_frame)
            alt = surf.mean_altitude
            q = surf.dynamic_pressure
            ap_alt = vessel.orbit.apoapsis_altitude
            if q > max_q:
                max_q = q
            if q > 22000:
                vessel.control.throttle = 0.55
            elif q > 12000:
                vessel.control.throttle = 0.75
            else:
                vessel.control.throttle = 1.0

            pitch = gravity_turn_pitch(alt)
            vessel.auto_pilot.target_pitch_and_heading(pitch, 90)
            if (not gravity_turn_logged) and alt > 1500:
                write_event(ef, vessel, sc, launch_ut, 'GRAVITY_TURN_START', f'pitch={pitch:.1f}')
                gravity_turn_logged = True

            write_telemetry(tf, vessel, sc, launch_ut, 'ASCENT')

            if (not boosters_sep) and alt > 8000 and vessel.thrust < 400000:
                vessel = stage_and_refresh(sc, ef, launch_ut, 'booster_separation')
                boosters_sep = True

            if ap_alt >= target_ap:
                safe_zero_throttle(sc)
                vessel = get_vessel(sc)
                write_event(ef, vessel, sc, launch_ut, 'AP_TARGET_REACHED', f'AP={ap_alt:.0f}')
                break

            if (not core_sep) and vessel.thrust < 1.0 and fuel_pct(vessel) < 60:
                vessel = stage_and_refresh(sc, ef, launch_ut, 'core_to_bobcat')
                core_sep = True

            if core_sep and (not upper_sep) and vessel.thrust < 1.0 and fuel_pct(vessel) < 25:
                vessel = stage_and_refresh(sc, ef, launch_ut, 'bobcat_to_cheetah')
                upper_sep = True

            if fuel_pct(vessel) <= 0.2 and ap_alt < 70000:
                write_event(ef, vessel, sc, launch_ut, 'ABORT', 'fuel_depleted_before_orbit')
                return
            time.sleep(0.1)

        vessel = get_vessel(sc)
        safe_zero_throttle(sc)
        write_event(ef, vessel, sc, launch_ut, 'MAX_Q', f'{max_q:.0f}')
        write_event(ef, vessel, sc, launch_ut, 'APOAPSIS_COAST_START', '')

        while vessel.orbit.time_to_apoapsis > 25:
            vessel = get_vessel(sc)
            safe_zero_throttle(sc)
            write_telemetry(tf, vessel, sc, launch_ut, 'COAST_TO_AP')
            time.sleep(0.2)

        vessel = get_vessel(sc)
        mu = kerbin.gravitational_parameter
        r = vessel.orbit.apoapsis
        a1 = vessel.orbit.semi_major_axis
        v1 = math.sqrt(mu * (2.0 / r - 1.0 / a1))
        v2 = math.sqrt(mu / r)
        circ_dv = v2 - v1
        node = vessel.control.add_node(sc.ut + vessel.orbit.time_to_apoapsis, prograde=circ_dv)
        write_event(ef, vessel, sc, launch_ut, 'NODE_CREATED', f'CIRCULARIZE dv={circ_dv:.1f}')
        execute_node(conn, sc, ef, tf, bf, launch_ut, node, 'CIRCULARIZE')

        vessel = get_vessel(sc)
        safe_zero_throttle(sc)
        write_telemetry(tf, vessel, sc, launch_ut, 'POST_CIRC')
        if vessel.orbit.body.name != 'Kerbin' or vessel.orbit.periapsis_altitude < 75000:
            write_event(ef, vessel, sc, launch_ut, 'ABORT', f'failed_lko AP={vessel.orbit.apoapsis_altitude:.0f} PE={vessel.orbit.periapsis_altitude:.0f}')
            return
        write_event(ef, vessel, sc, launch_ut, 'LKO_CONFIRMED', f'AP={vessel.orbit.apoapsis_altitude:.0f} PE={vessel.orbit.periapsis_altitude:.0f}')

        r_lko = vessel.orbit.semi_major_axis
        r_mun = mun.orbit.semi_major_axis
        a_trans = 0.5 * (r_lko + r_mun)
        v_lko = math.sqrt(mu / r_lko)
        v_trans = math.sqrt(mu * (2.0 / r_lko - 1.0 / a_trans))
        tmi_dv = v_trans - v_lko
        base_ut = sc.ut + vessel.orbit.time_to_apoapsis
        node = vessel.control.add_node(base_ut, prograde=tmi_dv)
        best = None
        best_score = float('inf')
        for dt in range(-180, 181, 20):
            for ddv in range(-120, 121, 10):
                try:
                    node.ut = base_ut + dt
                    node.prograde = tmi_dv + ddv
                    nxt = node.orbit.next_orbit
                    if nxt and nxt.body.name == 'Mun':
                        score = abs(nxt.periapsis_altitude - 30000)
                    else:
                        score = 1e12
                except Exception:
                    score = 1e12
                if score < best_score:
                    best_score = score
                    best = (base_ut + dt, tmi_dv + ddv)
        if best is None or best_score >= 1e11:
            try:
                node.remove()
            except Exception:
                pass
            write_event(ef, vessel, sc, launch_ut, 'ABORT', 'tmi_sweep_no_encounter')
            return
        node.ut = best[0]
        node.prograde = best[1]
        write_event(ef, vessel, sc, launch_ut, 'NODE_REFINED', f'TMI ut={best[0]:.1f} dv={best[1]:.1f} score={best_score:.0f}')
        execute_node(conn, sc, ef, tf, bf, launch_ut, node, 'TMI')

        vessel = get_vessel(sc)
        safe_zero_throttle(sc)
        write_telemetry(tf, vessel, sc, launch_ut, 'POST_TMI')
        if not (vessel.orbit.next_orbit and vessel.orbit.next_orbit.body.name == 'Mun') and vessel.orbit.body.name == 'Kerbin':
            write_event(ef, vessel, sc, launch_ut, 'ABORT', 'no_mun_encounter_after_tmi')
            return
        write_event(ef, vessel, sc, launch_ut, 'MUN_ENCOUNTER_CONFIRMED', '')

        current_body = vessel.orbit.body.name
        while vessel.orbit.body.name == 'Kerbin':
            vessel = get_vessel(sc)
            safe_zero_throttle(sc)
            write_telemetry(tf, vessel, sc, launch_ut, 'COAST_TO_MUN')
            t_soi = vessel.orbit.time_to_soi_change
            if not math.isnan(t_soi) and t_soi > 120:
                sc.warp_to(sc.ut + t_soi - 60)
            time.sleep(0.2)
            if vessel.orbit.body.name != current_body:
                current_body = vessel.orbit.body.name
                write_event(ef, vessel, sc, launch_ut, 'SOI_CHANGE', current_body)

        vessel = get_vessel(sc)
        if vessel.orbit.body.name != 'Mun':
            write_event(ef, vessel, sc, launch_ut, 'ABORT', f'unexpected_body_{vessel.orbit.body.name}')
            return

        while vessel.orbit.time_to_periapsis > 120:
            vessel = get_vessel(sc)
            safe_zero_throttle(sc)
            write_telemetry(tf, vessel, sc, launch_ut, 'PLAN_MOI')
            if vessel.orbit.time_to_periapsis > 300:
                sc.warp_to(sc.ut + vessel.orbit.time_to_periapsis - 90)
            time.sleep(0.2)

        vessel = get_vessel(sc)
        mu_m = mun.gravitational_parameter
        r_peri = vessel.orbit.periapsis
        a1 = vessel.orbit.semi_major_axis
        target_r = mun.equatorial_radius + 50000
        v_peri = math.sqrt(mu_m * (2.0 / r_peri - 1.0 / a1))
        v_target = math.sqrt(mu_m * (2.0 / r_peri - 1.0 / ((r_peri + target_r) / 2.0)))
        moi_dv = max(v_peri - v_target, 0.0)
        node = vessel.control.add_node(sc.ut + vessel.orbit.time_to_periapsis, prograde=-moi_dv)
        write_event(ef, vessel, sc, launch_ut, 'NODE_CREATED', f'MOI dv={moi_dv:.1f}')
        execute_node(conn, sc, ef, tf, bf, launch_ut, node, 'MOI')

        vessel = get_vessel(sc)
        safe_zero_throttle(sc)
        final_ap = vessel.orbit.apoapsis_altitude
        final_pe = vessel.orbit.periapsis_altitude
        write_event(ef, vessel, sc, launch_ut, 'ORBIT_CHECK', f'AP={final_ap:.0f} PE={final_pe:.0f}')
        if vessel.orbit.body.name == 'Mun' and final_pe >= 10000 and final_ap <= 500000:
            write_event(ef, vessel, sc, launch_ut, 'ORBIT_CONFIRMED', f'AP={final_ap:.0f} PE={final_pe:.0f}')
            period = vessel.orbit.period
            t_end = sc.ut + min(period, 3600)
            while sc.ut < t_end:
                vessel = get_vessel(sc)
                safe_zero_throttle(sc)
                write_telemetry(tf, vessel, sc, launch_ut, 'MUN_ORBIT_OBSERVE')
                time.sleep(0.5)
            write_event(ef, vessel, sc, launch_ut, 'MISSION_COMPLETE', f'AP={vessel.orbit.apoapsis_altitude:.0f} PE={vessel.orbit.periapsis_altitude:.0f}')
        else:
            write_event(ef, vessel, sc, launch_ut, 'ABORT', f'bad_final_mun_orbit AP={final_ap:.0f} PE={final_pe:.0f}')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        try:
            conn = krpc.connect(name='attempt2_exception_cleanup')
            conn.space_center.active_vessel.control.throttle = 0.0
        except Exception:
            pass
        try:
            with open(EVENTS_FILE, 'a') as ef:
                safe_write(ef, f"[T+0s] EVENT=EXCEPTION DETAIL={type(exc).__name__}:{exc} TRACE={traceback.format_exc().replace(chr(10), ' | ')}\n")
        except Exception:
            pass
        raise

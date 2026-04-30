import os
import math
import time
import traceback
import krpc

WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
N = 1
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
        row = (
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
        )
        safe_write(tf, row)
    except Exception as exc:
        safe_write(tf, f"[TEL ERROR] {exc}\n")


def write_burn_row(bf, vessel, sc, launch_ut, phase, rdv):
    try:
        row = (
            f"[T+{sc.ut-launch_ut:.2f}s] PHASE={phase} "
            f"THROTTLE={vessel.control.throttle:.2f} "
            f"REMAINING_DV={rdv:.2f} "
            f"AP={vessel.orbit.apoapsis_altitude:.0f}m "
            f"PE={vessel.orbit.periapsis_altitude:.0f}m\n"
        )
        safe_write(bf, row)
    except Exception as exc:
        safe_write(bf, f"[BURN ERROR] {exc}\n")


def gravity_turn_pitch(altitude):
    if altitude < 1000:
        return 90.0
    elif altitude < 45000:
        frac = (altitude - 1000.0) / (45000.0 - 1000.0)
        return max(0.0, 90.0 - 90.0 * frac)
    else:
        return 0.0


def stage_if_no_thrust(vessel, ef, sc, launch_ut, label):
    if vessel.thrust < 1.0 and vessel.available_thrust > 0.0:
        vessel.control.activate_next_stage()
        write_event(ef, vessel, sc, launch_ut, 'STAGE', label)
        time.sleep(1.5)


def wait_pointing(ap, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            err = ap.error
        except Exception:
            err = 0.0
        if err < 3.0:
            return
        time.sleep(0.1)


def estimate_burn_time(vessel, delta_v):
    thrust = max(vessel.available_thrust, 1.0)
    isp = max(vessel.specific_impulse, 1.0) * 9.82
    m0 = vessel.mass
    mf = m0 / math.exp(max(delta_v, 0.1) / isp)
    return max((m0 - mf) / (thrust / isp), 0.5)


def execute_node(conn, vessel, sc, node, bf, ef, tf, launch_ut, phase, allow_stage=False):
    ap = vessel.auto_pilot
    ap.reference_frame = node.reference_frame
    ap.target_direction = (0, 1, 0)
    ap.engage()
    wait_pointing(ap)

    target_dv = max(node.delta_v, 0.1)
    start_speed = vessel.orbit.speed
    burn_time = estimate_burn_time(vessel, target_dv)
    burn_start = node.ut - burn_time / 2.0

    write_event(ef, vessel, sc, launch_ut, 'NODE_EXECUTE', f'{phase} target_dv={target_dv:.1f} burn_time={burn_time:.1f}')

    sc.rails_warp_factor = 0
    sc.physics_warp_factor = 0
    if sc.ut < burn_start - 15:
        sc.warp_to(burn_start - 10)
    while sc.ut < burn_start:
        write_telemetry(tf, vessel, sc, launch_ut, phase + '_COAST')
        time.sleep(0.1)

    rdv_stream = conn.add_stream(getattr, node, 'remaining_delta_v')
    vessel.control.throttle = 1.0
    write_event(ef, vessel, sc, launch_ut, 'BURN_START', phase)
    last_burn_log = -1e9
    try:
        while True:
            rdv = rdv_stream()
            delivered = abs(vessel.orbit.speed - start_speed)
            if sc.ut - last_burn_log >= 0.25:
                write_burn_row(bf, vessel, sc, launch_ut, phase, rdv)
                last_burn_log = sc.ut
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

            if allow_stage and vessel.thrust < 1.0 and vessel.available_thrust > 0.0:
                vessel.control.activate_next_stage()
                write_event(ef, vessel, sc, launch_ut, 'STAGE', f'during_{phase}')
                time.sleep(1.0)

            if vessel.orbit.eccentricity >= 1.0 and phase in ('TMI', 'CIRCULARIZE'):
                write_event(ef, vessel, sc, launch_ut, 'ABORT', f'hyperbolic_during_{phase}')
                break

            time.sleep(0.05)
    finally:
        vessel.control.throttle = 0.0
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
    vessel = sc.active_vessel
    bodies = sc.bodies
    mun = bodies['Mun']
    kerbin = bodies['Kerbin']

    with open(TEL_FILE, 'w') as tf, open(BURNS_FILE, 'w') as bf, open(EVENTS_FILE, 'w') as ef:
        launch_ut = sc.ut
        phase = 'INIT'
        prev_body = vessel.orbit.body.name
        write_event(ef, vessel, sc, launch_ut, 'SCRIPT_START', 'attempt_1')
        write_telemetry(tf, vessel, sc, launch_ut, phase)

        ap = vessel.auto_pilot
        ap.engage()
        ap.target_pitch_and_heading(90, 90)
        time.sleep(1.0)

        vessel.control.sas = False
        vessel.control.rcs = False
        vessel.control.throttle = 1.0
        vessel.control.activate_next_stage()
        write_event(ef, vessel, sc, launch_ut, 'LAUNCH', 'stage_activated')
        phase = 'ASCENT'

        max_q = 0.0
        boosters_sep = False
        core_sep = False
        upper_sep = False

        while True:
            alt = vessel.flight(vessel.surface_reference_frame).mean_altitude
            q = vessel.flight(vessel.surface_reference_frame).dynamic_pressure
            ap_alt = vessel.orbit.apoapsis_altitude
            if q > max_q:
                max_q = q
            if q > 20000:
                vessel.control.throttle = 0.65
            else:
                vessel.control.throttle = 1.0
            pitch = gravity_turn_pitch(alt)
            ap.target_pitch_and_heading(pitch, 90)
            if alt > 1500 and alt < 5000:
                write_event(ef, vessel, sc, launch_ut, 'GRAVITY_TURN_START', f'pitch={pitch:.1f}')
            write_telemetry(tf, vessel, sc, launch_ut, phase)

            if not boosters_sep and alt > 5000 and vessel.thrust < 250000:
                vessel.control.activate_next_stage()
                boosters_sep = True
                write_event(ef, vessel, sc, launch_ut, 'STAGE', 'booster_separation')
                time.sleep(1.0)

            if ap_alt > 90000:
                vessel.control.throttle = 0.0
                write_event(ef, vessel, sc, launch_ut, 'AP_TARGET_REACHED', f'AP={ap_alt:.0f}')
                break

            if vessel.thrust < 1.0 and not core_sep and fuel_pct(vessel) < 70:
                vessel.control.activate_next_stage()
                core_sep = True
                write_event(ef, vessel, sc, launch_ut, 'STAGE', 'core_to_second_stage')
                time.sleep(1.0)

            if fuel_pct(vessel) < 12 and not upper_sep:
                vessel.control.activate_next_stage()
                upper_sep = True
                write_event(ef, vessel, sc, launch_ut, 'STAGE', 'second_to_upper_stage')
                time.sleep(1.0)

            if fuel_pct(vessel) <= 0.5 and ap_alt < 70000:
                write_event(ef, vessel, sc, launch_ut, 'ABORT', 'fuel_depleted_before_orbit')
                return
            time.sleep(0.1)

        write_event(ef, vessel, sc, launch_ut, 'MAX_Q', f'{max_q:.0f}')
        phase = 'COAST_TO_AP'
        write_event(ef, vessel, sc, launch_ut, 'APOAPSIS_COAST_START', '')
        while vessel.orbit.time_to_apoapsis > 25:
            write_telemetry(tf, vessel, sc, launch_ut, phase)
            time.sleep(0.2)

        mu = kerbin.gravitational_parameter
        r = vessel.orbit.apoapsis
        a1 = vessel.orbit.semi_major_axis
        a2 = r
        v1 = math.sqrt(mu * (2.0 / r - 1.0 / a1))
        v2 = math.sqrt(mu / r)
        circ_dv = v2 - v1
        node = vessel.control.add_node(sc.ut + vessel.orbit.time_to_apoapsis, prograde=circ_dv)
        write_event(ef, vessel, sc, launch_ut, 'NODE_CREATED', f'CIRCULARIZE dv={circ_dv:.1f}')
        phase = 'CIRCULARIZE'
        execute_node(conn, vessel, sc, node, bf, ef, tf, launch_ut, phase)

        write_telemetry(tf, vessel, sc, launch_ut, 'POST_CIRC')
        if vessel.orbit.body.name != 'Kerbin' or vessel.orbit.periapsis_altitude < 75000:
            write_event(ef, vessel, sc, launch_ut, 'ABORT', f'failed_lko pe={vessel.orbit.periapsis_altitude:.0f}')
            return
        write_event(ef, vessel, sc, launch_ut, 'LKO_CONFIRMED', f'AP={vessel.orbit.apoapsis_altitude:.0f} PE={vessel.orbit.periapsis_altitude:.0f}')

        phase = 'PLAN_TMI'
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
        best_desc = 'none'
        for dt in range(-180, 181, 30):
            for ddv in range(-100, 101, 10):
                try:
                    node.ut = base_ut + dt
                    node.prograde = tmi_dv + ddv
                    nxt = node.orbit.next_orbit
                    if nxt and nxt.body.name == 'Mun':
                        score = abs(nxt.periapsis_altitude - 30000)
                        desc = f'encounter pe={nxt.periapsis_altitude:.0f}'
                    else:
                        score = 1e12
                        desc = 'no_encounter'
                except Exception:
                    score = 1e12
                    desc = 'exception'
                if score < best_score:
                    best_score = score
                    best = (base_ut + dt, tmi_dv + ddv)
                    best_desc = desc
        if best is None or best_score >= 1e11:
            node.remove()
            write_event(ef, vessel, sc, launch_ut, 'ABORT', 'tmi_sweep_no_encounter')
            return
        node.ut = best[0]
        node.prograde = best[1]
        write_event(ef, vessel, sc, launch_ut, 'NODE_REFINED', f'TMI ut={best[0]:.1f} dv={best[1]:.1f} {best_desc}')
        phase = 'TMI'
        execute_node(conn, vessel, sc, node, bf, ef, tf, launch_ut, phase)

        write_telemetry(tf, vessel, sc, launch_ut, 'POST_TMI')
        if not (vessel.orbit.next_orbit and vessel.orbit.next_orbit.body.name == 'Mun') and vessel.orbit.body.name == 'Kerbin':
            write_event(ef, vessel, sc, launch_ut, 'ABORT', 'no_mun_encounter_after_tmi')
            return
        write_event(ef, vessel, sc, launch_ut, 'MUN_ENCOUNTER_CONFIRMED', '')

        phase = 'COAST_TO_MUN'
        while vessel.orbit.body.name == 'Kerbin':
            write_telemetry(tf, vessel, sc, launch_ut, phase)
            t_soi = vessel.orbit.time_to_soi_change
            if not math.isnan(t_soi) and t_soi > 90:
                sc.warp_to(sc.ut + t_soi - 60)
            time.sleep(0.2)
            if vessel.orbit.body.name != prev_body:
                prev_body = vessel.orbit.body.name
                write_event(ef, vessel, sc, launch_ut, 'SOI_CHANGE', prev_body)
        if vessel.orbit.body.name != 'Mun':
            write_event(ef, vessel, sc, launch_ut, 'ABORT', f'unexpected_body_{vessel.orbit.body.name}')
            return

        phase = 'PLAN_MOI'
        while vessel.orbit.time_to_periapsis > 120:
            write_telemetry(tf, vessel, sc, launch_ut, phase)
            if vessel.orbit.time_to_periapsis > 300:
                sc.warp_to(sc.ut + vessel.orbit.time_to_periapsis - 90)
            time.sleep(0.2)

        mu_m = mun.gravitational_parameter
        r_peri = vessel.orbit.periapsis
        a1 = vessel.orbit.semi_major_axis
        target_r = mun.equatorial_radius + 50000
        v_peri = math.sqrt(mu_m * (2.0 / r_peri - 1.0 / a1))
        v_target = math.sqrt(mu_m * (2.0 / r_peri - 1.0 / ((r_peri + target_r) / 2.0)))
        moi_dv = max(v_peri - v_target, 0.0)
        node = vessel.control.add_node(sc.ut + vessel.orbit.time_to_periapsis, prograde=-moi_dv)
        write_event(ef, vessel, sc, launch_ut, 'NODE_CREATED', f'MOI dv={moi_dv:.1f}')
        phase = 'MOI'
        execute_node(conn, vessel, sc, node, bf, ef, tf, launch_ut, phase)

        write_telemetry(tf, vessel, sc, launch_ut, 'POST_MOI')
        if vessel.orbit.body.name != 'Mun':
            write_event(ef, vessel, sc, launch_ut, 'ABORT', 'left_mun_soi_after_moi')
            return
        if vessel.orbit.periapsis_altitude < 10000:
            # small cleanup circularization at next periapsis/apoapsis depending on orbit
            desired = 30000
            node = vessel.control.add_node(sc.ut + max(vessel.orbit.time_to_periapsis, 20), prograde=0)
            current_pe = vessel.orbit.periapsis_altitude
            current_ap = vessel.orbit.apoapsis_altitude
            if current_pe < desired:
                mu_m = mun.gravitational_parameter
                r = vessel.orbit.apoapsis
                a1 = vessel.orbit.semi_major_axis
                a2 = 0.5 * ((mun.equatorial_radius + desired) + r)
                dv = math.sqrt(mu_m * (2.0 / r - 1.0 / a2)) - math.sqrt(mu_m * (2.0 / r - 1.0 / a1))
                node.ut = sc.ut + vessel.orbit.time_to_apoapsis
                node.prograde = dv
            write_event(ef, vessel, sc, launch_ut, 'NODE_CREATED', 'MUN_CLEANUP')
            phase = 'MUN_CLEANUP'
            execute_node(conn, vessel, sc, node, bf, ef, tf, launch_ut, phase)

        final_ap = vessel.orbit.apoapsis_altitude
        final_pe = vessel.orbit.periapsis_altitude
        write_event(ef, vessel, sc, launch_ut, 'ORBIT_CHECK', f'AP={final_ap:.0f} PE={final_pe:.0f}')
        if vessel.orbit.body.name == 'Mun' and final_pe >= 10000 and final_ap <= 500000:
            write_event(ef, vessel, sc, launch_ut, 'ORBIT_CONFIRMED', f'AP={final_ap:.0f} PE={final_pe:.0f}')
            phase = 'MUN_ORBIT_OBSERVE'
            period = vessel.orbit.period
            t_end = sc.ut + min(period, 3600)
            vessel.control.throttle = 0.0
            while sc.ut < t_end:
                write_telemetry(tf, vessel, sc, launch_ut, phase)
                time.sleep(0.5)
            write_event(ef, vessel, sc, launch_ut, 'MISSION_COMPLETE', f'AP={vessel.orbit.apoapsis_altitude:.0f} PE={vessel.orbit.periapsis_altitude:.0f}')
        else:
            write_event(ef, vessel, sc, launch_ut, 'ABORT', f'bad_final_mun_orbit AP={final_ap:.0f} PE={final_pe:.0f}')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        try:
            with open(EVENTS_FILE, 'a') as ef:
                safe_write(ef, f"[T+0s] EVENT=EXCEPTION DETAIL={type(exc).__name__}:{exc} TRACE={traceback.format_exc().replace(chr(10), ' | ')}\n")
        except Exception:
            pass
        raise

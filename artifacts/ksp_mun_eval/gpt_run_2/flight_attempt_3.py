import os
import math
import time
import traceback
import krpc

WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
N = 3
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


def vessel(sc):
    return sc.active_vessel


def safe_zero(sc):
    try:
        sc.active_vessel.control.throttle = 0.0
    except Exception:
        pass


def safe_surface_flight(v):
    try:
        return v.flight(v.surface_reference_frame)
    except Exception:
        try:
            return v.flight()
        except Exception:
            return None


def fuel_pct(v):
    try:
        res = v.resources
        left = res.amount('LiquidFuel') + res.amount('Oxidizer')
        cap = res.max('LiquidFuel') + res.max('Oxidizer')
        return 100.0 * left / max(cap, 1.0)
    except Exception:
        return 0.0


def write_event(ef, v, sc, launch_ut, event_type, detail=''):
    met = sc.ut - launch_ut
    fl = safe_surface_flight(v)
    alt = fl.mean_altitude if fl else float('nan')
    body = 'UNKNOWN'
    try:
        body = v.orbit.body.name
    except Exception:
        pass
    safe_write(ef, f"[T+{met:.0f}s] EVENT={event_type} DETAIL={detail} BODY={body} ALT={alt:.0f}m\n")


def write_tel(tf, v, sc, launch_ut, phase):
    global _last_tel
    if sc.ut - _last_tel < 5.0:
        return
    _last_tel = sc.ut
    try:
        fl = safe_surface_flight(v)
        alt = fl.mean_altitude if fl else 0.0
        s_alt = fl.surface_altitude if fl else 0.0
        spd = v.orbit.speed
        ap = v.orbit.apoapsis_altitude
        pe = v.orbit.periapsis_altitude
        body = v.orbit.body.name
        safe_write(tf, f"[T+{sc.ut-launch_ut:.0f}s] ALT={alt:.0f}m SURF_ALT={s_alt:.0f}m SPD={spd:.1f}m/s AP={ap:.0f}m PE={pe:.0f}m BODY={body} FUEL={fuel_pct(v):.1f}% PHASE={phase} THROTTLE={v.control.throttle:.2f} STAGE={v.control.current_stage}\n")
    except Exception as exc:
        safe_write(tf, f"[TEL ERROR] {exc}\n")


def write_burn(bf, v, sc, launch_ut, phase, rdv):
    try:
        safe_write(bf, f"[T+{sc.ut-launch_ut:.2f}s] PHASE={phase} THROTTLE={v.control.throttle:.2f} REMAINING_DV={rdv:.2f} AP={v.orbit.apoapsis_altitude:.0f}m PE={v.orbit.periapsis_altitude:.0f}m\n")
    except Exception as exc:
        safe_write(bf, f"[BURN ERROR] {exc}\n")


def gravity_pitch(alt):
    if alt < 1000:
        return 90.0
    if alt < 10000:
        return 90.0 - 30.0 * ((alt - 1000.0) / 9000.0)
    if alt < 45000:
        return 60.0 - 55.0 * ((alt - 10000.0) / 35000.0)
    return 5.0


def estimate_bt(v, dv):
    thrust = max(v.available_thrust, 1.0)
    isp = max(v.specific_impulse, 1.0) * 9.82
    m0 = v.mass
    mf = m0 / math.exp(max(dv, 0.1) / isp)
    return max((m0 - mf) / (thrust / isp), 0.5)


def stage(sc, ef, launch_ut, detail):
    v = vessel(sc)
    v.control.activate_next_stage()
    time.sleep(1.5)
    v = vessel(sc)
    write_event(ef, v, sc, launch_ut, 'STAGE', detail)
    return v


def point_to_node(v, node):
    ap = v.auto_pilot
    ap.reference_frame = node.reference_frame
    ap.target_direction = (0, 1, 0)
    ap.engage()
    t0 = time.time()
    while time.time() - t0 < 60:
        try:
            if ap.error < 3.0:
                return
        except Exception:
            pass
        time.sleep(0.1)


def execute_node(conn, sc, ef, tf, bf, launch_ut, node, phase):
    v = vessel(sc)
    safe_zero(sc)
    point_to_node(v, node)
    target_dv = max(node.delta_v, 0.1)
    start_speed = v.orbit.speed
    bt = estimate_bt(v, target_dv)
    burn_start = node.ut - bt / 2.0
    write_event(ef, v, sc, launch_ut, 'NODE_EXECUTE', f'{phase} target_dv={target_dv:.1f} bt={bt:.1f}')

    sc.rails_warp_factor = 0
    sc.physics_warp_factor = 0
    if sc.ut < burn_start - 20:
        sc.warp_to(burn_start - 10)
    while sc.ut < burn_start:
        v = vessel(sc)
        safe_zero(sc)
        write_tel(tf, v, sc, launch_ut, phase + '_COAST')
        time.sleep(0.1)

    rdv_stream = conn.add_stream(getattr, node, 'remaining_delta_v')
    v = vessel(sc)
    v.control.throttle = 1.0
    write_event(ef, v, sc, launch_ut, 'BURN_START', phase)
    last = -1e9
    while True:
        v = vessel(sc)
        rdv = rdv_stream()
        delivered = abs(v.orbit.speed - start_speed)
        if sc.ut - last >= 0.25:
            write_burn(bf, v, sc, launch_ut, phase, rdv)
            last = sc.ut
        write_tel(tf, v, sc, launch_ut, phase)
        if rdv < 0.5:
            break
        if delivered >= target_dv * 0.98:
            write_event(ef, v, sc, launch_ut, 'BURN_FALLBACK_STOP', f'{phase} delivered={delivered:.1f} target={target_dv:.1f}')
            break
        if rdv < 5:
            v.control.throttle = 0.05
        elif rdv < 20:
            v.control.throttle = 0.15
        elif rdv < 50:
            v.control.throttle = 0.35
        else:
            v.control.throttle = 1.0
        time.sleep(0.05)
    safe_zero(sc)
    v = vessel(sc)
    write_event(ef, v, sc, launch_ut, 'BURN_END', phase)
    try:
        node.remove()
        write_event(ef, v, sc, launch_ut, 'NODE_REMOVED', phase)
    except Exception:
        pass


def main():
    conn = krpc.connect(name=f'flight_attempt_{N}')
    sc = conn.space_center
    kerbin = sc.bodies['Kerbin']
    mun = sc.bodies['Mun']
    v = vessel(sc)

    with open(TEL_FILE, 'w') as tf, open(BURNS_FILE, 'w') as bf, open(EVENTS_FILE, 'w') as ef:
        launch_ut = sc.ut
        write_event(ef, v, sc, launch_ut, 'SCRIPT_START', 'attempt_3')
        write_tel(tf, v, sc, launch_ut, 'INIT')

        v.auto_pilot.engage()
        v.auto_pilot.target_pitch_and_heading(90, 90)
        v.control.sas = False
        v.control.rcs = False
        v.control.throttle = 1.0
        v.control.activate_next_stage()
        write_event(ef, v, sc, launch_ut, 'LAUNCH', 'ignite_all')

        gt_logged = False
        booster_sep = False
        core_sep = False
        upper_sep = False
        max_q = 0.0
        t_launch = sc.ut

        while True:
            v = vessel(sc)
            fl = safe_surface_flight(v)
            alt = fl.mean_altitude if fl else 0.0
            q = fl.dynamic_pressure if fl else 0.0
            ap_alt = v.orbit.apoapsis_altitude
            if q > max_q:
                max_q = q
            if q > 25000:
                v.control.throttle = 0.45
            elif q > 15000:
                v.control.throttle = 0.70
            else:
                v.control.throttle = 1.0
            pitch = gravity_pitch(alt)
            v.auto_pilot.target_pitch_and_heading(pitch, 90)
            if (not gt_logged) and alt > 1500:
                write_event(ef, v, sc, launch_ut, 'GRAVITY_TURN_START', f'pitch={pitch:.1f}')
                gt_logged = True
            write_tel(tf, v, sc, launch_ut, 'ASCENT')

            if (not booster_sep) and sc.ut - t_launch > 35 and alt > 5000:
                v = stage(sc, ef, launch_ut, 'booster_separation')
                booster_sep = True

            if ap_alt >= 85000:
                safe_zero(sc)
                v = vessel(sc)
                write_event(ef, v, sc, launch_ut, 'AP_TARGET_REACHED', f'AP={ap_alt:.0f}')
                break

            if booster_sep and (not core_sep) and fuel_pct(v) < 18 and alt > 25000:
                v = stage(sc, ef, launch_ut, 'core_to_bobcat')
                core_sep = True

            if core_sep and (not upper_sep) and fuel_pct(v) < 8 and alt > 60000:
                v = stage(sc, ef, launch_ut, 'bobcat_to_cheetah')
                upper_sep = True

            if sc.ut - t_launch > 20 and alt < 150:
                write_event(ef, v, sc, launch_ut, 'ABORT', 'failed_pad_departure')
                return
            time.sleep(0.1)

        v = vessel(sc)
        safe_zero(sc)
        write_event(ef, v, sc, launch_ut, 'MAX_Q', f'{max_q:.0f}')
        write_event(ef, v, sc, launch_ut, 'APOAPSIS_COAST_START', '')
        while v.orbit.time_to_apoapsis > 25:
            v = vessel(sc)
            safe_zero(sc)
            write_tel(tf, v, sc, launch_ut, 'COAST_TO_AP')
            time.sleep(0.2)

        v = vessel(sc)
        mu = kerbin.gravitational_parameter
        r = v.orbit.apoapsis
        a1 = v.orbit.semi_major_axis
        circ_dv = math.sqrt(mu / r) - math.sqrt(mu * (2.0 / r - 1.0 / a1))
        node = v.control.add_node(sc.ut + v.orbit.time_to_apoapsis, prograde=circ_dv)
        write_event(ef, v, sc, launch_ut, 'NODE_CREATED', f'CIRCULARIZE dv={circ_dv:.1f}')
        execute_node(conn, sc, ef, tf, bf, launch_ut, node, 'CIRCULARIZE')

        v = vessel(sc)
        safe_zero(sc)
        write_tel(tf, v, sc, launch_ut, 'POST_CIRC')
        if v.orbit.body.name != 'Kerbin' or v.orbit.periapsis_altitude < 75000:
            write_event(ef, v, sc, launch_ut, 'ABORT', f'failed_lko AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')
            return
        write_event(ef, v, sc, launch_ut, 'LKO_CONFIRMED', f'AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')

        r_lko = v.orbit.semi_major_axis
        r_mun = mun.orbit.semi_major_axis
        a_trans = 0.5 * (r_lko + r_mun)
        v_lko = math.sqrt(mu / r_lko)
        v_trans = math.sqrt(mu * (2.0 / r_lko - 1.0 / a_trans))
        tmi_dv = v_trans - v_lko
        base_ut = sc.ut + v.orbit.time_to_apoapsis
        node = v.control.add_node(base_ut, prograde=tmi_dv)
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
            write_event(ef, v, sc, launch_ut, 'ABORT', 'tmi_sweep_no_encounter')
            return
        node.ut = best[0]
        node.prograde = best[1]
        write_event(ef, v, sc, launch_ut, 'NODE_REFINED', f'TMI ut={best[0]:.1f} dv={best[1]:.1f} score={best_score:.0f}')
        execute_node(conn, sc, ef, tf, bf, launch_ut, node, 'TMI')

        v = vessel(sc)
        safe_zero(sc)
        write_tel(tf, v, sc, launch_ut, 'POST_TMI')
        if not (v.orbit.next_orbit and v.orbit.next_orbit.body.name == 'Mun') and v.orbit.body.name == 'Kerbin':
            write_event(ef, v, sc, launch_ut, 'ABORT', 'no_mun_encounter_after_tmi')
            return
        write_event(ef, v, sc, launch_ut, 'MUN_ENCOUNTER_CONFIRMED', '')

        current_body = v.orbit.body.name
        while v.orbit.body.name == 'Kerbin':
            v = vessel(sc)
            safe_zero(sc)
            write_tel(tf, v, sc, launch_ut, 'COAST_TO_MUN')
            t_soi = v.orbit.time_to_soi_change
            if not math.isnan(t_soi) and t_soi > 120:
                sc.warp_to(sc.ut + t_soi - 60)
            time.sleep(0.2)
            if v.orbit.body.name != current_body:
                current_body = v.orbit.body.name
                write_event(ef, v, sc, launch_ut, 'SOI_CHANGE', current_body)

        v = vessel(sc)
        if v.orbit.body.name != 'Mun':
            write_event(ef, v, sc, launch_ut, 'ABORT', f'unexpected_body_{v.orbit.body.name}')
            return
        while v.orbit.time_to_periapsis > 120:
            v = vessel(sc)
            safe_zero(sc)
            write_tel(tf, v, sc, launch_ut, 'PLAN_MOI')
            if v.orbit.time_to_periapsis > 300:
                sc.warp_to(sc.ut + v.orbit.time_to_periapsis - 90)
            time.sleep(0.2)

        v = vessel(sc)
        mu_m = mun.gravitational_parameter
        r_peri = v.orbit.periapsis
        a1 = v.orbit.semi_major_axis
        target_r = mun.equatorial_radius + 50000
        v_peri = math.sqrt(mu_m * (2.0 / r_peri - 1.0 / a1))
        v_target = math.sqrt(mu_m * (2.0 / r_peri - 1.0 / ((r_peri + target_r) / 2.0)))
        moi_dv = max(v_peri - v_target, 0.0)
        node = v.control.add_node(sc.ut + v.orbit.time_to_periapsis, prograde=-moi_dv)
        write_event(ef, v, sc, launch_ut, 'NODE_CREATED', f'MOI dv={moi_dv:.1f}')
        execute_node(conn, sc, ef, tf, bf, launch_ut, node, 'MOI')

        v = vessel(sc)
        safe_zero(sc)
        final_ap = v.orbit.apoapsis_altitude
        final_pe = v.orbit.periapsis_altitude
        write_event(ef, v, sc, launch_ut, 'ORBIT_CHECK', f'AP={final_ap:.0f} PE={final_pe:.0f}')
        if v.orbit.body.name == 'Mun' and final_pe >= 10000 and final_ap <= 500000:
            write_event(ef, v, sc, launch_ut, 'ORBIT_CONFIRMED', f'AP={final_ap:.0f} PE={final_pe:.0f}')
            t_end = sc.ut + min(v.orbit.period, 3600)
            while sc.ut < t_end:
                v = vessel(sc)
                safe_zero(sc)
                write_tel(tf, v, sc, launch_ut, 'MUN_ORBIT_OBSERVE')
                time.sleep(0.5)
            write_event(ef, v, sc, launch_ut, 'MISSION_COMPLETE', f'AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')
        else:
            write_event(ef, v, sc, launch_ut, 'ABORT', f'bad_final_mun_orbit AP={final_ap:.0f} PE={final_pe:.0f}')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        try:
            conn = krpc.connect(name='attempt3_exception_cleanup')
            conn.space_center.active_vessel.control.throttle = 0.0
        except Exception:
            pass
        try:
            with open(EVENTS_FILE, 'a') as ef:
                safe_write(ef, f"[T+0s] EVENT=EXCEPTION DETAIL={type(exc).__name__}:{exc} TRACE={traceback.format_exc().replace(chr(10), ' | ')}\n")
        except Exception:
            pass
        raise

import os
import math
import time
import traceback
import krpc

WORKSPACE = r"C:\Users\kevin\OneDrive\Desktop\causal_reasoning_agent\agent_workspace"
N = 5
TEL_FILE = os.path.join(WORKSPACE, f"telemetry_attempt_{N}.txt")
BURNS_FILE = os.path.join(WORKSPACE, f"burns_attempt_{N}.txt")
EVENTS_FILE = os.path.join(WORKSPACE, f"events_attempt_{N}.txt")

_last_tel = -1e9


def sw(f, txt):
    try:
        f.write(txt)
        f.flush()
    except Exception:
        pass


def get_vessel(sc):
    return sc.active_vessel


def sflight(v):
    try:
        return v.flight(v.surface_reference_frame)
    except Exception:
        try:
            return v.flight()
        except Exception:
            return None


def fpct(v):
    try:
        r = v.resources
        left = r.amount('LiquidFuel') + r.amount('Oxidizer')
        cap = r.max('LiquidFuel') + r.max('Oxidizer')
        return 100.0 * left / max(cap, 1.0)
    except Exception:
        return 0.0


def we(ef, v, sc, t0, ev, detail=''):
    fl = sflight(v)
    alt = fl.mean_altitude if fl else float('nan')
    body = 'UNKNOWN'
    try:
        body = v.orbit.body.name
    except Exception:
        pass
    sw(ef, f"[T+{sc.ut-t0:.0f}s] EVENT={ev} DETAIL={detail} BODY={body} ALT={alt:.0f}m\n")


def wt(tf, v, sc, t0, phase):
    global _last_tel
    if sc.ut - _last_tel < 5.0:
        return
    _last_tel = sc.ut
    try:
        fl = sflight(v)
        alt = fl.mean_altitude if fl else 0.0
        s_alt = fl.surface_altitude if fl else 0.0
        sw(tf, f"[T+{sc.ut-t0:.0f}s] ALT={alt:.0f}m SURF_ALT={s_alt:.0f}m SPD={v.orbit.speed:.1f}m/s AP={v.orbit.apoapsis_altitude:.0f}m PE={v.orbit.periapsis_altitude:.0f}m BODY={v.orbit.body.name} FUEL={fpct(v):.1f}% PHASE={phase} THROTTLE={v.control.throttle:.2f} STAGE={v.control.current_stage}\n")
    except Exception as exc:
        sw(tf, f"[TEL ERROR] {exc}\n")


def wb(bf, v, sc, t0, phase, metric):
    try:
        sw(bf, f"[T+{sc.ut-t0:.2f}s] PHASE={phase} THROTTLE={v.control.throttle:.2f} REMAINING_DV={metric:.2f} AP={v.orbit.apoapsis_altitude:.0f}m PE={v.orbit.periapsis_altitude:.0f}m\n")
    except Exception:
        pass


def gp(alt):
    if alt < 1000:
        return 90.0
    if alt < 10000:
        return 90.0 - 35.0 * ((alt - 1000.0) / 9000.0)
    if alt < 45000:
        return 55.0 - 50.0 * ((alt - 10000.0) / 35000.0)
    return 5.0


def active_engine_snapshot(v):
    engines = []
    try:
        engines = [e for e in v.parts.engines if e.active]
    except Exception:
        engines = []
    has_fuel_flags = []
    for e in engines:
        try:
            has_fuel_flags.append('1' if e.has_fuel else '0')
        except Exception:
            has_fuel_flags.append('?')
    try:
        thrust = v.thrust
    except Exception:
        thrust = -1.0
    try:
        avail = v.available_thrust
    except Exception:
        avail = -1.0
    return {
        'count': len(engines),
        'flags': ''.join(has_fuel_flags),
        'thrust': thrust,
        'avail': avail,
    }


def stage_signal(v, commanded_throttle_high=False):
    snap = active_engine_snapshot(v)
    all_no_fuel = (snap['count'] > 0 and all(ch == '0' for ch in snap['flags']))
    thrust_collapse = commanded_throttle_high and snap['avail'] < 5.0 and snap['thrust'] < 5.0
    return all_no_fuel or thrust_collapse, snap, all_no_fuel, thrust_collapse


def stage(sc, ef, t0, detail):
    v = get_vessel(sc)
    v.control.activate_next_stage()
    time.sleep(1.5)
    v = get_vessel(sc)
    we(ef, v, sc, t0, 'STAGE', detail)
    return v


def point_surface(v, pitch, heading=90):
    ap = v.auto_pilot
    ap.engage()
    ap.target_pitch_and_heading(pitch, heading)


def point_orbital_prograde(v):
    ap = v.auto_pilot
    ap.reference_frame = v.orbital_reference_frame
    ap.target_direction = (0, 1, 0)
    ap.engage()
    try:
        ap.wait()
    except Exception:
        time.sleep(1.0)


def point_orbital_retrograde(v):
    ap = v.auto_pilot
    ap.reference_frame = v.orbital_reference_frame
    ap.target_direction = (0, -1, 0)
    ap.engage()
    try:
        ap.wait()
    except Exception:
        time.sleep(1.0)


def zero_throttle(v):
    try:
        v.control.throttle = 0.0
    except Exception:
        pass


def main():
    conn = krpc.connect(name=f'flight_attempt_{N}')
    sc = conn.space_center
    mun = sc.bodies['Mun']
    v = get_vessel(sc)

    with open(TEL_FILE, 'w') as tf, open(BURNS_FILE, 'w') as bf, open(EVENTS_FILE, 'w') as ef:
        t0 = sc.ut
        we(ef, v, sc, t0, 'SCRIPT_START', 'attempt_5')
        wt(tf, v, sc, t0, 'INIT')

        v.control.sas = False
        v.control.rcs = False
        point_surface(v, 90, 90)
        v.control.throttle = 1.0
        v.control.activate_next_stage()
        we(ef, v, sc, t0, 'LAUNCH', 'mainsail_ignite')
        launch_ut = sc.ut

        gt = False
        stage1_sep = False
        stage2_sep = False
        max_q = 0.0
        last_stage_diag = -1e9
        last_nonzero_alt = 0.0

        while True:
            v = get_vessel(sc)
            fl = sflight(v)
            alt = fl.mean_altitude if fl else 0.0
            q = fl.dynamic_pressure if fl else 0.0
            ap_alt = v.orbit.apoapsis_altitude
            if alt > last_nonzero_alt:
                last_nonzero_alt = alt
            if q > max_q:
                max_q = q

            if q > 25000:
                v.control.throttle = 0.45
            elif q > 15000:
                v.control.throttle = 0.70
            else:
                v.control.throttle = 1.0

            point_surface(v, gp(alt), 90)
            if (not gt) and alt > 1500:
                we(ef, v, sc, t0, 'GRAVITY_TURN_START', f'pitch={gp(alt):.1f}')
                gt = True

            need_stage, snap, all_no_fuel, thrust_collapse = stage_signal(v, commanded_throttle_high=(v.control.throttle > 0.9))
            if sc.ut - last_stage_diag >= 2.0:
                we(
                    ef, v, sc, t0, 'STAGE_CHECK',
                    f"stage={v.control.current_stage} active_engines={snap['count']} has_fuel={snap['flags']} thrust={snap['thrust']:.1f} avail={snap['avail']:.1f} fuel_pct={fpct(v):.1f} all_no_fuel={int(all_no_fuel)} thrust_collapse={int(thrust_collapse)}"
                )
                last_stage_diag = sc.ut

            wt(tf, v, sc, t0, 'ASCENT')

            if ap_alt >= 85000:
                zero_throttle(v)
                we(ef, v, sc, t0, 'AP_TARGET_REACHED', f'AP={ap_alt:.0f}')
                break

            if (not stage1_sep) and alt > 15000 and need_stage:
                we(ef, v, sc, t0, 'STAGE_TRIGGER', f'mainsail_to_bobcat all_no_fuel={int(all_no_fuel)} thrust_collapse={int(thrust_collapse)}')
                v = stage(sc, ef, t0, 'mainsail_to_bobcat')
                stage1_sep = True
                continue

            if stage1_sep and (not stage2_sep) and alt > 60000 and need_stage:
                we(ef, v, sc, t0, 'STAGE_TRIGGER', f'bobcat_to_cheetah all_no_fuel={int(all_no_fuel)} thrust_collapse={int(thrust_collapse)}')
                v = stage(sc, ef, t0, 'bobcat_to_cheetah')
                stage2_sep = True
                continue

            if sc.ut - launch_ut > 30 and alt < 100 and last_nonzero_alt < 500:
                we(ef, v, sc, t0, 'ABORT', 'failed_initial_climb')
                return
            if sc.ut - launch_ut > 120 and alt < 1000 and ap_alt < 10000:
                we(ef, v, sc, t0, 'ABORT', 'ascent_failed_no_ap_growth')
                return
            if sc.ut - launch_ut > 180 and alt < 5000 and ap_alt < 30000:
                we(ef, v, sc, t0, 'ABORT', 'impact_after_ascent_failure')
                return

            time.sleep(0.1)

        v = get_vessel(sc)
        zero_throttle(v)
        we(ef, v, sc, t0, 'MAX_Q', f'{max_q:.0f}')
        we(ef, v, sc, t0, 'APOAPSIS_COAST_START', '')

        while v.orbit.time_to_apoapsis > 12:
            v = get_vessel(sc)
            zero_throttle(v)
            wt(tf, v, sc, t0, 'COAST_TO_AP')
            time.sleep(0.2)

        v = get_vessel(sc)
        point_orbital_prograde(v)
        we(ef, v, sc, t0, 'CIRC_START', f'AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')
        v.control.throttle = 1.0
        last_burn = -1e9

        while v.orbit.periapsis_altitude < 75000:
            v = get_vessel(sc)
            tta = v.orbit.time_to_apoapsis
            if abs(tta) > 20 and v.orbit.apoapsis_altitude < 120000:
                v.control.throttle = 0.35
            elif v.orbit.periapsis_altitude > 50000:
                v.control.throttle = 0.15
            else:
                v.control.throttle = 1.0

            need_stage, snap, all_no_fuel, thrust_collapse = stage_signal(v, commanded_throttle_high=(v.control.throttle > 0.5))
            if (not stage2_sep) and need_stage:
                we(ef, v, sc, t0, 'STAGE_TRIGGER', f'bobcat_to_cheetah_during_circ all_no_fuel={int(all_no_fuel)} thrust_collapse={int(thrust_collapse)}')
                v = stage(sc, ef, t0, 'bobcat_to_cheetah')
                stage2_sep = True
                point_orbital_prograde(v)

            if sc.ut - last_burn >= 0.25:
                wb(bf, v, sc, t0, 'CIRCULARIZE', max(0.0, 75000 - v.orbit.periapsis_altitude))
                last_burn = sc.ut
            wt(tf, v, sc, t0, 'CIRCULARIZE')

            if v.orbit.body.name != 'Kerbin':
                we(ef, v, sc, t0, 'ABORT', 'unexpected_soi_during_circularize')
                zero_throttle(v)
                return
            if fpct(v) < 2.0:
                we(ef, v, sc, t0, 'ABORT', 'fuel_low_during_circularize')
                zero_throttle(v)
                return
            time.sleep(0.05)

        zero_throttle(v)
        v = get_vessel(sc)
        we(ef, v, sc, t0, 'CIRC_END', f'AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')
        wt(tf, v, sc, t0, 'POST_CIRC')
        if v.orbit.body.name != 'Kerbin' or v.orbit.periapsis_altitude < 75000:
            we(ef, v, sc, t0, 'ABORT', f'failed_lko AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')
            return
        we(ef, v, sc, t0, 'LKO_CONFIRMED', f'AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')

        while v.orbit.time_to_periapsis > 20:
            v = get_vessel(sc)
            zero_throttle(v)
            wt(tf, v, sc, t0, 'COAST_TO_TMI')
            if v.orbit.time_to_periapsis > 120:
                sc.warp_to(sc.ut + v.orbit.time_to_periapsis - 30)
            time.sleep(0.2)

        v = get_vessel(sc)
        point_orbital_prograde(v)
        we(ef, v, sc, t0, 'TMI_START', '')
        last_burn = -1e9
        target_ap = 12000000.0

        while True:
            v = get_vessel(sc)
            nxt = v.orbit.next_orbit
            if nxt and nxt.body.name == 'Mun':
                break
            if v.orbit.apoapsis_altitude > target_ap:
                break

            if v.orbit.apoapsis_altitude > 9000000:
                v.control.throttle = 0.10
            elif v.orbit.apoapsis_altitude > 7000000:
                v.control.throttle = 0.25
            else:
                v.control.throttle = 1.0

            need_stage, snap, all_no_fuel, thrust_collapse = stage_signal(v, commanded_throttle_high=(v.control.throttle > 0.5))
            if need_stage and (not stage2_sep):
                we(ef, v, sc, t0, 'STAGE_TRIGGER', f'bobcat_to_cheetah_during_tmi all_no_fuel={int(all_no_fuel)} thrust_collapse={int(thrust_collapse)}')
                v = stage(sc, ef, t0, 'bobcat_to_cheetah')
                stage2_sep = True
                point_orbital_prograde(v)

            if sc.ut - last_burn >= 0.25:
                wb(bf, v, sc, t0, 'TMI', max(0.0, target_ap - v.orbit.apoapsis_altitude))
                last_burn = sc.ut
            wt(tf, v, sc, t0, 'TMI')

            if fpct(v) < 2.0:
                we(ef, v, sc, t0, 'ABORT', 'fuel_low_during_tmi')
                zero_throttle(v)
                return
            time.sleep(0.05)

        zero_throttle(v)
        v = get_vessel(sc)
        if not (v.orbit.next_orbit and v.orbit.next_orbit.body.name == 'Mun'):
            we(ef, v, sc, t0, 'ABORT', 'no_mun_encounter_after_tmi')
            return
        we(ef, v, sc, t0, 'MUN_ENCOUNTER_CONFIRMED', '')

        last_body = v.orbit.body.name
        while v.orbit.body.name == 'Kerbin':
            v = get_vessel(sc)
            zero_throttle(v)
            wt(tf, v, sc, t0, 'COAST_TO_MUN')
            t_soi = v.orbit.time_to_soi_change
            if not math.isnan(t_soi) and t_soi > 120:
                sc.warp_to(sc.ut + t_soi - 60)
            if v.orbit.body.name != last_body:
                last_body = v.orbit.body.name
                we(ef, v, sc, t0, 'SOI_CHANGE', last_body)
            time.sleep(0.2)

        v = get_vessel(sc)
        if v.orbit.body.name != 'Mun':
            we(ef, v, sc, t0, 'ABORT', f'unexpected_body_{v.orbit.body.name}')
            return
        we(ef, v, sc, t0, 'SOI_CHANGE', 'Mun')

        while v.orbit.time_to_periapsis > 20:
            v = get_vessel(sc)
            zero_throttle(v)
            wt(tf, v, sc, t0, 'COAST_TO_MOI')
            if v.orbit.time_to_periapsis > 180:
                sc.warp_to(sc.ut + v.orbit.time_to_periapsis - 30)
            time.sleep(0.2)

        v = get_vessel(sc)
        point_orbital_retrograde(v)
        we(ef, v, sc, t0, 'MOI_START', '')
        last_burn = -1e9

        while not (v.orbit.periapsis_altitude >= 10000 and v.orbit.apoapsis_altitude <= 500000):
            v = get_vessel(sc)
            if v.orbit.apoapsis_altitude > 500000:
                v.control.throttle = 0.5
            elif v.orbit.apoapsis_altitude > 100000:
                v.control.throttle = 0.15
            else:
                v.control.throttle = 0.05

            if sc.ut - last_burn >= 0.25:
                wb(bf, v, sc, t0, 'MOI', v.orbit.apoapsis_altitude)
                last_burn = sc.ut
            wt(tf, v, sc, t0, 'MOI')

            if fpct(v) < 1.0:
                we(ef, v, sc, t0, 'ABORT', 'fuel_low_during_moi')
                zero_throttle(v)
                return
            time.sleep(0.05)

        zero_throttle(v)
        v = get_vessel(sc)
        we(ef, v, sc, t0, 'ORBIT_CONFIRMED', f'AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')

        observe_until = sc.ut + max(v.orbit.period, 1.0)
        while sc.ut < observe_until:
            v = get_vessel(sc)
            zero_throttle(v)
            wt(tf, v, sc, t0, 'MUN_ORBIT_OBSERVE')
            if v.orbit.body.name != 'Mun':
                we(ef, v, sc, t0, 'ABORT', 'left_mun_soi_during_observation')
                return
            if v.orbit.periapsis_altitude < 10000 or v.orbit.apoapsis_altitude > 500000:
                we(ef, v, sc, t0, 'ABORT', f'orbit_not_sustained AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')
                return
            time.sleep(0.5)

        v = get_vessel(sc)
        we(ef, v, sc, t0, 'MISSION_COMPLETE', f'AP={v.orbit.apoapsis_altitude:.0f} PE={v.orbit.periapsis_altitude:.0f}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        try:
            conn = krpc.connect(name='attempt5_exception_cleanup')
            conn.space_center.active_vessel.control.throttle = 0.0
        except Exception:
            pass
        try:
            with open(EVENTS_FILE, 'a') as ef:
                sw(ef, f"[T+0s] EVENT=EXCEPTION DETAIL={type(exc).__name__}:{exc} TRACE={traceback.format_exc().replace(chr(10), ' | ')}\n")
        except Exception:
            pass
        raise

import sys, math
sys.path.insert(0, sys.argv[1])
import numpy as np, eq_flip, pad_control as pc
fails = []
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)

lat = math.radians(48.1)
LST = 1.234
dh = 10000.0 - 600.0

def enu(az, el):
    return np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])

def hadec_to_altaz(ha, dec):
    # independent: vector rotation in the meridian plane
    v_eq = np.array([math.cos(dec) * math.cos(ha), -math.cos(dec) * math.sin(ha), math.sin(dec)])  # x to meridian, y west->east? (east negative ha)
    # equatorial (x: HA=0 on equator, y: east, z: pole) -> local (east, north, up)
    x, y, z = v_eq
    up = x * math.cos(lat) + z * math.sin(lat)
    north = -x * math.sin(lat) + z * math.cos(lat)
    east = y
    return math.atan2(east, north) % (2 * math.pi), math.asin(up)

# 0) independent check of altaz_to_hadec
for az_d, el_d in ((10, 20), (100, 45), (200, 70), (300, 15), (170, 5)):
    ha, dec = pc.altaz_to_hadec(math.radians(az_d), math.radians(el_d), lat)
    az2, el2 = hadec_to_altaz(ha, dec)
    err = math.degrees(abs(pc._wrap_pi(az2 - math.radians(az_d))) + abs(el2 - math.radians(el_d)))
    check(err < 1e-9, f'altaz_to_hadec az {az_d} el {el_d}: Rueckrechnung {err:.1e} Grad')

def ground(az, el):
    d = pc.map_distance(el, dh)
    return None if d is None else np.array([d * math.sin(az), d * math.cos(az)])

class Tel:
    start_time = 0.0
    def get_ra_dec(self): return 0.0, 0.0

P = eq_flip.EqPointing(Tel(), 1.1, -0.4)

def raw_to_altaz(ra_raw, dec_raw):
    ra, dec, side = P.raw_to_radec(ra_raw, dec_raw)
    return hadec_to_altaz(LST - ra, dec)

dirs = {'Norden': (0, 1), 'Osten': (1, 0), 'Sueden': (0, -1), 'Westen': (-1, 0), 'Nordost': (0.7071, 0.7071)}
for az_d, el_d in ((30, 10), (120, 25), (200, 8), (290, 40), (80, 60)):
    az, el = math.radians(az_d), math.radians(el_d)
    ha, dec = pc.altaz_to_hadec(az, el, lat)
    cands = P.candidates(LST - ha, dec, 0.0, 0.0)
    for side in 'AB':
        raw = (cands[side].ra_raw, cands[side].dec_raw)
        a0, e0 = raw_to_altaz(*raw)
        g0 = ground(a0, e0)
        worst = 0.0
        for name, (e, n) in dirs.items():
            speed = math.radians(1.0)
            daz, delv = pc.map_to_altaz_rate(e, n, speed, a0, e0, dh)
            dra, ddec = pc.altaz_rate_to_radec_rate(a0, e0, daz, delv, lat)
            rr = pc.radec_rate_to_raw_rate(P.raw_to_radec, *raw, dra, ddec)
            dt = 0.01
            a1, e1 = raw_to_altaz(raw[0] + rr[0] * dt, raw[1] + rr[1] * dt)
            sky = math.degrees(math.acos(min(1.0, float(enu(a0, e0) @ enu(a1, e1))))) / dt
            g1 = ground(a1, e1)
            mv = g1 - g0
            ang = math.degrees(math.atan2(mv[0] * n - mv[1] * e, mv[0] * e + mv[1] * n))
            worst = max(worst, abs(ang), abs(sky - 1.0) * 10)
        check(worst < 0.5, f'az {az_d} el {el_d} Seite {side}: Kreuz folgt dem Stick (max. Richtungsfehler {worst:.3f} Grad, 1 Grad/s)')

print('Fehler:', len(fails))
sys.exit(1 if fails else 0)

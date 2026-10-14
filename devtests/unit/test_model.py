import sys, math, random, time
sys.path.insert(0, sys.argv[1])
import eq_flip, pointing_model
from pointing_model import Model
fails=[]
def check(c,m):
    print(('OK   ' if c else 'FEHL ')+m)
    if not c: fails.append(m)
D = math.radians
LAT = D(51.5)
def ang(a, b):
    va = pointing_model.vec(-a[0], a[1]); vb = pointing_model.vec(-b[0], b[1])
    return math.degrees(math.acos(max(-1, min(1, sum(x*y for x, y in zip(va, vb))))))
def hor_to_radec(az, el, lst):
    # Horizont (az von Nord ueber Ost) -> Stundenwinkel/Dek -> ra
    sd = math.sin(el)*math.sin(LAT) + math.cos(el)*math.cos(LAT)*math.cos(az)
    dec = math.asin(sd)
    ha = math.atan2(-math.sin(az)*math.cos(el), math.cos(LAT)*math.sin(el) - math.sin(LAT)*math.cos(el)*math.cos(az))
    return lst - ha, dec

class Tel:
    start_time = 0.0
    def get_ra_dec(self): return (0.0, 0.0)

def run(ex, ey, cone, label, noise_deg=0.0, seed=1):
    random.seed(seed)
    lst0 = 1.234
    true = Model(); true.set_lst(lst0, 1000.0); true.set_params(ex, ey, cone, True)
    ra_cal_true, dec_cal_true = 0.7, -0.3
    # "Reale" Montierung: welche Rohstellung zeigt wirklich auf ein Ziel (Seite A/B)?
    def real_raw(ra, dec, side_b=False):
        ra_m, dec_m = true.to_mount(ra, dec, side_b)
        if not side_b: return ra_m - ra_cal_true, dec_m - dec_cal_true
        return ra_m + math.pi - ra_cal_true, math.pi - dec_m - dec_cal_true
    def real_pointing(ra_raw, dec_raw):
        return true.from_raw(ra_raw + ra_cal_true, dec_raw + dec_cal_true)
    noise = lambda: D(noise_deg) * random.gauss(0, 1)
    P = eq_flip.EqPointing(Tel(), 0.0, 0.0)
    P.model.set_lst(lst0, 1000.0)
    lst = true.lst()
    # 1) Ausrichtung auf Landmarke im Norden am Horizont (wie beim Nutzer)
    lm = hor_to_radec(D(2), D(1.5), lst)
    rr = real_raw(*lm)
    cal = eq_flip.calibrate(lm[0], lm[1], rr[0], rr[1], None)
    P.set_calibration(cal[0], cal[1]); P.start_session(lm[0], lm[1], rr[0], rr[1])
    grid = [hor_to_radec(D(az), D(el), lst) for az in range(0, 360, 30) for el in (15, 35, 60, 80)]
    def sky_error():
        errs = []
        for side in ('A', 'B'):
            for tgt in grid:
                c = P.candidates(tgt[0], tgt[1], 0.0, 0.0)[side]
                errs.append(ang(real_pointing(c.ra_raw, c.dec_raw), tgt))
        return max(errs), sum(errs)/len(errs)
    out = [sky_error()]
    # 2) Flugzeuge an verschiedenen Stellen zentrieren und uebernehmen
    plan = [(90, 30, False), (200, 45, False), (300, 25, True), (150, 60, True), (30, 50, False)]
    for az, el, side_b in plan:
        tgt = hor_to_radec(D(az), D(el), lst)
        rr = real_raw(*tgt, side_b)
        res = P.sync(tgt[0] + noise(), tgt[1] + noise(), rr[0], rr[1])
        out.append(sky_error())
    print(f'-- {label}')
    for i, (mx, mean) in enumerate(out):
        print(f'   nach {i} Punkt(en) zusaetzlich: max {mx:6.2f}  mittel {mean:6.2f} Grad   Modell aktiv={P.model.active if i else False}')
    pe_t = true.polar_error(LAT); pe_e = P.model.polar_error(LAT)
    return out, pe_t, pe_e, P

out, pt, pe, P = run(D(1.2), D(-0.8), 0.0, 'Polfehler 1,2/-0,8 Grad, kein Kegelfehler')
check(out[0][0] > 1.0, f'ohne Modell grosser Fehler am Himmel (max {out[0][0]:.2f} Grad)')
check(out[3][0] < 0.01, f'nach Landmarke + 3 Punkten: max Fehler {out[3][0]:.4f} Grad')
check(abs(math.degrees(pt[0]-pe[0])) < 0.01 and abs(math.degrees(pt[1]-pe[1])) < 0.01,
      f'Polfehler erkannt: wahr hoch {math.degrees(pt[0]):+.2f} ost {math.degrees(pt[1]):+.2f} / geschaetzt {math.degrees(pe[0]):+.2f} {math.degrees(pe[1]):+.2f}')
out, pt, pe, P = run(D(-2.0), D(1.5), D(0.6), 'Polfehler -2/1,5 Grad, Kegelfehler 0,6 Grad')
check(out[-1][0] < 0.02, f'mit Kegelfehler nach 5 Punkten (beide Seiten): max {out[-1][0]:.4f} Grad, Kegel geschaetzt {math.degrees(P.model.cone):.2f}')
out, pt, pe, P = run(D(1.0), D(0.7), 0.0, 'Polfehler 1/0,7 Grad, Punkte mit 0,15 Grad Rauschen', noise_deg=0.15, seed=3)
check(out[-1][1] < 0.3, f'mit Rauschen: mittlerer Fehler {out[-1][1]:.2f} Grad (vorher {out[0][1]:.2f})')
# Sinn der Anzeige: Achse um +1 Grad nach Osten und +0,5 nach oben gedreht
m = Model(); m.set_lst(0, 0)
best = None
for ex10 in range(-30, 31):
    for ey10 in range(-30, 31):
        m.set_params(D(ex10/10), D(ey10/10), 0, True); h, e = m.polar_error(LAT)
        err = abs(math.degrees(h) - 0.5) + abs(math.degrees(e) - 1.0)
        if best is None or err < best[0]: best = (err, ex10/10, ey10/10)
check(best[0] < 0.15, f'Polfehler-Anzeige laesst sich eindeutig zuordnen (ex {best[1]}, ey {best[2]})')
m.set_params(0, D(0.5), 0, True); h, e = m.polar_error(LAT)
check(abs(math.degrees(h) - 0.5) < 1e-6 and abs(e) < 1e-9, f'Drehung um Ostachse = Hoehenfehler ({math.degrees(h):+.3f})')
m.set_params(D(-0.5), 0, 0, True); h, e = m.polar_error(LAT)
check(math.degrees(e) > 0.49, f'Drehung um Meridianachse = Azimutfehler ({math.degrees(e):+.3f} Grad Ost)')
# Letzten Punkt loeschen
n = len(P.model.points); P.remove_last_point(); check(len(P.model.points) == n - 1, 'letzten Punkt loeschen')
print('FEHLER:', fails or 'keine')

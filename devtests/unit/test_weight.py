import sys, math, random
sys.path.insert(0, sys.argv[1])
import eq_flip, pointing_model
from pointing_model import Model
D = math.radians; LAT = D(51.5)
fails=[]
def check(c,m):
    print(('OK   ' if c else 'FEHL ')+m)
    if not c: fails.append(m)
def hor(az, el, lst):
    sd = math.sin(el)*math.sin(LAT) + math.cos(el)*math.cos(LAT)*math.cos(az)
    ha = math.atan2(-math.sin(az)*math.cos(el), math.cos(LAT)*math.sin(el) - math.sin(LAT)*math.cos(el)*math.cos(az))
    return lst - ha, math.asin(sd)
def ang(a, b):
    va = pointing_model.vec(-a[0], a[1]); vb = pointing_model.vec(-b[0], b[1])
    return math.degrees(math.acos(max(-1, min(1, sum(x*y for x, y in zip(va, vb))))))
class Tel:
    start_time = 0.0
    def get_ra_dec(self): return (0.0, 0.0)
def run(weighted):
    random.seed(7)
    true = Model(); true.set_lst(1.0, 0.0); true.set_params(D(1.0), D(-0.6), 0.0, True)
    rc, dc = 0.4, -0.2
    def raw(ra, dec):
        a, d = true.to_mount(ra, dec); return a - rc, d - dc
    def real(r, d): return true.from_raw(r + rc, d + dc)
    P = eq_flip.EqPointing(Tel(), 0.0, 0.0); P.model.set_lst(1.0, 0.0); lst = true.lst()
    # Erster Punkt grob (150 mm, 1 Grad daneben zentriert)
    t0 = hor(D(80), D(30), lst); r = raw(*t0)
    off = (t0[0] + D(1.0) / math.cos(t0[1]), t0[1])      # Flugzeug lag 1 Grad neben der Mitte
    cal = eq_flip.calibrate(off[0], off[1], r[0], r[1], None)
    P.set_calibration(cal[0], cal[1]); P.start_session(off[0], off[1], r[0], r[1], 'grob', 150 if weighted else None)
    for az, el in [(190, 45), (290, 30), (20, 25), (120, 60)]:
        t = hor(D(az), D(el), lst); r = raw(*t)
        n = lambda: D(0.05) * random.gauss(0, 1)
        P.sync(t[0] + n(), t[1] + n(), r[0], r[1], 'fein', 600 if weighted else None)
    grid = [hor(D(az), D(el), lst) for az in range(0, 360, 30) for el in (20, 45, 70)]
    errs = [ang(real(*(lambda c: (c.ra_raw, c.dec_raw))(P.candidates(g[0], g[1], 0, 0)['A'])), g) for g in grid]
    return sum(errs) / len(errs), max(errs), P.model.status(LAT)['list']
mu, mx, lst_u = run(False); mw, mxw, lst_w = run(True)
print(f'ohne Gewichtung: mittel {mu:.3f}  max {mx:.3f} Grad')
print(f'mit Gewichtung:  mittel {mw:.3f}  max {mxw:.3f} Grad')
print('Punkte (gewichtet):', [(p['name'], p['focal'], round(p['res'], 2)) for p in lst_w])
check(mw < mu * 0.6, 'Gewichtung verringert den Fehler durch den groben ersten Punkt deutlich')
check(lst_w[0]['res'] > 0.7, 'grober Punkt zeigt grosse Abweichung in der Liste')
print('FEHLER:', fails or 'keine')

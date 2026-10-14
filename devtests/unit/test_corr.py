import sys, math
sys.path.insert(0, sys.argv[1])
import numpy as np, eq_flip
fails=[]
def check(c,m):
    print(('OK   ' if c else 'FEHL ')+m)
    if not c: fails.append(m)
class Tel:
    start_time = 0.0
    def __init__(self): self.ra, self.dec = 0.3, 0.2
    def get_ra_dec(self): return self.ra, self.dec
def p_of(alpha, d):
    return np.array([math.cos(d)*math.cos(alpha), math.cos(d)*math.sin(alpha), math.sin(d)])
def frame(alpha, d):
    x = np.array([-math.sin(alpha), math.cos(alpha), 0.0])           # Dec-Achse, fest an der Kamera
    y = np.array([-math.sin(d)*math.cos(alpha), -math.sin(d)*math.sin(alpha), math.cos(d)])
    return x, y
t = Tel(); P = eq_flip.EqPointing(t, 1.1, -0.4)
# 1) Kandidaten mit Korrektur: raw_to_radec(Kandidat) == Ziel, beide Seiten
P.corr_ra, P.corr_dec = math.radians(1.3), math.radians(-0.7)
ra_t, dec_t = 2.0, 0.6
c = P.candidates(ra_t, dec_t, 0.3, 0.2)
for s in 'AB':
    r, d, side = P.raw_to_radec(c[s].ra_raw, c[s].dec_raw)
    err = math.degrees(abs(eq_flip._wrap(r-ra_t)) + abs(d-dec_t))
    check(err < 1e-9 and side == s, f'Seite {s}: Kandidat mit Korrektur zeigt aufs Ziel (Fehler {err:.2e} Grad)')
# 2) Uebernehmen aendert die Kandidaten nicht
before = {s: (c[s].ra_raw, c[s].dec_raw) for s in 'AB'}
P.absorb_correction()
c2 = P.candidates(ra_t, dec_t, 0.3, 0.2)
check(all(abs(eq_flip._wrap(before[s][0]-c2[s].ra_raw)) < 1e-12 and abs(before[s][1]-c2[s].dec_raw) < 1e-12 for s in 'AB')
      and P.corr_ra == 0 and P.corr_dec == 0, 'Uebernehmen: gleiche Stellung, Korrektur danach 0')
# 3) Bildrichtung: gleiche Bewegung im Kamerabild auf beiden Seiten und in jeder Hoehe
step = math.radians(0.05)
for d_deg in (10, 45, 80, 100, 135, 170, -30):
    d = math.radians(d_deg); alpha = 0.7
    x, y = frame(alpha, d); p0 = p_of(alpha, d)
    dra, ddec = P.image_to_axes(step, 0.0, d)
    mv = p_of(alpha + dra, d + ddec) - p0
    ok_x = abs(mv @ x - step) < step * 0.02 and abs(mv @ y) < step * 0.02
    dra, ddec = P.image_to_axes(0.0, step, d)
    mv = p_of(alpha + dra, d + ddec) - p0
    ok_y = abs(mv @ y - step) < step * 0.02 and abs(mv @ x) < step * 0.02
    check(ok_x and ok_y, f'd={d_deg:4d} Grad (Seite {"B" if abs(d_deg)>90 else "A"}): x und y bewegen das Bild richtig')
print('FEHLER:', fails or 'keine')

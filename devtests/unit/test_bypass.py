import sys, time, os, tempfile
sys.path.insert(0, sys.argv[1])
import skywatcher, axis_limits
from axis_limits import rad, deg, DEFAULTS, AxisLimitGuard
fails=[]
def check(c,m):
    print(('OK   ' if c else 'FEHL ')+m)
    if not c: fails.append(m)
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
h1, h2 = m._inquire_position(1), m._inquire_position(2)
L = [(-5,-5),(5,-5),(5,5),(-5,5)]
limits = {'cpr': {1: m.cpr[1], 2: m.cpr[2]}, 'home_deg': {1: deg(h1), 2: deg(h2)},
          'polygon_deg': [(deg(h1)+a, deg(h2)+b) for a,b in L]}
s = dict(DEFAULTS); s.update(margin_degrees=1.0)
g = AxisLimitGuard(m, limits, s)
def run(r, secs):
    t0=time.time()
    while time.time()-t0<secs:
        m._slew_axis(1, r); m._slew_axis(2, 0.0); time.sleep(0.1)
    m._slew_axis(1,0.0); time.sleep(1.5)
    return deg(m._inquire_position(1)-h1)
p = run(rad(2), 4); check(p < 4.2, f'mit Ueberwachung: Stopp vor Rand bei {p:.2f} Grad')
g.set_bypass(True)
p = run(rad(2), 3); check(p > 6, f'abgeschaltet: faehrt ueber Rand hinaus bis {p:.2f} Grad')
w = g.set_bypass(False); check(w is not None and 'ausserhalb' in w, f'Einschalten ausserhalb meldet: {w}')
p2 = run(rad(2), 2); check(abs(p2-p) < 0.1, f'wieder aktiv: weiter nach aussen gesperrt ({p:.2f} -> {p2:.2f})')
p3 = run(rad(-2), 2); check(p3 < p2-0.5, f'zurueck nach innen erlaubt ({p2:.2f} -> {p3:.2f})')
g.set_bypass(True); p4 = run(rad(2), 3)
sim2 = skywatcher.SkyWatcher(sim)  # gleiche Simulation, neuer Guard-Start ausserhalb
try:
    s2=dict(s); s2['require_home_at_start']=False; g2 = AxisLimitGuard(sim2, limits, s2); check(True, 'Start ausserhalb: nur Warnung, kein Abbruch')
except Exception as e:
    check(False, f'Start ausserhalb bricht ab: {e}')
sim.close()
print('FEHLER:', fails if fails else 'keine')

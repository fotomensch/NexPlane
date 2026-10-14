import sys, os, math, tempfile, shutil
sys.path.insert(0, sys.argv[1])
import skywatcher, axis_limits
from axis_limits import rad, deg, DEFAULTS, AxisLimitGuard, LimitError
fails=[]
def check(c,m):
    print(('OK   ' if c else 'FEHL ')+m)
    if not c: fails.append(m)
tmp = tempfile.mkdtemp(); f = os.path.join(tmp, 'lim.yaml')
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
h1, h2 = m._inquire_position(1), m._inquire_position(2)
P = lambda a, b: (h1 + rad(a), h2 + rad(b))
axis_limits.save_limits(f, m.cpr, {1: h1, 2: h2}, [P(-20,-20), P(20,-20), P(20,20), P(-20,20)], [[P(5,5), P(12,5), P(12,12), P(5,12)]])
s = dict(DEFAULTS); s.update(margin_degrees=2.0, file=f)
g = AxisLimitGuard(m, axis_limits.load_limits(f), s)
try:
    check(g.file == f, 'Datei des Profils bekannt')
    pv = g.refine_preview(P(0, 0)); check(pv['kind'] == 'inside', f'Punkt innen: {pv["msg"]}')
    pv = g.refine_preview(P(26, 0)); check(pv['kind'] == 'outline', f'Punkt ausserhalb: {pv["msg"]}')
    before = g.clearance_at(P(24, 0))
    g.refine_add(P(26, 0))
    after = g.clearance_at(P(24, 0))
    check(after > before, f'ein Punkt: Spitze, Abstand bei (24,0) vorher {deg(before):.2f}, nachher {deg(after):.2f} Grad')
    check(abs(deg(g.clearance_at(P(26, 0))) + 2.0) < 0.01, 'neuer Punkt liegt auf dem Rand (Sicherheitsabstand bleibt)')
    pv = g.refine_preview(P(8.5, 8.5)); check(pv['kind'] == 'hole', f'Punkt in Sperrzone: {pv["msg"]}')
    c0 = g.clearance_at(P(6.5, 8.5)); g.refine_add(P(8.5, 8.5)); c1 = g.clearance_at(P(6.5, 8.5))
    check(c1 > c0, f'Sperrzone verkleinert: Abstand bei (6.5,8.5) {deg(c0):.2f} -> {deg(c1):.2f} Grad')
    pv = g.refine_preview(P(-20.1, 0)); check(pv['kind'] == 'invalid', f'zu nah: {pv["msg"]}')
    check(g.refine_undo() and len(g.holes[0]) == 4, 'Rückgängig stellt Sperrzone wieder her')
    path = g.refine_save()
    check(os.path.exists(f + '.bak') and len(axis_limits.load_limits(f)['polygon_deg']) == 5, 'Speichern: 5 Randpunkte, .bak angelegt')
    check(len(axis_limits.load_limits(f + '.bak')['polygon_deg']) == 4, '.bak enthält die alte Fassung')
    for x, y in ((26, -15), (27, -5), (27, 5), (26, 15)):
        g.refine_add(P(x, y))
    check(g.clearance_at(P(23.5, 0)) >= 0 and g.clearance_at(P(23.5, -12)) >= 0, f'mehrere Punkte entlang der neuen Grenze: (23.5,0) frei mit {deg(g.clearance_at(P(23.5, 0))):.2f} Grad')
    check(not axis_limits.polygon_problems(g.poly), f'Umriss mit {len(g.poly)} Punkten ohne Selbstkreuzung')
    g.refine_discard(); check(len(g.poly) == 5 and not g.refine_undo_stack, 'Verwerfen lädt die gespeicherte Datei')
    # Selbstkreuzung: Punkt weit draussen hinter einer Ecke darf nicht zu einem kaputten Umriss fuehren
    pv = g.refine_preview(P(60, 60)); check(pv['kind'] in ('outline', 'invalid'), f'weit draussen: {pv["kind"]} {pv["msg"]}')
    if pv['kind'] == 'outline':
        check(not axis_limits.polygon_problems(pv['poly']), 'Vorschau ohne Selbstkreuzung')
except Exception as e:
    import traceback; traceback.print_exc(); fails.append(repr(e))
finally:
    sim.close(); shutil.rmtree(tmp)
print('FEHLER:', fails or 'keine')

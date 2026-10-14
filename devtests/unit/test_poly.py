import sys, time, math, os, tempfile
sys.path.insert(0, sys.argv[1])
import skywatcher, axis_limits
from axis_limits import rad, deg, LimitError, AxisLimitGuard, DEFAULTS, clearance
from teach_limits import Teacher

def settings(**kw):
    s = dict(DEFAULTS); s.update(kw); return s
tmp = tempfile.mkdtemp()
fails = []
def check(cond, msg):
    print(('OK   ' if cond else 'FEHL ') + msg)
    if not cond: fails.append(msg)

# --- 1) Einlernen per Teacher (kleines Dreieck), Validierung ---
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
t = Teacher(m, os.path.join(tmp, 't.yaml'), 0.8, 1.0)
t.faster(+3)  # 2 Grad/s
def drive(axis, d, secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        t.jog(axis, d); t.update(); time.sleep(0.05)
    t.stop(); time.sleep(1.2); t.update()
drive(1, +1, 2); t.mark()            # rechts
drive(2, +1, 2); t.mark()            # rechts oben
drive(1, -1, 4); t.mark()            # links oben
t.save(); check('Home' in t.message, 'Teacher: Dreieck ohne Home im Inneren wird abgelehnt -> ' + t.message)
drive(2, -1, 4); t.mark()            # links unten -> Viereck
t.save(); check('Gespeichert' in t.message, 'Teacher: Viereck speichern -> ' + t.message)
print('   ', t.status_lines())
t.stop(); sim.close()

# Fehlerfaelle beim Speichern
h = (0.0, 0.0)
try:
    axis_limits.save_limits(os.path.join(tmp,'x.yaml'), {1:1,2:1}, {1:0,2:0},
        [(rad(-1),rad(-1)),(rad(1),rad(1)),(rad(1),rad(-1)),(rad(-1),rad(1))])
    check(False, 'Selbstueberkreuzung wird abgelehnt')
except LimitError as e:
    check('ueberkreuzt' in str(e), 'Selbstueberkreuzung wird abgelehnt')
try:
    axis_limits.save_limits(os.path.join(tmp,'x.yaml'), {1:1,2:1}, {1:0,2:0},
        [(rad(1),rad(1)),(rad(3),rad(1)),(rad(3),rad(3))])
    check(False, 'Home ausserhalb wird abgelehnt')
except LimitError as e:
    check('Home' in str(e), 'Home ausserhalb wird abgelehnt')

# --- 2) L-foermiger (nicht konvexer) Bereich ---
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
h1, h2 = m._inquire_position(1), m._inquire_position(2)
L = [(-20,-10),(20,-10),(20,0),(5,0),(5,10),(-20,10)]   # Kerbe x>5, y>0 verboten
poly = [(h1+rad(a), h2+rad(b)) for a,b in L]
path = os.path.join(tmp, 'L.yaml')
lim = axis_limits.save_limits(path, m.cpr, {1:h1,2:h2}, poly)
sim.close()
MARGIN = 2.0
def run(direction_deg, speed_deg, secs=10, start=None):
    sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
    if start:
        # Startpunkt per Original-Slew ohne Waechter anfahren
        for ax, target in [(1, start[0]), (2, start[1])]:
            m._slew_axis(ax, rad(2) * (1 if target > 0 else -1))
            time.sleep(abs(target)/2); m._slew_axis(ax, 0); time.sleep(1.5)
    g = AxisLimitGuard(m, lim, settings(margin_degrees=MARGIN, require_home_at_start=start is None))
    vx = math.cos(math.radians(direction_deg)); vy = math.sin(math.radians(direction_deg))
    worst = math.inf; t0 = time.time()
    while time.time() - t0 < secs:
        m._slew_axis(1, rad(speed_deg*vx)); m._slew_axis(2, rad(speed_deg*vy))
        p = (sim_pos(sim,1), sim_pos(sim,2))
        worst = min(worst, clearance(p, poly, 0.0))
        time.sleep(0.05)
    m._slew_axis(1,0); m._slew_axis(2,0); time.sleep(1.5)
    p = (sim_pos(sim,1), sim_pos(sim,2)); worst = min(worst, clearance(p, poly, 0.0))
    rel = (deg(p[0]-h1), deg(p[1]-h2))
    sim.close()
    return deg(worst), rel
def sim_pos(sim, axis):
    # wahre Position direkt aus dem Simulator (unabhaengig vom Waechter)
    return skywatcher.decode_int_6(sim.speak(f':j{axis}')) / sim.cpr[axis] * 2*math.pi if hasattr(sim,'cpr') else None

# Simulator-Position direkt lesen (cpr aus Mount)
_m = skywatcher.SkyWatcher(skywatcher.SkyWatcherSerialHootl()); CPR = _m.cpr; _m._client = None
def sim_pos(sim, axis):
    v = skywatcher.decode_int_6(sim.speak(f':j{axis}'))
    return v / CPR[axis] * 2*math.pi

for ang, spd in [(45, 3), (45, 5), (0, 5), (90, 5), (135, 2), (200, 5)]:
    w, rel = run(ang, spd, secs=8)
    check(w >= 0.0, f'Richtung {ang:3d} Grad, {spd} Grad/s: Endstellung {rel[0]:+.2f}/{rel[1]:+.2f}, '
                    f'min. Abstand zum Rand {w:+.3f} Grad (Sicherheitsabstand {MARGIN})')

# In der Kerbe: Start links unter der Kerbe, nach oben fahren -> muss an y=0-Kante vor x>5 nicht relevant;
# Start bei x=+10,y=-5 (rechts unten), nach oben fahren -> Kerbe! stoppt bei y=-2
w, rel = run(90, 4, secs=6, start=(10, -5))
check(w >= 0 and rel[1] < 0, f'Unter der Kerbe nach oben: stoppt bei Achse 2 = {rel[1]:+.2f} (Rand bei 0, Abstand {MARGIN})')
# Start links (x=-10, y=-5), nach oben: darf bis y=8 fahren
w, rel = run(90, 4, secs=6, start=(-10, -5))
check(w >= 0 and rel[1] > 5, f'Links nach oben (keine Kerbe): faehrt bis Achse 2 = {rel[1]:+.2f}')

# --- 3) Aus dem Randbereich: nicht weiter nach aussen, aber nach innen ---
for label, dec_off in [('Randbereich', -5.0), ('Randbereich auf Kerbenlinie', 0.0)]:
    sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
    g = AxisLimitGuard(m, lim, settings(margin_degrees=MARGIN))
    if dec_off:
        g._orig_slew(2, rad(-2)); time.sleep(abs(dec_off)/2); g._orig_slew(2, 0); time.sleep(1.5)
    g._orig_slew(1, rad(3)); time.sleep(6.5); g._orig_slew(1, 0); time.sleep(1.5)   # ohne Waechter auf ~19,8 Grad
    p = deg(m._inquire_position(1) - h1)
    mx = p
    for _ in range(40):
        m._slew_axis(1, rad(2)); m._slew_axis(2, 0); time.sleep(0.05)
        mx = max(mx, deg(sim_pos(sim, 1) - h1))
    m._slew_axis(1, 0); time.sleep(1.5); mx = max(mx, deg(sim_pos(sim, 1) - h1))
    for _ in range(60):
        m._slew_axis(1, rad(-2)); m._slew_axis(2, 0); time.sleep(0.05)
    m._slew_axis(1, 0); time.sleep(1.5)
    p3 = deg(m._inquire_position(1) - h1)
    check(mx <= 20.0 and p3 < p - 0.3,
          f'{label} (Start {p:.2f}): nach aussen max. {mx:.2f} (Umriss bei 20), nach innen bis {p3:.2f}')
    sim.close()

# --- 4) Home- und cpr-Pruefung ---
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
m._slew_axis(1, rad(3)); time.sleep(1.5); m._slew_axis(1, 0); time.sleep(1.5)
try:
    AxisLimitGuard(m, lim, settings()); check(False, 'Home-Pruefung')
except LimitError as e:
    check('Home' in str(e), 'Home-Pruefung greift')
sim.close()
bad = dict(lim); bad['cpr'] = {1: 9011200, 2: 9011200}
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
try:
    AxisLimitGuard(m, bad, settings()); check(False, 'cpr-Pruefung')
except LimitError as e:
    check('Schritte' in str(e), 'cpr-Pruefung greift (Simulator vs. echte Montierung)')
sim.close()

# --- 5) Verkehrte Drehrichtung ---
class Inverted(skywatcher.SkyWatcherSerialHootl):
    def speak(self, command):
        if command[1] == 'G':
            v = int(command[3:5], 16) ^ 0x01
            command = command[:3] + format(v, '02X')
        return super().speak(command)
sim = Inverted(); m = skywatcher.SkyWatcher(sim)
AxisLimitGuard(m, lim, settings(margin_degrees=MARGIN))
try:
    for _ in range(100):
        m._inquire_position(1); m._slew_axis(1, rad(1)); time.sleep(0.05)
    check(False, 'Richtungspruefung')
except LimitError:
    time.sleep(1.5); check(not m._client.rate[1] if hasattr(m,'_client') else True, 'Richtungspruefung loest Not-Stopp aus')
sim.close()

# --- 6) Altes Dateiformat ---
import yaml
old = os.path.join(tmp, 'old.yaml'); yaml.safe_dump({'cpr':{1:1,2:1},'home_deg':{1:0,2:0},'axis1':{},'axis2':{}}, open(old,'w'))
try:
    axis_limits.load_limits(old); check(False, 'Altes Format')
except LimitError as e:
    check('alte' in str(e), 'Altes Dateiformat wird mit Hinweis abgelehnt')

print('\nERGEBNIS:', 'ALLE TESTS OK' if not fails else f'{len(fails)} FEHLER')

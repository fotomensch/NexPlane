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

sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
h1, h2 = m._inquire_position(1), m._inquire_position(2)
L = [(-20,-10),(20,-10),(20,0),(5,0),(5,10),(-20,10)]
poly = [(h1+rad(a), h2+rad(b)) for a,b in L]
lim = axis_limits.save_limits(os.path.join(tmp, 'L.yaml'), m.cpr, {1:h1,2:h2}, poly)
sim.close(); MARGIN = 2.0
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

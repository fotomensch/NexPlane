'''
Limits taught on the real mount (other steps per revolution) with the simulator:
--hootl skips them with a warning, a real mount gets an error naming both step counts,
limits taught on the simulator stay active. Argument: code directory.
'''
import os, sys, tempfile
sys.path.insert(0, sys.argv[1])
import skywatcher, axis_limits, messages
from axis_limits import rad
fails = []
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
d = tempfile.mkdtemp()
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
h1, h2 = m._inquire_position(1), m._inquire_position(2)
corners = [(h1 + rad(a), h2 + rad(b)) for a, b in [(-40, -40), (40, -40), (40, 40), (-40, 40)]]
axis_limits.save_limits(os.path.join(d, 'sim.yaml'), m.cpr, {1: h1, 2: h2}, corners, [])
axis_limits.save_limits(os.path.join(d, 'eq5.yaml'), {1: 9011200, 2: 9011200}, {1: h1, 2: h2}, corners, [])
cfg = lambda f: {'axis_limits': {'file': os.path.join(d, f), 'require_home_at_start': False}}
said = []
g = axis_limits.install_from_config(m, cfg('eq5.yaml'), 'skywatcher-mount-head-usb', simulated=True, notify=said.append)
check(g is None and len(said) == 1 and 'not used' in str(said[0]), f'hootl, EQ5-Datei: uebersprungen mit Warnung: {said}')
try:
    axis_limits.install_from_config(m, cfg('eq5.yaml'), 'skywatcher-mount-head-usb')
    check(False, 'echte Montierung, EQ5-Datei: Fehler erwartet')
except axis_limits.LimitError as e:
    t = str(messages.of_exception(e))
    check('9216000/9216000' in t and '9011200/9011200' in t, f'Fehler nennt beide Werte: {t[:120]}')
m2 = skywatcher.SkyWatcher(sim)   # fresh mount object (the failed guard above has hooked into m)
g = axis_limits.install_from_config(m2, cfg('sim.yaml'), 'skywatcher-mount-head-usb', simulated=True)
check(g is not None, 'hootl, Simulator-Datei: sicherer Bereich aktiv')
sim.close()
print('FEHLER:', fails or 'keine')

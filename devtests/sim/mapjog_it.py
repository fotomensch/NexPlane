import json, time, urllib.request, re, math, os, struct, sys
sys.path.insert(0, '.')
import gamepad
base = 'http://127.0.0.1:8802'
for _ in range(60):
    try:
        token = re.search(r"TOKEN = '([^']+)'", urllib.request.urlopen(base + '/').read().decode()).group(1); break
    except Exception:
        time.sleep(1)
def req(path, data=None):
    r = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(),
                               headers={'X-NexPlane-Token': token, 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
w = os.open('padfifo', os.O_WRONLY)
def ev(t, c, v): os.write(w, struct.pack(gamepad.EVENT_FMT, 0, 0, t, c, v))
fails = []
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
R = 6371000.0
def ground(az, el, dh):
    lo, hi = 1.0, 450000.0
    f = lambda d: math.atan2(dh - d * d / (2 * R), d)
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) > el: lo = mid
        else: hi = mid
    return lo * math.sin(az), lo * math.cos(az)
time.sleep(3)
s = req('/api/state'); check(s['gamepad'] and s['gamepad']['connected'], 'Gamepad verbunden')
print(req('/api/refine', {'action': 'on', 'alt_m': 10000}))
print(req('/api/limits_off', {'off': True, 'confirm': True}))
dh = 10000 - 80
# first move the telescope a bit lower with the browser jog so the crosshair is on the map
def tel0():
    t = req('/api/state')['telescope']; return t['az'], t['el']
print('Start', tel0())
t0 = time.time()
while time.time() - t0 < 9:
    req('/api/jog', {'r1': 5, 'r2': 3}); time.sleep(0.2)
req('/api/jog_stop', {}); time.sleep(2)
print('nach Jog', tel0())
def tel():
    t = req('/api/state')['telescope']; return math.radians(t['az']), math.radians(t['el'])
for name, code, val, exp in (('hoch', 1, 0, (0, 1)), ('rechts', 0, 255, (1, 0)), ('runter', 1, 255, (0, -1)), ('links', 0, 0, (-1, 0))):
    a0, e0 = tel(); g0 = ground(a0, e0, dh)
    ev(3, code, val); time.sleep(3.0)
    a0, e0 = tel(); g0 = ground(a0, e0, dh)    # steady state (after acceleration)
    time.sleep(3.0)
    a1, e1 = tel(); g1 = ground(a1, e1, dh)
    ev(3, code, 128); time.sleep(3)
    mx, my = g1[0] - g0[0], g1[1] - g0[1]
    ang = math.degrees(math.atan2(mx * exp[1] - my * exp[0], mx * exp[0] + my * exp[1]))
    dist = math.hypot(mx, my)
    print(f'  {name}: az {math.degrees(a0):.2f}->{math.degrees(a1):.2f}, el {math.degrees(e0):.2f}->{math.degrees(e1):.2f}, '
          f'Kreuz {mx/1000:+.2f} km Ost, {my/1000:+.2f} km Nord')
    check(dist > 200 and abs(ang) < 5, f'Stick {name}: Kreuz bewegt sich in Kartenrichtung (Abweichung {ang:.2f} Grad, {dist/1000:.1f} km)')
req('/api/limits_off', {'off': False})
print('FEHLER:', fails or 'keine')

import json, time, urllib.request, re, os, struct, sys
sys.path.insert(0, '.')
import gamepad
base = 'http://127.0.0.1:8802'
token = re.search(r"TOKEN = '([^']+)'", urllib.request.urlopen(base + '/').read().decode()).group(1)
def req(path, data=None):
    r = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(),
                               headers={'X-NexPlane-Token': token, 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
def en(m):
    '''Message from the state (template + parameters, see messages.py) as English text.'''
    if isinstance(m, dict):
        p = m.get('p', {})
        return re.sub(r'\{(\w+)(?::[^}]*)?\}', lambda x: en(p.get(x.group(1), x.group(0))), m['t'])
    return str(m)
w = os.open('padfifo', os.O_WRONLY)
def press(code): os.write(w, struct.pack(gamepad.EVENT_FMT, 0, 0, 1, code, 1) + struct.pack(gamepad.EVENT_FMT, 0, 0, 1, code, 0)); time.sleep(2.0)
st = lambda: req('/api/state')
msg = lambda: en(st()['messages'][-1]['text'])
time.sleep(5)
for hexid, wait in [('0x0aa0001', 0), ('0x0aa0002', 0), ('0x0aa0003', 0), ('0x0aa0004', 0)]:
    r = req('/api/track', {'hex': hexid}); t0 = time.time()
    import math
    while time.time() - t0 < 60:
        s = st(); a, b = s['telescope'], s['tracked_now']
        if a and b:
            c = math.sin(math.radians(a['el']))*math.sin(math.radians(b['el'])) + math.cos(math.radians(a['el']))*math.cos(math.radians(b['el']))*math.cos(math.radians(a['az']-b['az']))
            dist = math.degrees(math.acos(max(-1, min(1, c))))
            if dist < 0.1 and time.time() - t0 > 8: break
        time.sleep(0.5)
    print(f'   Abstand vor dem Uebernehmen {dist:.3f} Grad nach {time.time()-t0:.0f} s')
    p = next(p for p in st()['planes'] if p['hex'] == hexid)
    press(0x130)
    print(f"{hexid} az {p['az']:.0f} el {p['el']:.0f} track={r['ok']}: {msg()}")
    print('   Modell:', st()['correction']['model'])
press(0x134); print('Quadrat:', msg())
print('   Modell:', st()['correction']['model'])

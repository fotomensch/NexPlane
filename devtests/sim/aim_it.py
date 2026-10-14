import json, time, urllib.request, re, os, struct, sys, math
sys.path.insert(0, '.')
import gamepad
base = 'http://127.0.0.1:8802'
token = re.search(r"TOKEN = '([^']+)'", urllib.request.urlopen(base + '/').read().decode()).group(1)
def req(path, data=None):
    r = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(), headers={'X-NexPlane-Token': token, 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
def en(m):
    '''Message from the state (template + parameters, see messages.py) as English text.'''
    if isinstance(m, dict):
        p = m.get('p', {})
        return re.sub(r'\{(\w+)(?::[^}]*)?\}', lambda x: en(p.get(x.group(1), x.group(0))), m['t'])
    return str(m)
w = os.open('padfifo', os.O_WRONLY)
ev = lambda t, c, v: os.write(w, struct.pack(gamepad.EVENT_FMT, 0, 0, t, c, v))
def press(c): ev(1, c, 1); ev(1, c, 0); time.sleep(2)
st = lambda: req('/api/state'); msg = lambda: en(st()['messages'][-1]['text'])
fails=[]
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
mode = sys.argv[1]
time.sleep(5)
s = st()
if mode == 'erst':
    check(not s['manual']['aligned'], f"nicht ausgerichtet beim Start | {en(s['messages'][-1]['text'])[:80]}")
    t0 = s['telescope']
    press(0x137); s = st()
    check(s['tracked'] is not None, f"R1 waehlt Peilziel: {msg()}")
    time.sleep(4); t1 = st()['telescope']
    check(abs(t1['az'] - t0['az']) < 0.05 and abs(t1['el'] - t0['el']) < 0.05, 'Peilziel: Montierung faehrt nicht selbst')
    ev(3, 0, 255); time.sleep(1.5); ev(3, 0, 128); time.sleep(1.5); t2 = st()['telescope']
    check(abs(t2['az'] - t1['az']) > 0.3 or abs(t2['el'] - t1['el']) > 0.3, 'Stick faehrt von Hand, Peilziel bleibt: ' + str(st()['tracked']))
    req('/api/set_focal', {'mm': 150}); time.sleep(0.5)
    press(0x130); s = st()
    check(s['manual']['aligned'] and 'aircraft' in en(s['manual']['aligned_text']), f"✕: ausgerichtet ({en(s['manual']['aligned_text'])}) | {msg()[:90]}")
    check(os.path.exists('home_direction.yaml'), 'Home-Richtung gespeichert')
    check(s['correction']['model']['list'][0]['focal'] == 150, 'Punkt 1 mit Brennweite 150 mm')
    time.sleep(15); s = st()
    a, b = s['telescope'], s['tracked_now']
    c = math.sin(math.radians(a['el']))*math.sin(math.radians(b['el'])) + math.cos(math.radians(a['el']))*math.cos(math.radians(b['el']))*math.cos(math.radians(a['az']-b['az']))
    check(math.degrees(math.acos(min(1, c))) < 0.5, 'danach verfolgt NexPlane selbst')
    press(0x13b); check(st()['focal']['mm'] == 300, f"Options schaltet Brennweite: {st()['focal']['mm']}")
else:
    check(s['manual']['aligned'] and s['manual']['rough_aligned'], f"Neustart: {en(s['manual']['aligned_text'])} | {[en(m['text'])[:60] for m in s['messages']][-1]}")
    press(0x137); time.sleep(20); s = st()
    a, b = s['telescope'], s['tracked_now']
    c = math.sin(math.radians(a['el']))*math.sin(math.radians(b['el'])) + math.cos(math.radians(a['el']))*math.cos(math.radians(b['el']))*math.cos(math.radians(a['az']-b['az']))
    print(f"   grob ausgerichtet, verfolgt {s['tracked']}: Abstand {math.degrees(math.acos(min(1, c))):.2f} Grad (Anzeige)")
    press(0x130); s = st(); check(s['correction']['model']['points'] == 1 and 'aircraft' in en(s['manual']['aligned_text']), f'✕ nach Grob-Ausrichtung = Punkt 1 | {msg()[:80]}')
print('FEHLER:', fails or 'keine')

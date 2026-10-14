import json, time, urllib.request, re, math, os, struct, sys, glob
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
def ev(t, c, v): os.write(w, struct.pack(gamepad.EVENT_FMT, 0, 0, t, c, v))
def press(code): ev(1, code, 1); ev(1, code, 0); time.sleep(1.5)
def hat(code, v): ev(3, code, v); ev(3, code, 0); time.sleep(1.2)
def st(): return req('/api/state')
def msgs(n=2): return [en(m['text'])[:100] for m in st()['messages']][-n:]
fails=[]
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
time.sleep(1.5)
s = st(); check(s['gamepad'] and s['gamepad']['connected'], f"Gamepad verbunden: {s['gamepad']}")
check(s['axis_correction'], 'Korrektur im Bildsystem aktiv')
time.sleep(4)   # Flugzeuge empfangen
press(0x137); s = st(); check(s['tracked'] is not None, f'R1 waehlt Flugzeug: {s["tracked"]} | {msgs(1)}')
first = s['tracked']
g = req('/api/reach')['grid']
for p in st()['planes']:
    i = int(((p['az'] % 360) // g['az_step'])); j = int(p['el'] // g['el_step'])
    code = g['rows'][j][i] if 0 <= j < len(g['rows']) else '-'
    print(f"   {p['callsign']:8s} az {p['az']:6.1f} el {p['el']:5.1f}  erreichbar-code {code}")
time.sleep(12)
ev(3, 0, 255); time.sleep(2.0); ev(3, 0, 128); time.sleep(0.5)
c = st()['correction']; check(abs(c['ra']) > 0.3 and abs(c['dec']) < 0.01, f'Stick rechts 2 s -> Korrektur {c}')
ev(3, 0, 255); ev(3, 5, 255); time.sleep(1.0); ev(3, 0, 128); ev(3, 5, 0); time.sleep(0.5)
c2 = st()['correction']; check(abs(c2['ra']) - abs(c['ra']) > 1.0, f'mit R2 schneller: {c} -> {c2}')
hat(0x11, -1); c3 = st()['correction']; check(c3['dec'] != 0, f'Steuerkreuz hoch -> {c3}')
align_before = open('testflip_align.yaml').read()
press(0x130); s = st()
check(s['correction']['ra'] == 0 and open('testflip_align.yaml').read() != align_before, f'Kreuz: uebernommen und gespeichert | {msgs(1)}')
check(os.path.exists('protokolle/ausrichtpunkte.csv'), 'ausrichtpunkte.csv geschrieben')
check(st()['tracked'] == first, 'Verfolgung laeuft nach dem Uebernehmen weiter')
hat(0x10, 1); press(0x131); c = st()['correction']; check(c['ra'] == 0.0 and c['dec'] == 0.0, f'Kreis: Korrektur 0 | {msgs(1)}')
req('/api/offset', {'daz': 0.1, 'del': 0}); time.sleep(1.2); c = st()['correction']; check(abs(c['ra']) > 0, f'Browser-Taste D -> {c}')
press(0x137); s = st(); check(s['tracked'] not in (None, first), f'R1 naechstes Flugzeug: {s["tracked"]} | {msgs(1)}')
press(0x136); s = st(); check(s['tracked'] == first, f'L1 zurueck: {s["tracked"]} | {msgs(1)}')
press(0x133); time.sleep(0.5); s = st(); check(s['tracked'] is None, f'Dreieck STOPP | {msgs(1)}')
time.sleep(2); t0 = st()['telescope']
ev(3, 1, 0); time.sleep(2.0); ev(3, 1, 128); time.sleep(2.0); t1 = st()['telescope']
d = math.degrees(math.acos(min(1, math.sin(math.radians(t0['el']))*math.sin(math.radians(t1['el'])) + math.cos(math.radians(t0['el']))*math.cos(math.radians(t1['el']))*math.cos(math.radians(t0['az']-t1['az'])))))
check(1.0 < d < 4.0, f'Stick ohne Ziel faehrt die Montierung: {d:.2f} Grad in 2 s (1 Grad/s)')
time.sleep(1.5); t2 = st()['telescope']; check(abs(t2['az']-t1['az']) < 0.05 and abs(t2['el']-t1['el']) < 0.05, 'Stick losgelassen: steht')
logs = glob.glob('protokolle/verfolgung_*.csv'); n = sum(1 for _ in open(logs[0])) if logs else 0
check(n > 50, f'Verfolgungsprotokoll: {n} Zeilen')
print('FEHLER:', fails or 'keine')

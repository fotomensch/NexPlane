import asyncio, json, os, re, time, urllib.request, glob
from playwright.async_api import async_playwright
base = 'http://127.0.0.1:8802'
for _ in range(60):
    try: token = re.search(r"TOKEN = '([^']+)'", urllib.request.urlopen(base + '/').read().decode()).group(1); break
    except Exception: time.sleep(1)
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
fails = []
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
import config
hfile = os.path.join(config.main_config_dir(), 'home_direction.yaml')
mt = {f: os.path.getmtime(f) for f in ['testflip_align.yaml'] + ([hfile] if os.path.exists(hfile) else [])}
time.sleep(3)
s = req('/api/state'); print('vorher:', s['manual']['aligned'], en(s['manual']['aligned_text']))
print(req('/api/test_align', {'action': 'flip'}))
print(req('/api/test_align', {'action': 'set', 'confirm': True})); time.sleep(1.5)
s = req('/api/state'); m = s['manual']; t = s['telescope']
check(m['test_aligned'] and m['aligned'], f"Testmodus aktiv: {en(m['aligned_text'])}")
check(abs(t['el'] - 51.5) < 0.5 and (t['az'] < 1 or t['az'] > 359), f"Home zeigt zum Pol: Az {t['az']:.2f} El {t['el']:.2f}")
def jog_dec(sign, secs=4):
    t0 = time.time()
    while time.time() - t0 < secs: req('/api/jog', {'r1': 0, 'r2': 5 * sign}); time.sleep(0.2)
    req('/api/jog_stop', {}); time.sleep(2)
jog_dec(-1); a = req('/api/state')['telescope']; print('Dec -:', a['az'], a['el'])
print(req('/api/test_align', {'action': 'flip'})); time.sleep(1.5)
b = req('/api/state')['telescope']; print('nach 180°:', b['az'], b['el'], en(req('/api/state')['manual']['aligned_text']))
check(abs(a['el'] - b['el']) < 0.3 and min((a['az'] + b['az']) % 360, 360 - (a['az'] + b['az']) % 360) < 1 and abs(a['az'] - 180) > 5,
      'Dec aus Home schwenkt nach Ost/West (gespiegelt an Nord), 180° drehen tauscht die Seite')
for _ in range(20):
    if req('/api/reach').get('grid'): break
    time.sleep(1)
check(bool(req('/api/reach').get('grid')), 'rote Flächen berechnet')
async def ui():
    async with async_playwright() as p:
        br = await p.chromium.launch(); pg = await br.new_page(viewport={'width': 1400, 'height': 1100})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(base + '/'); await pg.wait_for_timeout(3000)
        await pg.evaluate("document.querySelectorAll('aside .card').forEach(c => c.classList.remove('collapsed'))")
        await pg.click('#testalign-box summary'); await pg.wait_for_timeout(500)
        de = await pg.inner_text('#align-status')
        await pg.evaluate("document.querySelector('#manual-card').scrollIntoView()")
        await pg.screenshot(path='testmodus_de.png')
        await pg.evaluate("setLang && setLang('en')") if await pg.evaluate("typeof setLang === 'function'") else None
        await pg.wait_for_timeout(1500)
        en = await pg.inner_text('#manual-card')
        print('DE Status:', de); print('EN Ausschnitt:', [l for l in en.split('\n') if 'TEST' in l or 'test' in l.lower()][:6])
        check(not errs, f'keine JS-Fehler {errs}')
        await br.close()
asyncio.run(ui())
print(req('/api/test_align', {'action': 'end'})); time.sleep(1)
check(not req('/api/state')['manual']['aligned'], 'Testmodus beendet, nicht ausgerichtet')
check(all(os.path.getmtime(f) == v for f, v in mt.items()) and (hfile in mt or not os.path.exists(hfile)),
      'keine Ausrichtungs-/Home-Richtungsdatei geschrieben')
print('FEHLER:', fails or 'keine')

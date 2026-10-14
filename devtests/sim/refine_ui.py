import asyncio, json, os, time, urllib.request, re
from playwright.async_api import async_playwright
base='http://127.0.0.1:8802'
def tok(): return re.search(r"TOKEN = '([^']+)'", urllib.request.urlopen(base + '/').read().decode()).group(1)
fails=[]
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
async def main():
    token = tok()
    def req(path, data=None):
        r = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(), headers={'X-NexPlane-Token': token, 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(r).read())
    def red(): g = req('/api/reach')['grid']; return sum(r.count('0') for r in g['rows'])
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1400, 'height': 1000})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(base + '/'); await pg.wait_for_timeout(4000)
        await pg.click('#tab-map'); await pg.wait_for_timeout(1000)
        await pg.evaluate("document.querySelectorAll('aside .card').forEach(c => c.classList.remove('collapsed'))")
        await pg.click('#refine-box summary'); await pg.wait_for_timeout(1500)
        r0 = red(); print('rote Zellen vorher:', r0)
        print(req('/api/limits_off', {'off': True, 'confirm': True}))
        t0 = time.time()
        while time.time() - t0 < 16:
            req('/api/jog', {'r1': 5, 'r2': 0}); await asyncio.sleep(0.2)
        req('/api/jog_stop', {}); await pg.wait_for_timeout(2500)
        st = req('/api/state')['refine']
        print('Status:', (await pg.inner_text('#refine-status')).replace('\n', ' | '))
        check(st['preview']['kind'] == 'outline', f"Vorschau: {st['preview']['msg']}, Abstand {st['clearance']}")
        n_cross = await pg.evaluate("document.querySelectorAll('#map .leaflet-marker-icon svg circle[r=\"9\"]').length")
        check(n_cross >= 1, f'Fadenkreuz auf der Landkarte ({n_cross})')
        await pg.screenshot(path='refine_map.png')
        await pg.click('#refine-add'); await pg.wait_for_timeout(3000)
        r1 = red(); check(r1 < r0, f'rote Zellen nach dem Punkt: {r0} -> {r1}')
        st = req('/api/state')['refine']; check(st['unsaved'] == 1, 'ein ungespeicherter Punkt')
        await pg.click('#refine-save'); await pg.wait_for_timeout(1500)
        check(os.path.exists('testflip_limits.yaml.bak'), 'gespeichert, .bak vorhanden')
        print('Meldungen:', [m['text'][:80] for m in req('/api/state')['messages']][-3:])
        print('JS-Fehler:', errs); check(not errs, 'keine JS-Fehler')
        await b.close()
asyncio.run(main())
print('FEHLER:', fails or 'keine')

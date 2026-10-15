'''
Own focal lengths (browser): add, select, duplicate, remove, config values protected,
saved in focal_lengths.yaml, German texts, gamepad Options cycles through all of them.
Needs the simulator with the gamepad FIFO (sim_setup pad) and Playwright.
'''
import asyncio, json, os, re, struct, sys, time, urllib.request
import yaml
from playwright.async_api import async_playwright
sys.path.insert(0, '.')
import gamepad
base = 'http://127.0.0.1:8802'
token = re.search(r"TOKEN = '([^']+)'", urllib.request.urlopen(base + '/').read().decode()).group(1)
def req(path, data=None):
    r = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(),
                               headers={'X-NexPlane-Token': token, 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
def st(): return req('/api/state')
def own_file():
    try: return yaml.safe_load(open('focal_lengths.yaml'))['focal_lengths_mm']
    except FileNotFoundError: return None
fails = []
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
w = os.open('padfifo', os.O_WRONLY)
def press(code):
    for v in (1, 0): os.write(w, struct.pack(gamepad.EVENT_FMT, 0, 0, 1, code, v))
    time.sleep(1.5)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1400, 'height': 1000})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(base + '/'); await pg.wait_for_timeout(3000)
        await pg.evaluate("localStorage.setItem('nexplane-lang', 'en')"); await pg.reload(); await pg.wait_for_timeout(3000)
        opts = lambda: pg.eval_on_selector_all('#focal-sel option', 'os => os.map(o => o.textContent)')
        check(await opts() == ['150 mm', '300 mm', '600 mm'], f'Liste aus config.yaml: {await opts()}')
        check(not await pg.is_visible('#focal-del'), 'Config-Brennweite: kein Entfernen-Knopf')
        await pg.fill('#focal-new', '900'); await pg.click('#focal-add'); await pg.wait_for_timeout(2000)
        check(await opts() == ['150 mm', '300 mm', '600 mm', '900 mm'], f'900 mm hinzugefuegt: {await opts()}')
        check(st()['focal']['mm'] == 900 and await pg.input_value('#focal-sel') == '900', 'neue Brennweite ausgewaehlt')
        check(await pg.input_value('#focal-new') == '', 'Eingabefeld geleert')
        check(own_file() == [900.0], f'focal_lengths.yaml: {own_file()}')
        check(await pg.is_visible('#focal-del'), 'eigene Brennweite: Entfernen-Knopf sichtbar')
        await pg.fill('#focal-new', '1250,5'); await pg.press('#focal-new', 'Enter'); await pg.wait_for_timeout(2000)
        check(own_file() == [900.0, 1250.0], f'Komma und Enter, auf ganze mm: {own_file()}')
        r = req('/api/focal_add', {'mm': 300.2}); check(not r['ok'] and 'already' in r['error']['t'], f'Doppelt abgelehnt: {r}')
        r = req('/api/focal_add', {'mm': 5}); check(not r['ok'], f'5 mm abgelehnt: {r}')
        r = req('/api/focal_add', {'mm': None}); check(not r['ok'], f'leer abgelehnt: {r}')
        r = req('/api/focal_remove', {'mm': 600}); check(not r['ok'] and 'config.yaml' in r['error']['t'], f'Config-Wert nicht entfernbar: {r}')
        # Gamepad Options: 1250 is selected -> wraps to 150, then 300
        press(0x13b); check(st()['focal']['mm'] == 150, f"Options nach letzter: {st()['focal']['mm']}")
        req('/api/set_focal', {'mm': 600}); press(0x13b)
        check(st()['focal']['mm'] == 900, f"Options erreicht eigene 900: {st()['focal']['mm']}")
        await pg.wait_for_timeout(1500)
        await pg.click('#focal-del'); await pg.wait_for_timeout(2000)
        check(own_file() == [1250.0], f'900 entfernt: {own_file()}')
        check(st()['focal']['mm'] == 150, f"Auswahl nach Entfernen: {st()['focal']['mm']}")
        # German
        await pg.evaluate("localStorage.setItem('nexplane-lang', 'de')"); await pg.reload(); await pg.wait_for_timeout(3000)
        txt = await pg.inner_text('#focal-row'); ph = await pg.get_attribute('#focal-new', 'placeholder')
        check('Hinzufügen' in txt and ph == 'andere (mm)', f'Deutsch: {txt!r} / {ph!r}')
        check(errs == [], f'JS-Fehler: {errs}')
        await b.close()
    print('FEHLER:', fails or 'keine')

asyncio.run(main())

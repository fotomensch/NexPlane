import asyncio, json, os, time, yaml
from playwright.async_api import async_playwright
fails=[]
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1400, 'height': 1400})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.add_init_script("localStorage.setItem('nexplane-lang', 'de');")   # the checks below read German texts
        await pg.goto('http://127.0.0.1:8802/'); await pg.wait_for_timeout(8000)
        gps = await pg.inner_text('#loc-gps'); print('   GPS-Zeile:', gps)
        check('51,51' in gps and 'vom Standort' in gps, 'GPS-Position wird angezeigt')
        check(await pg.is_visible('#h-locwarn'), 'Warnung im Kopf: ' + await pg.inner_text('#h-locwarn'))
        # Karte "Standort" aufklappen falls zugeklappt
        card = pg.locator('#loc-card')
        if 'collapsed' in (await card.get_attribute('class') or ''):
            await card.locator('h2').click()
        await pg.click('#place-edit summary'); await pg.wait_for_timeout(1500)
        box = await pg.locator('#place-map').bounding_box()
        await pg.mouse.click(box['x'] + box['width'] * 0.7, box['y'] + box['height'] * 0.3); await pg.wait_for_timeout(300)
        lat = await pg.input_value('#place-lat'); lon = await pg.input_value('#place-lon')
        check(lat != '' and lon != '', f'Klick in die Karte setzt Koordinaten ({lat}, {lon})')
        await pg.fill('#place-name', 'Kirchturm Test'); await pg.select_option('#place-type', 'landmark'); await pg.fill('#place-alt', '182')
        await pg.click('#place-save'); await pg.wait_for_timeout(2500)
        o = yaml.safe_load(open('places.yaml'))['locations']
        check('Kirchturm Test' in o and o['Kirchturm Test']['type'] == 'landmark', 'Landmarke in places.yaml gespeichert')
        opts = await pg.locator('#align-sel option').all_inner_texts()
        check(any('Kirchturm Test' in t for t in opts), 'Landmarke sofort als Ausrichtungsziel wählbar')
        locopts = await pg.locator('#loc-sel option').all_inner_texts()
        check(not any('Kirchturm' in t for t in locopts), 'Landmarke nicht in der Standortliste')
        await pg.click('#place-gps'); await pg.wait_for_timeout(300)
        check((await pg.input_value('#place-lat')).startswith('51.51'), 'GPS-Position übernommen in die Felder')
        await pg.fill('#place-name', 'Feld Nord'); await pg.select_option('#place-type', 'location')
        await pg.click('#place-save'); await pg.wait_for_timeout(2500)
        locopts = await pg.locator('#loc-sel option').all_inner_texts()
        check(any('Feld Nord' in t for t in locopts), 'neuer Standort in der Standortliste')
        await pg.locator('[data-placedel="Kirchturm Test"]').click(); await pg.wait_for_timeout(2500)
        o = yaml.safe_load(open('places.yaml'))['locations']
        check('Kirchturm Test' not in o, 'Löschen entfernt den Eintrag')
        await pg.fill('#place-name', 'testort'); await pg.click('#place-save'); await pg.wait_for_timeout(2000)
        msgs = await pg.evaluate('S.messages.map(m => msgText(m.text))')
        check(any('config.yaml' in m for m in msgs[-2:]), 'Name aus config.yaml wird nicht überschrieben: ' + msgs[-1][:80])
        await pg.locator('#loc-card').screenshot(path='places_card.png')
        await pg.fill('#place-name', 'Feld Nord'); await pg.click('#place-save-act'); await pg.wait_for_timeout(9000)
        print('JS-Fehler:', errs)
        check(not errs, 'keine JS-Fehler')
        await b.close()
asyncio.run(main())
print('FEHLER:', fails or 'keine')

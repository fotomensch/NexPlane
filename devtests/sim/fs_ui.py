import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1300, 'height': 800})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8802/'); await pg.wait_for_timeout(4000)
        await pg.evaluate("document.querySelectorAll('aside .card').forEach(c => c.classList.remove('collapsed'))")
        await pg.click('#place-edit summary'); await pg.wait_for_timeout(1500)
        await pg.click('#place-fs'); await pg.wait_for_timeout(500)
        bb = await pg.locator('#place-map').bounding_box(); print('Vollbild Karte:', bb)
        await pg.hover('.leaflet-control-layers'); await pg.wait_for_timeout(300)
        labels = await pg.locator('.leaflet-control-layers-base label').all_inner_texts(); print('Ebenen:', labels)
        await pg.locator('.leaflet-control-layers-base label', has_text='Satellit').click(); await pg.wait_for_timeout(500)
        srcs = await pg.evaluate("[...document.querySelectorAll('#place-map img.leaflet-tile')].slice(0,1).map(i => i.src)"); print('Kachel:', srcs)
        await pg.mouse.click(400, 300); await pg.wait_for_timeout(300)
        print('Leiste:', await pg.inner_text('#place-barpos'))
        await pg.screenshot(path='fs.png')
        await pg.click('#place-fs-done'); await pg.wait_for_timeout(400)
        print('zurueck, Hoehe:', (await pg.locator('#place-map').bounding_box())['height'], 'Breite-Feld:', await pg.input_value('#place-lat'))
        print('JS-Fehler:', errs); await b.close()
asyncio.run(main())

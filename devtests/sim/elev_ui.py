import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1300, 'height': 900})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8802/'); await pg.wait_for_timeout(4000)
        await pg.evaluate("document.querySelectorAll('aside .card').forEach(c => c.classList.remove('collapsed'))")
        await pg.click('#place-edit summary'); await pg.wait_for_timeout(1500)
        await pg.evaluate("""() => { const f = window.fetch; window.fetch = (u, o) => String(u).startsWith('/api/elevation') ?
            Promise.resolve(new Response(JSON.stringify({ok: true, alt: 121.4, source: 'EU-DEM 25 m (OpenTopoData)'}))) : f(u, o); }""")
        await pg.select_option('#place-type', 'landmark')
        bb = await pg.locator('#place-map').bounding_box()
        print('bb', bb); await pg.mouse.click(bb['x'] + 100, bb['y'] + 100); await pg.wait_for_timeout(1000); print('lat:', await pg.input_value('#place-lat'), '| nach Klick:', await pg.inner_text('#place-elev')); await pg.wait_for_timeout(500)
        print('Anzeige:', await pg.inner_text('#place-elev')); print('Hoehenfeld:', await pg.input_value('#place-alt'))
        await pg.fill('#place-alt', '170'); await pg.mouse.click(bb['x'] + 150, bb['y'] + 120); await pg.wait_for_timeout(500); print('nach eigener Eingabe bleibt:', await pg.input_value('#place-alt')); print('JS-Fehler:', errs); await b.close()
asyncio.run(main())

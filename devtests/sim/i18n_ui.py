import asyncio, os, struct, sys, re, time
sys.path.insert(0, '.')
import gamepad
from playwright.async_api import async_playwright
GER = re.compile(r'[äöüÄÖÜß]|\b(der|die|das|und|nicht|mit|ist|auf|wird|Seite|Flugzeug|Teleskop|Montierung|bitte|Bitte|kein|keine|Kein|Punkt|Ausricht\w*|Korrektur|Standort|Landmarke|zu|vom|nach|oder|Grad|hoch|tief|aktiv|verfolge|übernommen|gelöscht|eingelernte|Stellung|Richtung|übrig|Brennweite|Peilziel|Rest|Polachse|vorher|Punkte|Gespeichert|Montierung)\b')
async def main():
    w = os.open('padfifo', os.O_WRONLY)
    def press(c): os.write(w, struct.pack(gamepad.EVENT_FMT, 0, 0, 1, c, 1) + struct.pack(gamepad.EVENT_FMT, 0, 0, 1, c, 0))
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1500, 'height': 2600})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        dialogs = []
        async def on_dialog(d): dialogs.append(d.message); await d.accept()
        pg.on('dialog', lambda d: asyncio.ensure_future(on_dialog(d)))
        await pg.add_init_script("localStorage.setItem('nexplane-lang','en')")
        await pg.goto('http://127.0.0.1:8802/'); await pg.wait_for_timeout(5000)
        # alle Karten aufklappen
        await pg.evaluate("document.querySelectorAll('aside .card').forEach(c => c.classList.remove('collapsed'))")
        await pg.click('#ort-edit summary')
        found = set()
        async def collect(tag):
            txt = await pg.evaluate("""() => { const out = [];
              const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
              for (let n = w.nextNode(); n; n = w.nextNode()) { const p = n.parentElement; if (!p || ['SCRIPT','STYLE'].includes(p.nodeName)) continue;
                if (p.offsetParent === null && p.nodeName !== 'OPTION') continue; const t = n.data.trim(); if (t) out.push(t); }
              document.querySelectorAll('[title],[placeholder]').forEach(e => { ['title','placeholder'].forEach(a => { if (e.getAttribute(a)) out.push(e.getAttribute(a)); }); });
              return out; }""")
            msgs = await pg.evaluate("S.messages.map(m => tr(m.text))")
            for m in msgs[-3:]:
                if m not in found:
                    found.add(m); print(f'  msg[{tag}] {m[:200]}')
            for t in txt:
                if GER.search(t) and t not in found:
                    found.add(t); print(f'[{tag}] {t[:160]}')
        await collect('start')
        press(0x137); await pg.wait_for_timeout(2500); await collect('peilziel')
        press(0x130); await pg.wait_for_timeout(3000); await collect('ausgerichtet')
        await pg.wait_for_timeout(6000); await collect('verfolgung')
        press(0x137); await pg.wait_for_timeout(2500); await collect('naechstes')
        press(0x130); await pg.wait_for_timeout(2500); await collect('punkt2')
        press(0x13b); await pg.wait_for_timeout(1500); press(0x134); await pg.wait_for_timeout(2500); await collect('loeschen')
        await pg.click('#ort-gps'); await pg.fill('#ort-name', 'Test X'); await pg.select_option('#ort-typ', 'landmarke'); await pg.fill('#ort-alt', '100')
        await pg.click('#ort-save'); await pg.wait_for_timeout(2500); await collect('ort')
        await pg.click('#btn-forget'); await pg.wait_for_timeout(2500); await collect('vergessen')
        await pg.click('#btn-limoff'); await pg.wait_for_timeout(2000); await collect('limoff')
        await pg.click('#btn-limoff'); await pg.wait_for_timeout(2000); await collect('limon')
        for d in dialogs:
            if GER.search(d): print('[dialog] ' + d[:160])
        await pg.screenshot(path='en_full.png')
        await pg.select_option('#opt-lang', 'de'); await pg.wait_for_timeout(1000)
        de = await pg.inner_text('#manual-card h2'); print('zurueck auf DE:', de)
        print('JS-Fehler:', errs); await b.close()
asyncio.run(main())

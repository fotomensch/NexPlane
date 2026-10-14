'''
Language check of the browser GUI against a running simulator (port 8802 or argv[1]).

Triggers messages from NexPlane and from the page itself (tracking, correction, refused commands,
places editor, refining the limits), switches the language back and forth, and then looks for
words of the other language in everything the page shows: text, titles, placeholders and the
canvas labels. Prints the lines that look wrong. Needs Playwright with Chromium.
'''
import re, sys
from playwright.sync_api import sync_playwright

port = sys.argv[1] if len(sys.argv) > 1 else '8802'
URL = f'http://127.0.0.1:{port}/'

GERMAN = re.compile(r'[äöüÄÖÜß]|\b(der|die|das|und|nicht|ist|kein|keine|mit|auf|wird|Seite|Grad|Flugzeug\w*|'
                    r'Ausricht\w*|Standort\w*|Landmarke\w*|Korrektur|Teleskop|Sicherer|Bereich|Fehler|Meldung\w*)\b')
ENGLISH = re.compile(r'\b(the|and|is|not|with|of|Side|degrees|aircraft|Aircraft|Alignment|aligned|Location|Landmark|'
                     r'Correction|Telescope|Safe area|Error|Messages|Point|accepted|saved|found)\b')
# Words that are the same in both languages or names
ALLOW = re.compile(r'NexPlane|OpenStreetMap|Leaflet|Esri|Maxar|Earthstar|AirNav Radar|Flightradar24|FlightAware|'
                   r'config\.yaml|testflip_\w+\.yaml|griffith|mt_wilson|hollywood_sign|Gamepad|GPS|Share|Options|'
                   r'R1/L1|R2|STOP|STOPP|Esc|EU-DEM|Open-Meteo|OpenTopoData|ModemManager|mmcli|Az |El |Dec|RA')

texts_js = '''() => {
  const out = [document.body.innerText];
  for (const el of document.querySelectorAll('[title],[placeholder]')) {
    if (el.offsetParent !== null || el.closest('details')) out.push(el.getAttribute('title') || el.getAttribute('placeholder'));
  }
  return out.join('\\n');
}'''

def click(pg, sel):
    '''Click via JavaScript, so hidden or collapsed elements work too.'''
    pg.evaluate('s => document.querySelector(s).click()', sel)
    pg.wait_for_timeout(300)

def actions(pg):
    dialogs = []
    pg.on('dialog', lambda d: (dialogs.append(d.message), d.accept()))
    click(pg, '#plist tr[data-hex]')                       # track an aircraft
    pg.wait_for_timeout(1500)
    pg.keyboard.press('d')                                  # correction step
    click(pg, '#btn-corr-save')                              # sync point (confirm dialog)
    pg.wait_for_timeout(1500)
    click(pg, '#btn-model-pop')                              # delete last point (refused: one point stays)
    pg.evaluate("document.querySelectorAll('.card.collapsed').forEach(c => c.classList.remove('collapsed'))")
    pg.select_option('#align-sel', '__sky__')
    click(pg, '#btn-align')                                  # no object name -> local message
    pg.fill('#align-sky', 'polaris')
    click(pg, '#btn-align')                                  # too close to the pole -> refused by NexPlane
    pg.wait_for_timeout(1500)
    click(pg, '#ort-edit summary')
    click(pg, '#ort-save')                                   # no name -> local message
    pg.fill('#ort-name', 'x' * 3)
    pg.fill('#ort-lat', '95'); pg.fill('#ort-lon', '10'); pg.fill('#ort-alt', '100')
    click(pg, '#ort-save')                                   # latitude out of range -> refused by NexPlane
    click(pg, '#ort-gps')                                    # no GPS -> local message
    click(pg, '#refine-box summary')                         # refine limits panel
    pg.wait_for_timeout(1500)
    click(pg, '#refine-add')                                 # inside the outline -> refused
    click(pg, '#btn-flip')                                   # side change test
    pg.wait_for_timeout(3000)
    click(pg, '#btn-stop2')
    pg.wait_for_timeout(1500)
    return dialogs

def check(lang, text, dialogs):
    bad = GERMAN if lang == 'en' else ENGLISH
    problems = []
    for line in text.splitlines() + dialogs:
        clean = ALLOW.sub('', line)
        if bad.search(clean):
            problems.append(line.strip()[:160])
    return sorted(set(problems))

fails = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for lang, other in (('de', 'en'), ('en', 'de')):
        pg = b.new_page(viewport={'width': 1500, 'height': 1000})
        pg.add_init_script(f"localStorage.setItem('nexplane-lang', '{other}');")
        pg.goto(URL)
        pg.wait_for_timeout(3000)
        pg.select_option('#opt-lang', lang)                 # switch after the page has rendered
        pg.wait_for_timeout(500)
        dialogs = actions(pg)
        probs = check(lang, pg.evaluate(texts_js), dialogs)
        pg.screenshot(path=f'/tmp/lang_{lang}.png', full_page=True)
        print(f'--- {lang}: {len(probs)} suspicious line(s), {len(dialogs)} dialog(s)')
        if '-v' in sys.argv:
            print('    messages:', pg.inner_text('#msgs').replace('\n', '\n              '))
            print('    dialogs: ', '\n              '.join(d.replace('\n', ' ') for d in dialogs))
            print('    refine:  ', pg.inner_text('#refine-status').replace('\n', ' | '))
        for line in probs:
            print('   ', line)
        fails += len(probs)
        pg.close()
    b.close()
print('Failures: ' + (str(fails) if fails else 'none'))

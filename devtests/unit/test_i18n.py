'''
Checks that every text the browser GUI can show has a German translation.

Collects the English templates of
  - Msg('...') calls in the Python code (the template must be a string literal),
  - T('...') calls and {t: '...'} message objects in the script of webgui.html,
  - static texts and title/placeholder attributes in the HTML of webgui.html,
and checks them against webgui_static/i18n_de.js: every template needs an entry, and the
German text must use the same {placeholders}. Also reports catalog entries that are no longer
used and German text left in Python string literals.

    python3 test_i18n.py CODE_DIR            run the checks
    python3 test_i18n.py CODE_DIR --list     print all templates as JSON (for writing the catalog)
'''
import ast, glob, json, os, re, sys
from html.parser import HTMLParser

code = sys.argv[1]
fails = []
def check(cond, msg):
    if not cond:
        print('FAIL ' + msg)
        fails.append(msg)

# Texts in the HTML that are the same in both languages
SAME = {'NexPlane', 'DE', 'EN', 'kp', 'ki', 'kd', '°/s', 'GPS', 'Dec +', 'RA −', 'RA +', 'Dec −', 'config',
        'Sprache / Language', 'Name', 'Elev.'}

templates = {}   # template -> first place where it is used

# --- Python: Msg('...') ---------------------------------------------------------
for path in sorted(glob.glob(os.path.join(code, '*.py'))):
    tree = ast.parse(open(path, encoding='utf-8').read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'Msg':
            arg = node.args[0] if node.args else None
            where = f'{os.path.basename(path)}:{node.lineno}'
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value not in ('{a} {b}', '{a}'):
                    templates.setdefault(arg.value, where)
            elif where not in ('messages.py:47',):
                check(False, f'{where}: Msg template is not a string literal')
    # German text left in Python string literals (comments are not string literals)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r'[äöüÄÖÜß]', node.value):
            check(False, f'{os.path.basename(path)}:{node.lineno}: German text in a string: {node.value[:60]!r}')

# --- webgui.html: script -------------------------------------------------------
html = open(os.path.join(code, 'webgui.html'), encoding='utf-8').read()
script = html[html.index('<script src="/static/i18n_de.js">'):]

STR = r"'(?:[^'\\]|\\.)*'"
def js_unquote(lit):
    return json.loads('"' + lit[1:-1].replace('"', '\\"').replace("\\'", "'") + '"')

for m in re.finditer(r'\bT\(\s*((?:' + STR + r'\s*\+?\s*)+)', script):
    parts = re.findall(STR, m.group(1))
    templates.setdefault(''.join(js_unquote(p) for p in parts), 'webgui.html (T)')
for m in re.finditer(r'\{t:\s*(' + STR + r')(?:\s*:\s*(' + STR + r'))?', script):
    for lit in (m.group(1), m.group(2)):
        if lit:
            templates.setdefault(js_unquote(lit), 'webgui.html ({t: ...})')
for m in re.finditer(r"\{t:\s*\w+\.\w+\s*>\s*0\s*\?\s*(" + STR + r")\s*:\s*(" + STR + r")", script):
    for lit in m.groups():
        templates.setdefault(js_unquote(lit), 'webgui.html ({t: ...})')

# --- webgui.html: static HTML --------------------------------------------------
class Static(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        for k, v in attrs:
            if k in ('title', 'placeholder') and v and v.strip() not in SAME and re.search('[A-Za-z]', v):
                templates.setdefault(v.strip(), 'webgui.html (attribute)')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1
    def handle_data(self, data):
        t = data.strip()
        if not self.skip and t and t not in SAME and re.search('[A-Za-z]', t):
            templates.setdefault(t, 'webgui.html (text)')
body = html[html.index('<body'):html.index('<script src="/static/i18n_de.js">')]
Static().feed(body)

if '--list' in sys.argv:
    print(json.dumps(templates, ensure_ascii=False, indent=1))
    sys.exit(0)

# --- Catalog -------------------------------------------------------------------
cat_src = open(os.path.join(code, 'webgui_static', 'i18n_de.js'), encoding='utf-8').read()
start = cat_src.index('{', cat_src.index('window.NEXPLANE_DE'))
catalog = json.loads(cat_src[start:cat_src.rindex('}') + 1])
names = lambda s: sorted(set(re.findall(r'\{(\w+)(?::[^}]*)?\}', s)))
for t, where in templates.items():
    if t not in catalog:
        check(False, f'no German entry for {t!r} ({where})')
    elif names(t) != names(catalog[t]):
        check(False, f'placeholders differ: {t!r} -> {catalog[t]!r}')
for t in catalog:
    check(t in templates, f'catalog entry is not used: {t!r}')

print(f'{len(templates)} templates, {len(catalog)} catalog entries')
print('Failures: ' + (str(len(fails)) if fails else 'none'))
sys.exit(1 if fails else 0)

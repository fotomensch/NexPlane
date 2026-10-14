import pexpect, time, os, sys, pyte, yaml
np_dir, out = sys.argv[1], sys.argv[2]
if os.path.exists(out): os.remove(out)
screen = pyte.Screen(120, 45); stream = pyte.ByteStream(screen)
c = pexpect.spawn(f'python3 teach_limits.py --hootl --telescope-protocol skywatcher-mount-head-usb --output {out}',
                  cwd=np_dir, dimensions=(45, 120), timeout=30)
def pump(t=0.3):
    end = time.time() + t
    while time.time() < end:
        try: stream.feed(c.read_nonblocking(65536, timeout=0.05))
        except pexpect.TIMEOUT: pass
def text(): return '\n'.join(l.rstrip() for l in screen.display if l.strip())
R, L, U, D = '\x1bOC', '\x1bOD', '\x1bOA', '\x1bOB'   # keypad (application) mode, as in terminfo
def hold(k, s):
    t = time.time()
    while time.time() - t < s: c.send(k); pump(0.05)
    pump(1.5)
pump(3)
for _ in range(4): c.send('+'); pump(0.1)      # 5 Grad/s
# Umriss: Quadrat ca. +-10 Grad
hold(R, 2); hold(D, 2); c.send('m'); pump()
hold(U, 4); c.send('m'); pump()
hold(L, 4); c.send('m'); pump()
hold(D, 4); c.send('m'); pump()
# Sperrzone links unten (innerhalb, ohne Home)
c.send('n'); pump()
hold(R, 0.6); c.send('m'); pump()
hold(R, 0.6); c.send('m'); pump()
hold(U, 0.6); c.send('m'); pump()
c.send('e'); pump()
c.send('s'); pump(1)
print(text()); print('-----')
c.send('q'); c.expect(pexpect.EOF)
d = yaml.safe_load(open(out))
print('gespeichert: Umriss', len(d['polygon_deg']), 'Punkte, Sperrzonen', [len(z) for z in d['exclusions_deg']])

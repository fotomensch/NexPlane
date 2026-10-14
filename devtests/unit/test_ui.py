import pexpect, time, os, sys, pyte
np_dir, out = sys.argv[1], sys.argv[2]
if os.path.exists(out): os.remove(out)
screen = pyte.Screen(110, 40); stream = pyte.ByteStream(screen)
c = pexpect.spawn(f'python3 teach_limits.py --hootl --telescope-protocol skywatcher-mount-head-usb --output {out}',
                  cwd=np_dir, dimensions=(40, 110), timeout=30)
def pump(t=0.3):
    end = time.time() + t
    while time.time() < end:
        try: stream.feed(c.read_nonblocking(65536, timeout=0.05))
        except pexpect.TIMEOUT: pass
def text(): return '\n'.join(l.rstrip() for l in screen.display if l.strip())
R, L, U, D = '\x1b[C', '\x1b[D', '\x1b[A', '\x1b[B'
def hold(k, s):
    t = time.time()
    while time.time() - t < s: c.send(k); pump(0.05)
    pump(1.5)
pump(3)
for _ in range(4): c.send('+'); pump(0.1)
hold(R, 1.5); hold(D, 1.0); c.send('m'); pump()
hold(U, 2.0); c.send('m'); pump()
hold(L, 3.0); c.send('m'); pump()
hold(D, 2.0); c.send('m'); pump()
c.send('g'); pump(1.0); print(text()); print('-----')
c.send('q'); pump(); print([l for l in text().splitlines() if 'gespeichert' in l.lower()])
c.send('s'); pump(); print([l for l in text().splitlines() if 'Gespeichert' in l])
c.send('q'); c.expect(pexpect.EOF)
print(open(out).read())

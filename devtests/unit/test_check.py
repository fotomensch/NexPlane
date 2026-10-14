import sys, os, time, math, pexpect, pyte
np_dir = sys.argv[1]; sys.path.insert(0, np_dir)
import skywatcher, axis_limits
from axis_limits import rad
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
h1, h2 = m._inquire_position(1), m._inquire_position(2)
lim_path = os.path.join(np_dir, 'testcheck_limits.yaml')
axis_limits.save_limits(lim_path, m.cpr, {1:h1,2:h2}, [(h1+rad(a), h2+rad(b)) for a,b in [(-10,-10),(10,-10),(10,10),(-10,10)]])
sim.close()
cfg = os.path.join(np_dir, 'config.yaml')
assert not os.path.exists(cfg)
open(cfg,'w').write('axis_limits:\n    file: testcheck_limits.yaml\n    margin_degrees: 3.0\n    require_home_at_start: false\n')
try:
    screen = pyte.Screen(110, 40); stream = pyte.ByteStream(screen)
    c = pexpect.spawn('python3 teach_limits.py --hootl --telescope-protocol skywatcher-mount-head-usb --check',
                      cwd=np_dir, dimensions=(40, 110), timeout=30)
    def pump(t=0.3):
        end = time.time() + t
        while time.time() < end:
            try: stream.feed(c.read_nonblocking(65536, timeout=0.05))
            except pexpect.TIMEOUT: pass
            except pexpect.EOF: return
    def text(): return '\n'.join(l.rstrip() for l in screen.display if l.strip())
    pump(4)
    for _ in range(4): c.send('+'); pump(0.1)
    t = time.time()
    while time.time() - t < 6: c.send('\x1b[C'); pump(0.05)      # 6 s rechts mit 5 Grad/s
    pump(2)
    c.send('m'); pump(0.5)
    print(text())
    c.send('q'); c.expect(pexpect.EOF)
finally:
    os.remove(cfg); os.remove(lim_path)

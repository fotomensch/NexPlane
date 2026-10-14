import pexpect, time, sys, pyte
np_dir = sys.argv[1]
for args, expect in [('--check --profile kamera', 'Profil kamera'), ('--check', 'Profil tubus'),
                     ('--edit --profile tubus', 'Sperrzone(n)'), ('--profile gibtsnicht', 'gibt es nicht')]:
    screen = pyte.Screen(130, 40); stream = pyte.ByteStream(screen)
    c = pexpect.spawn(f'python3 teach_limits.py --hootl --telescope-protocol skywatcher-mount-head-usb {args}',
                      cwd=np_dir, dimensions=(40, 130), timeout=20)
    end = time.time() + 6; raw = b''
    while time.time() < end:
        try:
            chunk = c.read_nonblocking(65536, timeout=0.2); raw += chunk; stream.feed(chunk)
        except (pexpect.TIMEOUT, pexpect.EOF): 
            if not c.isalive(): break
    txt = '\n'.join(screen.display) + raw.decode(errors='ignore')
    line = next((l.strip() for l in screen.display if expect in l), None) or (expect if expect in txt else None)
    print(f'{args:28s} ->', 'OK  ' if line else 'FEHL', (line or txt[-200:])[:110])
    if c.isalive(): c.send('q'); time.sleep(0.5); c.send('q'); c.terminate(force=True)

import json, time, urllib.request, re, os, struct, sys, csv, glob
sys.path.insert(0, '.')
import gamepad
base = 'http://127.0.0.1:8802'
token = re.search(r"TOKEN = '([^']+)'", urllib.request.urlopen(base + '/').read().decode()).group(1)
def req(path, data=None):
    r = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(), headers={'X-NexPlane-Token': token, 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())
w = os.open('padfifo', os.O_WRONLY)
ev = lambda t, c, v: os.write(w, struct.pack(gamepad.EVENT_FMT, 0, 0, t, c, v))
time.sleep(4); print(req('/api/track', {'hex': '0x0aa0001'})); time.sleep(30)
t_stick = time.time(); ev(3, 0, 255); time.sleep(3); ev(3, 0, 128); t_end = time.time()
time.sleep(8); s = req('/api/state'); print('Korrektur', s['correction']['ra'], s['correction']['dec']); req('/api/stop', {})
rows = list(csv.DictReader(open(glob.glob('protokolle/verfolgung_*.csv')[0])))
for r in rows:
    t = float(r['zeit'])
    if t_stick - 4 < t < t_end + 8 and int(t*5) % 5 == 0:
        print(f"t={t - t_stick:+5.1f}  ra_raw {float(r['ra_raw']):9.3f} dec_raw {float(r['dec_raw']):8.3f}  korr_ra {float(r['korr_ra']):6.3f}  tele_az {float(r['tele_az']):7.2f} flug_az {float(r['flug_az']):7.2f}")

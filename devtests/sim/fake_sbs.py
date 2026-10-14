'''Simulierter dump1090: SBS-1-Daten fuer einige Flugzeuge auf einem TCP-Port.'''
import math, socket, sys, threading, time
LAT0, LON0 = float(sys.argv[2]), float(sys.argv[3])
PORT = int(sys.argv[1])
R = 6371000.0
# hex, callsign, Start-Nord/Ost (km), Kurs, Geschwindigkeit m/s, Hoehe m
PLANES = [('3c6444', 'DLH4AB', -30, 2, 5, 230, 10600),
          ('4ca7b1', 'RYR82QX', 10, 40, 260, 220, 11200),
          ('3c65a3', 'EWG7LM', 60, -50, 120, 200, 7600),
          ('440123', 'AUA111', -80, -90, 45, 210, 3000)]
T0 = time.time()
def fields(**kw):
    f = [''] * 22; f[0] = 'MSG'
    for k, v in kw.items(): f[int(k[1:])] = str(v)
    return ','.join(f)
def lines():
    t = time.time() - T0
    out = []
    for hx, cs, n0, e0, trk, v, h in PLANES:
        n = n0 * 1000 + v * t * math.cos(math.radians(trk)); e = e0 * 1000 + v * t * math.sin(math.radians(trk))
        lat = LAT0 + math.degrees(n / R); lon = LON0 + math.degrees(e / (R * math.cos(math.radians(LAT0))))
        out.append(fields(f1=1, f4=hx, f10=cs))
        out.append(fields(f1=3, f4=hx, f11=round(h / 0.3048), f14=f'{lat:.5f}', f15=f'{lon:.5f}'))
        out.append(fields(f1=4, f4=hx, f12=round(v / 0.514444), f13=trk, f16=0))
    return out
def client(c):
    try:
        while True:
            c.sendall(('\r\n'.join(lines()) + '\r\n').encode()); time.sleep(0.5)
    except OSError:
        pass
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('127.0.0.1', PORT)); s.listen()
while True:
    c, _ = s.accept(); threading.Thread(target=client, args=(c,), daemon=True).start()

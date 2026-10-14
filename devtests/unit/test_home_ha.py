# Mathematik der Grob-Ausrichtung: h_home aus einer Kalibrierung speichern und daraus spaeter
# (anderer Programmstart, andere Zeit) dieselbe Kalibrierung wiederherstellen.
import sys, math
sys.path.insert(0, sys.argv[1])
import eq_flip, pointing_model
W = eq_flip.SIDEREAL_RAD_PER_S
fails = []
def check(c, m):
    print(('OK   ' if c else 'FEHL ') + m)
    if not c: fails.append(m)
m = pointing_model.Model(); m.set_lst(1.0, 1000.0)
home = (0.3, 4.2)           # Achsstellungen in Home (rad), fest seit dem Einschalten
# Lauf 1: Start um t=1000, ausgerichtet mit ra_cal1, dec_cal1, zur Zeit t=1500
start1, t1 = 1000.0, 1500.0
ra_cal1 = 2.0
ra_raw_home = W * (t1 - start1) - home[0]
h_home = m.lst(t1) - (ra_raw_home + ra_cal1)
# Lauf 2: neuer Programmstart (start_time 5000), Grob-Ausrichtung zur Zeit 5200
start2, t2 = 5000.0, 5200.0
ra_raw_home2 = W * (t2 - start2) - home[0]
ra_cal2 = m.lst(t2) - ra_raw_home2 - h_home
# Pruefen: eine beliebige Achsstellung zeigt in beiden Laeufen auf dieselbe Stundenwinkel-Richtung
ax1 = -0.7
for t in (t2, t2 + 3600):
    ra_raw_1 = W * (t - start1) - ax1; ra_raw_2 = W * (t - start2) - ax1
    h1 = m.lst(t) - (ra_raw_1 + ra_cal1); h2 = m.lst(t) - (ra_raw_2 + ra_cal2)
    d = math.degrees(abs((h1 - h2 + math.pi) % (2 * math.pi) - math.pi))
    check(d < 1e-9, f'gleiche Richtung nach Neustart (Abweichung {d:.1e} Grad)')
print('FEHLER:', fails or 'keine')

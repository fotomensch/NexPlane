import sys, math, random
sys.path.insert(0, sys.argv[1])
import axis_limits as al
random.seed(3)
def star(n):
    return [((0.5 + random.random()) * math.cos(2 * math.pi * k / n), (0.5 + random.random()) * math.sin(2 * math.pi * k / n)) for k in range(n)]
def old_insert(poly, p):
    n = len(poly)
    for i in sorted(range(n), key=lambda i: al.segment_distance(p, poly[i], poly[(i + 1) % n])):
        new = poly[:i + 1] + [p] + poly[i + 1:]
        if not al.polygon_problems(new): return new
    return None
samples = [(random.uniform(-1.6, 1.6), random.uniform(-1.6, 1.6)) for _ in range(1500)]
bad_old = bad_new = tried = none_new = 0
for _ in range(300):
    P = star(random.choice([8, 20, 40]))
    p = (random.uniform(-1.7, 1.7), random.uniform(-1.7, 1.7))
    if al.point_in_polygon(p, P): continue
    tried += 1
    for f, kind in ((old_insert, 'old'), (lambda a, b: al.insert_vertex(a, b, True), 'new')):
        Q = f(P, p)
        if Q is None:
            if kind == 'new': none_new += 1
            continue
        lost = any(al.point_in_polygon(s, P) and not al.point_in_polygon(s, Q) for s in samples)
        if lost:
            if kind == 'old': bad_old += 1
            else: bad_new += 1
# holes: point inside, must only shrink
bad_hole = 0
for _ in range(300):
    H = star(random.choice([8, 20]))
    p = (random.uniform(-1.2, 1.2), random.uniform(-1.2, 1.2))
    if not al.point_in_polygon(p, H): continue
    Q = al.insert_vertex(H, p, grow=False)
    if Q is None: continue
    if any(al.point_in_polygon(s, Q) and not al.point_in_polygon(s, H) for s in samples): bad_hole += 1
print(f'{tried} Punkte ausserhalb: alter Code verkleinert anderswo in {bad_old} Faellen, neuer in {bad_new} (kein Rand moeglich: {none_new})')
print(f'Sperrzonen: neuer Code vergroessert eine Sperrzone in {bad_hole} Faellen')
sys.exit(1 if bad_new or bad_hole else 0)

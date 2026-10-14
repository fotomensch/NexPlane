import sys, math, os
sys.path.insert(0, sys.argv[1]); out = sys.argv[2]
import limits_plot, axis_limits
from axis_limits import rad
home = (rad(327.68), rad(327.68))
def P(pts): return [(home[0]+rad(a), home[1]+rad(b)) for a,b in pts]
# nur Linie A (gebogen) -> Schlusslinie kreuzt
wrong = P([(-60,-40),(-40,-55),(-20,-62),(0,-65),(20,-62),(40,-55),(60,-40),(60,45),(40,60),(20,68),(-5,62),(10,64),(-20,68),(-40,60),(-60,45)])
right = P([(-60,-40),(-40,-55),(-20,-62),(0,-65),(20,-62),(40,-55),(60,-40),
           (60,45),(40,60),(20,68),(0,70),(-20,68),(-40,60),(-60,45)])
for name, poly, cur in [('falsch', wrong, (home[0]+rad(10), home[1]-rad(20))), ('richtig', right, home)]:
    probs = axis_limits.polygon_problems(poly)
    status = str(probs[0]) if probs else 'Outline is valid.'
    print(name, '->', status[:90])
    limits_plot.write_svg(os.path.join(out, f'vorschau_{name}.svg'), home, poly, cur, rad(3), status)
    print('\n'.join(limits_plot.render_ascii(home, poly, cur, 78, 16)))

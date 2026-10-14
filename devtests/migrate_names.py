#!/usr/bin/env python3
'''
One-time migration of the files NexPlane writes next to config.yaml, after the German file names
and keys were renamed to English. Writes the new files and keeps the old ones; nothing is
overwritten. config.yaml itself is never changed: keys that need renaming are only listed.

    ./devtests/migrate_names.py [CONFIG_DIR]      (default: the NexPlane directory)

  orte.yaml           -> places.yaml          (typ: standort/landmarke -> type: location/landmark)
  home_richtung.yaml  -> home_direction.yaml  (home_stundenwinkel_grad -> hour_angle_degrees)
  protokolle/         -> logs/                (old logs stay where they are)
  config.yaml keys    brennweiten_mm -> focal_lengths_mm, brennweite_mm -> focal_length_mm,
                      sensor_breite_mm -> sensor_width_mm; profile name "standard" -> "default"
'''
import os
import sys

import yaml

d = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..'))
print('Config directory:', d)

def write_new(name: str, header: str, data: dict) -> None:
    path = os.path.join(d, name)
    if os.path.exists(path):
        print(f'  {name} exists already, not touched.')
        return
    with open(path, 'w') as f:
        f.write(header)
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=True)
    print(f'  wrote {name}')

old = os.path.join(d, 'orte.yaml')
if os.path.exists(old):
    locs = (yaml.safe_load(open(old)) or {}).get('locations') or {}
    types = {'standort': 'location', 'landmarke': 'landmark'}
    new = {}
    for k, v in locs.items():
        v = dict(v)
        v['type'] = types.get(v.pop('typ', 'standort'), 'location')
        new[k] = v
    write_new('places.yaml', '# Written by NexPlane (browser, places editor). Own locations and landmarks.\n',
              {'locations': new})

old = os.path.join(d, 'home_richtung.yaml')
if os.path.exists(old):
    h = yaml.safe_load(open(old)) or {}
    if 'home_stundenwinkel_grad' in h:
        write_new('home_direction.yaml',
                  '# Written by NexPlane: hour angle of the RA axis in the home position.\n'
                  '# Used for rough alignment without a landmark. Delete it if the mount was rebuilt.\n',
                  {'hour_angle_degrees': float(h['home_stundenwinkel_grad']), 'saved': str(h.get('gespeichert', ''))})

if os.path.isdir(os.path.join(d, 'protokolle')):
    print('  protokolle/ stays as it is; new logs go to logs/ (CSV columns now have English names).')

cfg = os.path.join(d, 'config.yaml')
if os.path.exists(cfg):
    text = open(cfg).read()
    keys = {'brennweiten_mm': 'focal_lengths_mm', 'brennweite_mm': 'focal_length_mm', 'sensor_breite_mm': 'sensor_width_mm'}
    todo = [f'{a} -> {b}' for a, b in keys.items() if a + ':' in text]
    data = yaml.safe_load(text) or {}
    lim = data.get('axis_limits') or {}
    if lim.get('file') and not lim.get('profiles'):
        todo.append('the single limits file is now profile "default" (was "standard"); nothing to change')
    if 'dump1090:' not in text:
        todo.append('start_nexplane.py: add "dump1090: /path/to/dump1090" (the executable) unless dump1090 is on the PATH; '
                    'it now uses telescope_protocol from config.yaml and the Python that runs it '
                    '(run it with the venv Python)')
    if todo:
        print('  Please change in config.yaml by hand: ' + '; '.join(todo))
print('Done. The old files can be deleted once NexPlane runs with the new ones.')

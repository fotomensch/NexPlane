'''
Own focal lengths for weighting sync points, added in the browser.

They are stored in focal_lengths.yaml (next to config.yaml) and offered together with
focal_lengths_mm from config.yaml. config.yaml itself is not modified.
'''

import math
import os

import yaml

from messages import Msg

MIN_MM = 10.0
MAX_MM = 5000.0

def path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'focal_lengths.yaml')

def load() -> list[float]:
    '''Focal lengths added in the browser (mm, sorted); invalid entries are skipped.'''
    try:
        with open(path()) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return []
    values = []
    for v in data.get('focal_lengths_mm') or []:
        try:
            mm = float(v)
        except (TypeError, ValueError):
            continue
        if validate(mm) is None:
            values.append(mm)
    return sorted(set(values))

def _write(values: list[float]) -> None:
    tmp = path() + '.tmp'
    with open(tmp, 'w') as f:
        f.write('# Written by NexPlane (browser). Own focal lengths for weighting sync points.\n')
        yaml.safe_dump({'focal_lengths_mm': sorted(values)}, f)
    os.replace(tmp, path())

def validate(mm: float) -> Msg | None:
    '''Error message for an invalid focal length, or None.'''
    if not math.isfinite(mm) or not MIN_MM <= mm <= MAX_MM:
        return Msg('Focal length: {lo:.0f} to {hi:.0f} mm', lo=MIN_MM, hi=MAX_MM)
    return None

def same(a: float, b: float) -> bool:
    '''Focal lengths that differ by less than 0.5 mm count as the same (the list shows whole mm).'''
    return abs(a - b) < 0.5

def add(mm: float, config_values: list[float]) -> Msg | None:
    '''Add a focal length (rounded to whole mm). Returns an error message or None.'''
    err = validate(mm)
    if err:
        return err
    mm = float(round(mm))   # whole mm, as shown in the list
    own = load()
    if any(same(mm, v) for v in own + config_values):
        return Msg('{mm:.0f} mm is already in the list.', mm=mm)
    _write(own + [mm])
    return None

def remove(mm: float) -> Msg | None:
    '''Remove a focal length added in the browser. Returns an error message or None.'''
    own = load()
    keep = [v for v in own if not same(v, mm)]
    if len(keep) == len(own):
        return Msg('{mm:.0f} mm comes from config.yaml (focal_lengths_mm) and can only be removed there.', mm=mm)
    _write(keep)
    return None

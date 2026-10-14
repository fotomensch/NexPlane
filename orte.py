'''
User-defined locations and landmarks from the browser UI.

They are stored in orte.yaml (next to config.yaml) and merged into "locations"
when the configuration is read. config.yaml itself is not modified.
Entries with typ: landmarke appear only as alignment targets, not as locations.
'''

import math
import os
import re

from typing import Any

import yaml

def path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'orte.yaml')

def load() -> dict[str, dict[str, Any]]:
    try:
        with open(path()) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    locs = data.get('locations') or {}
    return {str(k): dict(v) for k, v in locs.items() if isinstance(v, dict)}

def _write(locs: dict[str, dict[str, Any]]) -> None:
    tmp = path() + '.tmp'
    with open(tmp, 'w') as f:
        f.write('# Written by NexPlane (browser, places editor). Own locations and landmarks.\n')
        yaml.safe_dump({'locations': locs}, f, allow_unicode=True, sort_keys=True)
    os.replace(tmp, path())

NAME_RE = re.compile(r'^[\w äöüÄÖÜß.\-()]{1,40}$')

def validate(name: str, typ: str, lat: float, lon: float, alt: float) -> str | None:
    if not NAME_RE.match(name or '') or name.strip() != name:
        return 'Name: 1-40 Zeichen, Buchstaben, Ziffern, Leerzeichen, . - ( ) _'
    if typ not in ('standort', 'landmarke'):
        return 'Typ muss Standort oder Landmarke sein'
    for v in (lat, lon, alt):
        if not math.isfinite(v):
            return 'Ungültige Zahl'
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return 'Breite -90..90, Länge -180..180'
    if not -500 <= alt <= 9000:
        return 'Höhe -500..9000 m'
    return None

def save(name: str, typ: str, lat: float, lon: float, alt: float, config_locations: dict[str, Any]) -> str | None:
    '''Saves/replaces an entry. Returns an error message or None.'''
    err = validate(name, typ, lat, lon, alt)
    if err:
        return err
    own = load()
    if name in config_locations and name not in own:
        return f'"{name}" steht bereits in config.yaml und kann hier nicht überschrieben werden.'
    own[name] = {'lat_degrees': round(lat, 7), 'lon_degrees': round(lon, 7), 'alt_meters': round(alt, 1), 'typ': typ}
    _write(own)
    return None

def delete(name: str) -> str | None:
    own = load()
    if name not in own:
        return f'"{name}" ist kein im Browser angelegter Ort (Einträge aus config.yaml dort ändern).'
    del own[name]
    _write(own)
    return None

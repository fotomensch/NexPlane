import sys, math, yaml
sys.path.insert(0, '.')
import skywatcher, axis_limits, util
import astropy.coordinates as coords, astropy.units as u
from axis_limits import rad
sim = skywatcher.SkyWatcherSerialHootl(); m = skywatcher.SkyWatcher(sim)
h1, h2 = m._inquire_position(1), m._inquire_position(2)
axis_limits.save_limits('testflip_limits.yaml', m.cpr, {1:h1,2:h2},
    [(h1+rad(a), h2+rad(b)) for a,b in [(-60,-50),(60,-50),(60,50),(-60,50)]])
sim.close()
obs = coords.EarthLocation.from_geodetic(7.5*u.deg, 51.5*u.deg, 80*u.m)
lst, _ = util.altaz_to_radec(rad(30), math.pi, obs, util.get_current_time())
cal = {'mount_mode': 'eq', 'calibration': {'ra': float(lst + h1), 'dec': float(math.pi/2 - h2)}}
yaml.safe_dump(cal, open('testflip_align.yaml', 'w'))
open('config.yaml','w').write('''locations:
    testort:
        lat_degrees: 51.5
        lon_degrees: 7.5
        alt_meters: 80.0
location: testort
mount_mode: eq
telescope_protocol: skywatcher-mount-head-usb
sbs1_servers:
    - localhost:30013
axis_limits:
    file: testflip_limits.yaml
    margin_degrees: 3.0
    require_home_at_start: false
''')
print('ok', cal)

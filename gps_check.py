#!/home/linux/myvenv/bin/python3
'''
Checks whether the built-in LTE modem (e.g. Dell DW5821e) has a GPS receiver and
delivers a position.

    ./gps_check.py                 (wait up to 3 minutes for a position)
    ./gps_check.py --dauer 600     (wait longer, e.g. the first time / cold start)

Best run outdoors or near a window: the modem uses the laptop antennas,
a cold start can take several minutes.

The script
  1. shows whether mobile/WWAN is disabled via rfkill (airplane mode),
  2. asks ModemManager (mmcli) for the modem's location capabilities,
  3. enables GPS there and waits for a position,
  4. additionally listens passively on the modem ports for NMEA data ($GPGGA ...).
The mount (Prolific/CH340/FTDI port) is not touched.
'''

import argparse
import glob
import os
import re
import select
import shutil
import subprocess
import time

MODEM_DRIVERS = ('option', 'option1', 'qcserial', 'sierra')

def run(cmd: list[str], timeout: float = 15) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, f'{cmd[0]} nicht installiert'
    except subprocess.TimeoutExpired:
        return 124, 'Zeitueberschreitung'

def driver(tty: str) -> str:
    try:
        return os.path.basename(os.path.realpath(f'/sys/class/tty/{os.path.basename(tty)}/device/driver'))
    except OSError:
        return ''

def parse_nmea_gga(line: str) -> tuple[float, float, float, int, int] | None:
    '''$..GGA -> (latitude, longitude, altitude, fix quality, satellites) or None.'''
    f = line.split(',')
    if len(f) < 10 or not f[0].endswith('GGA') or not f[2] or not f[4]:
        return None
    try:
        lat = int(f[2][:2]) + float(f[2][2:]) / 60
        lon = int(f[4][:3]) + float(f[4][3:]) / 60
        if f[3] == 'S':
            lat = -lat
        if f[5] == 'W':
            lon = -lon
        return lat, lon, float(f[9] or 0), int(f[6] or 0), int(f[7] or 0)
    except ValueError:
        return None

def inject_xtra(modem: str, location_status: str) -> None:
    import urllib.request
    urls = re.findall(r'https?://\S+?\.bin', location_status) or ['https://path1.xtracloud.net/xtra3grcej.bin']
    path = '/tmp/nexplane_xtra.bin'
    for url in urls:
        try:
            print(f'  Lade Hilfsdaten von {url} ...')
            with urllib.request.urlopen(url, timeout=20) as r, open(path, 'wb') as f:
                f.write(r.read())
            break
        except Exception as e:
            print(f'    fehlgeschlagen: {e}')
    else:
        print('  Hilfsdaten konnten nicht geladen werden (Internet?).')
        return
    code, out = run(['mmcli', '-m', modem, f'--location-inject-assistance-data={path}'], timeout=60)
    print('  Hilfsdaten ans Modem: ' + (out or 'ok'))
    if code != 0:
        print('  -> Ging nicht. Mit sudo erneut versuchen.')

def gsv_summary(sats: dict[str, int]) -> str:
    good = sorted((snr for snr in sats.values() if snr > 0), reverse=True)
    return f'{len(sats)} Satelliten gesehen, {len(good)} mit Signal' + (f' (beste {good[:4]} dB)' if good else '')

def main() -> None:
    parser = argparse.ArgumentParser(description='Prueft den GPS-Empfaenger im LTE-Modem.')
    parser.add_argument('--dauer', type=int, default=180, help='Sekunden auf eine Position warten (Standard 180)')
    parser.add_argument('--xtra', action='store_true',
                        help='Hilfsdaten (Satellitenbahnen) ueber das Internet des Laptops laden und ans Modem geben; '
                             'verkuerzt den Kaltstart stark. Braucht meist sudo.')
    args = parser.parse_args()

    print('== 1. Flugmodus / rfkill')
    code, out = run(['rfkill', 'list'])
    print(out if code == 0 else f'  rfkill: {out}')
    if re.search(r'(?is)wwan.*?Soft blocked: yes', out):
        print('  -> Mobilfunk (WWAN) ist abgeschaltet. Einschalten mit: rfkill unblock wwan')

    print('\n== 2. Modem-Anschluesse')
    ports = [p for p in sorted(glob.glob('/dev/ttyUSB*')) + sorted(glob.glob('/dev/wwan*')) if driver(p) in MODEM_DRIVERS or '/wwan' in p]
    for p in ports:
        print(f'  {p}  (Treiber {driver(p) or "?"})')
    if not ports:
        print('  keine Modem-Anschluesse gefunden')

    print('\n== 3. ModemManager')
    modem = None
    if not shutil.which('mmcli'):
        print('  mmcli nicht installiert (Paket modemmanager). Ueberspringe.')
    else:
        code, out = run(['mmcli', '-L'])
        print('  ' + out.replace('\n', '\n  '))
        m = re.search(r'/Modem/(\d+)', out)
        if m:
            modem = m.group(1)
            code, out = run(['mmcli', '-m', modem])
            for line in out.splitlines():
                if any(k in line for k in ('model', 'manufacturer', 'firmware', 'state', 'power state')):
                    print('  ' + line.strip())
            code, out = run(['mmcli', '-m', modem, '--location-status'])
            print('  Ortung:\n  ' + out.replace('\n', '\n  '))
            if 'gps' not in out.lower():
                print('  -> ModemManager meldet keine GPS-Faehigkeit fuer dieses Modem.')
            if args.xtra:
                inject_xtra(modem, out)
            print('  Schalte GPS ein ...')
            code, out = run(['mmcli', '-m', modem, '--location-enable-gps-nmea', '--location-enable-gps-raw'])
            print('  ' + (out or 'ok'))
            if code != 0 and ('not authorized' in out.lower() or 'permission' in out.lower()):
                print('  -> Keine Berechtigung. Das Skript bitte noch einmal mit sudo starten.')
        else:
            print('  Kein Modem bei ModemManager angemeldet (Flugmodus? ModemManager laeuft nicht?).')

    print(f'\n== 4. Warte bis zu {args.dauer} s auf eine Position (Strg+C bricht ab)')
    # Listen passively on the modem ports for NMEA (read only, send no commands)
    fds: dict[int, str] = {}
    for p in ports:
        if not p.startswith('/dev/ttyUSB'):
            continue
        try:
            fds[os.open(p, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)] = p
        except OSError as e:
            print(f'  {p} nicht lesbar ({e.strerror})')
    buffers = {fd: '' for fd in fds}
    nmea_seen: set[str] = set()
    sats: dict[str, int] = {}
    last_report = 0.0
    t0 = time.monotonic()
    last_mm = 0.0
    found = None
    try:
        while time.monotonic() - t0 < args.dauer and found is None:
            if fds:
                ready, _, _ = select.select(list(fds), [], [], 1.0)
                for fd in ready:
                    try:
                        buffers[fd] += os.read(fd, 4096).decode(errors='ignore')
                    except OSError:
                        continue
                    *lines, buffers[fd] = buffers[fd].split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('$'):
                            if fds[fd] not in nmea_seen:
                                print(f'  NMEA-Daten auf {fds[fd]}: {line[:60]}')
                                nmea_seen.add(fds[fd])
                            if 'GSV' in line[:7]:
                                f = line.split('*')[0].split(',')
                                for k in range(4, len(f) - 3, 4):
                                    if f[k]:
                                        sats[line[1:3] + f[k]] = int(f[k + 3]) if f[k + 3].isdigit() else 0
                            g = parse_nmea_gga(line)
                            if g and g[3] > 0:
                                found = (g, f'NMEA auf {fds[fd]}')
            else:
                time.sleep(1.0)
            if modem and time.monotonic() - last_mm > 5:
                last_mm = time.monotonic()
                code, out = run(['mmcli', '-m', modem, '--location-get'])
                for line in out.splitlines():
                    if 'GGA' in line:
                        g = parse_nmea_gga(line[line.index('$'):].strip()) if '$' in line else None
                        if g and g[3] > 0:
                            found = (g, 'ModemManager (NMEA)')
                m_lat = re.search(r'latitude:\s*([-\d.]+)', out)
                m_lon = re.search(r'longitude:\s*([-\d.]+)', out)
                if m_lat and m_lon and found is None and float(m_lat.group(1)) != 0:
                    m_alt = re.search(r'altitude:\s*([-\d.]+)', out)
                    found = ((float(m_lat.group(1)), float(m_lon.group(1)),
                              float(m_alt.group(1)) if m_alt else 0.0, 1, 0), 'ModemManager')
            if time.monotonic() - last_report > 30:
                last_report = time.monotonic()
                print(f'  {int(time.monotonic() - t0):4d} s: noch keine Position; {gsv_summary(sats)}', flush=True)
    except KeyboardInterrupt:
        pass
    for fd in fds:
        os.close(fd)

    print('\n== Ergebnis')
    if found:
        (lat, lon, alt, fix, sats), src = found
        print(f'  GPS FUNKTIONIERT ({src}): Breite {lat:.6f}, Laenge {lon:.6f}, Hoehe {alt:.0f} m'
              + (f', {sats} Satelliten' if sats else ''))
    elif nmea_seen:
        print('  GPS-Empfaenger vorhanden (NMEA-Daten kommen), aber noch keine Position. '
              'Laenger und unter freiem Himmel versuchen: --dauer 600')
    elif modem:
        print('  Keine Position und keine NMEA-Daten. Moeglich: Modem hat kein GPS, GPS ist in der Firmware '
              'abgeschaltet, oder es braucht laenger (--dauer 600, draussen).')
    else:
        print('  Kein Modem erreichbar. rfkill/Flugmodus und ModemManager pruefen.')
    print('  Bitte die komplette Ausgabe zurueckschicken.')

if __name__ == '__main__':
    main()

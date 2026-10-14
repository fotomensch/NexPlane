#!/home/linux/myvenv/bin/python3
'''
Starts everything NexPlane needs, each in its own GNOME Terminal window:

  1. dump1090          (aircraft data from the RTL stick, port 30003)
  2. telescope_server  (connection to the mount, UDP port 45345)
  3. satellites.py     (only if requested, port 40004)
  4. nexplane.py --web (browser UI; alignment always in the browser)

The order matters: NexPlane connects to the data sources only once at
startup. Therefore the script waits until dump1090 (and satellites.py, if used)
are reachable before starting NexPlane.

Usage:
    ./start_nexplane.py            normal start
    ./start_nexplane.py --hootl    trial run with simulated mount

A program that is already running (port in use) is not started a second time.
To quit: exit NexPlane (button in the browser, Ctrl+C or closing its window). The
helper windows started by this script (dump1090, telescope_server, satellites)
then close automatically. Programs that were already running before are left alone.
If NexPlane ends with an error, its own window stays open so the message can be read.
'''

import argparse
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time

NEXPLANE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = '/home/linux/myvenv/bin/python3'
DUMP1090_DIR = '/home/linux/dump1090'
DUMP1090 = os.path.join(DUMP1090_DIR, 'dump1090')

PORT_DUMP1090 = 30003
PORT_TELESCOPE = 45345
PORT_SATELLITES = 40004

TLE_FILES = ['tle/visual.txt', 'tle/stations.txt']
TLE_MAX_AGE_DAYS = 2.0

def port_open(port: int) -> bool:
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5):
            return True
    except OSError:
        return False

def udp_port_in_use(port: int) -> bool:
    '''
    telescope_server listens via UDP (not TCP). Whether it is running is detected
    by the port no longer being bindable.
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('0.0.0.0', port))
        return False
    except OSError:
        return True
    finally:
        sock.close()

def wait_for_port(port: int, name: str, timeout_s: float, udp: bool = False) -> bool:
    print(f'  warte auf {name} (Port {port}) ', end='', flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if (udp_port_in_use(port) if udp else port_open(port)):
            print('bereit')
            return True
        print('.', end='', flush=True)
        time.sleep(1)
    print(' keine Antwort')
    return False

RUN_DIR = os.path.join(os.environ.get('XDG_RUNTIME_DIR') or '/tmp', f'nexplane-{os.getuid()}')

def prepare_run_dir() -> None:
    '''Directory for the PID files of the helper windows started by this script.'''
    os.makedirs(RUN_DIR, mode=0o700, exist_ok=True)
    for name in os.listdir(RUN_DIR):
        if name.endswith('.pid'):
            try:
                os.remove(os.path.join(RUN_DIR, name))
            except OSError:
                pass

def open_terminal(title: str, workdir: str, command: str, pid_name: str | None = None) -> None:
    '''
    Command in a new GNOME Terminal window; the window stays open after it finishes (to read errors).
    With pid_name the window's shell writes its PID to RUN_DIR, so that the NexPlane window can
    close it (together with the program) when NexPlane ends.
    '''
    pid_part = f'echo $$ > {shlex.quote(os.path.join(RUN_DIR, pid_name + ".pid"))}; ' if pid_name else ''
    script = (f'{pid_part}cd {shlex.quote(workdir)} && {command}; '
              'status=$?; echo; echo "--- beendet (Status $status) ---"; '
              'read -r -p "Enter schliesst dieses Fenster." _')
    subprocess.Popen(['gnome-terminal', f'--title={title}', '--', 'bash', '-c', script],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def open_nexplane_terminal(workdir: str, command: str) -> None:
    '''
    NexPlane in its own window. When NexPlane ends (normally, Ctrl+C or window closed), the
    helper windows listed in RUN_DIR are closed: each window shell is the leader of its own
    process group, so signalling the group ends the program and the shell, and the window closes.
    After a normal end the NexPlane window closes as well; after an error it stays open.
    '''
    run = shlex.quote(RUN_DIR)
    script = (
        'cleanup() { '
        f'  for f in {run}/*.pid; do '
        '    [ -e "$f" ] || continue; pid=$(cat "$f"); rm -f "$f"; '
        '    [ -n "$pid" ] || continue; '
        '    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null; '
        '    for i in 1 2 3 4 5 6; do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done; '
        '    kill -KILL -- "-$pid" 2>/dev/null; '
        '  done; '
        '}; '
        'trap cleanup EXIT; trap "exit 129" HUP; trap "exit 143" TERM; '
        f'cd {shlex.quote(workdir)} && {command}; '
        'status=$?; '
        'echo; echo "--- NexPlane beendet (Status $status), schliesse Hilfsfenster ---"; cleanup; '
        'if [ "$status" -ne 0 ] && [ "$status" -ne 130 ]; then read -r -p "Enter schliesst dieses Fenster." _; fi'
    )
    subprocess.Popen(['gnome-terminal', '--title=NexPlane', '--', 'bash', '-c', script],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ask_yes_no(question: str, default: bool = False) -> bool:
    hint = '[J/n]' if default else '[j/N]'
    while True:
        answer = input(f'{question} {hint} ').strip().lower()
        if not answer:
            return default
        if answer in ('j', 'ja', 'y', 'yes'):
            return True
        if answer in ('n', 'nein', 'no'):
            return False

def tle_outdated() -> bool:
    for rel in TLE_FILES:
        path = os.path.join(NEXPLANE_DIR, rel)
        if not os.path.exists(path):
            return True
        if (time.time() - os.path.getmtime(path)) / 86400 > TLE_MAX_AGE_DAYS:
            return True
    return False

def check_prerequisites() -> list[str]:
    problems = []
    if shutil.which('gnome-terminal') is None:
        problems.append('gnome-terminal nicht gefunden.')
    if not os.access(PYTHON, os.X_OK):
        problems.append(f'Python nicht gefunden: {PYTHON}')
    if not os.access(DUMP1090, os.X_OK):
        problems.append(f'dump1090 nicht gefunden: {DUMP1090}')
    for f in ('nexplane.py', 'telescope_server.py', 'satellites.py', 'webgui.py'):
        if not os.path.exists(os.path.join(NEXPLANE_DIR, f)):
            problems.append(f'{f} fehlt in {NEXPLANE_DIR}')
    return problems

def main() -> None:
    parser = argparse.ArgumentParser(description='Startet dump1090, telescope_server und NexPlane (Browser).')
    parser.add_argument('--hootl', action='store_true', help='Probelauf mit simulierter Montierung')
    args = parser.parse_args()

    problems = check_prerequisites()
    if problems:
        print('Kann nicht starten:')
        for p in problems:
            print(' -', p)
        sys.exit(1)

    prepare_run_dir()
    print('NexPlane-Start' + (' (Probelauf mit simulierter Montierung)' if args.hootl else ''))
    print()
    with_satellites = ask_yes_no('Satelliten anzeigen?', default=False)
    if not args.hootl:
        input('Montierung in der Home-Stellung eingeschaltet und per USB verbunden? Dann Enter. ')
    print()

    # 1) dump1090
    if port_open(PORT_DUMP1090):
        print('dump1090 laeuft bereits.')
    else:
        print('Starte dump1090 ...')
        open_terminal('dump1090', DUMP1090_DIR, f'{shlex.quote(DUMP1090)} --interactive --net', 'dump1090')
        if not wait_for_port(PORT_DUMP1090, 'dump1090', 20):
            print('dump1090 ist nicht erreichbar. Steckt der RTL-Stick? Fehler stehen im dump1090-Fenster.')
            sys.exit(1)

    # 2) telescope_server (not needed with --hootl: NexPlane simulates the mount itself)
    if not args.hootl:
        if udp_port_in_use(PORT_TELESCOPE):
            print('telescope_server laeuft bereits.')
        else:
            print('Starte telescope_server ...')
            open_terminal('telescope_server', NEXPLANE_DIR,
                          f'{shlex.quote(PYTHON)} telescope_server.py --telescope-protocol skywatcher-mount-head-usb',
                          'telescope_server')
            if not wait_for_port(PORT_TELESCOPE, 'telescope_server', 20, udp=True):
                print('telescope_server ist nicht erreichbar. Montierung eingeschaltet und USB verbunden? '
                      'Fehler stehen im telescope_server-Fenster.')
                sys.exit(1)

    # 3) satellites.py (optional)
    sbs1 = [f'localhost:{PORT_DUMP1090}']
    if with_satellites:
        if port_open(PORT_SATELLITES):
            print('satellites.py laeuft bereits.')
            sbs1.append(f'localhost:{PORT_SATELLITES}')
        else:
            command = f'{shlex.quote(PYTHON)} satellites.py'
            if tle_outdated():
                print('Satellitendaten fehlen oder sind aelter als 2 Tage, sie werden zuerst neu geladen.')
                command = '(cd tle && ./fetch.sh); ' + command
            print('Starte satellites.py ...')
            open_terminal('satellites', NEXPLANE_DIR, command, 'satellites')
            if wait_for_port(PORT_SATELLITES, 'satellites.py', 60):
                sbs1.append(f'localhost:{PORT_SATELLITES}')
            else:
                print('satellites.py ist nicht erreichbar, NexPlane startet ohne Satelliten.')

    # 4) NexPlane with browser UI, without saved alignment
    nexplane_args = ['--web']
    for server in sbs1:
        nexplane_args += ['--sbs1', server]
    if args.hootl:
        nexplane_args.append('--hootl')
    print('Starte NexPlane ...')
    open_nexplane_terminal(NEXPLANE_DIR,
                           f'{shlex.quote(PYTHON)} nexplane.py ' + ' '.join(shlex.quote(a) for a in nexplane_args))
    print()
    print('Fertig. Der Browser oeffnet sich gleich (http://127.0.0.1:8765/).')
    print('Dort zuerst ausrichten: Karte "Steuerung & Ausrichtung".')
    print('Beim Beenden von NexPlane schliessen sich die hier gestarteten Hilfsfenster automatisch.')

if __name__ == '__main__':
    main()

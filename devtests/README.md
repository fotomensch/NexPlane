# Entwicklungstests

Diese Skripte sind während der Entwicklung entstanden. Sie gehören nicht zum Patch für upstream.

## Unit-Tests (`unit/`)

Ohne Montierung, ohne Netz. Erstes Argument ist das Verzeichnis mit dem NexPlane-Code:

```bash
cd /tmp && /home/linux/myvenv/bin/python3 /home/linux/nexplane/NexPlane/devtests/unit/test_refine.py /home/linux/nexplane/NexPlane
```

Die meisten enden mit `FEHLER: keine` bzw. `Fehler: 0`. Aus einem leeren Arbeitsverzeichnis starten
(z. B. `/tmp`), manche legen Hilfsdateien an.

| Test | Prüft |
| --- | --- |
| `test_poly.py`, `test_poly_rest.py`, `test_check.py` | Polygon-Grenzen, Bremsen, Prüfungen |
| `test_bypass.py` | Sicheren Bereich abschalten |
| `test_refine.py`, `test_insert_grow.py` | Grenzen verfeinern, nur vergrößern / nur verkleinern |
| `test_corr.py` | Korrektur im Bild-/Achssystem, beide Seiten |
| `test_model.py`, `test_weight.py` | Polfehler-Modell, Gewichtung nach Brennweite |
| `test_home_ha.py` | Home-Richtung speichern / Grobausrichtung |
| `test_pad.py` | Gamepad über FIFO |
| `test_mapjog.py` | Stick → Fadenkreuz auf der Karte (Nord/Ost) |
| `test_prof_cli.py` | Profile auf der Kommandozeile |
| `test_plot.py` | Vorschau-SVG; zweites Argument = Ausgabeverzeichnis |
| `test_ui.py`, `test_ui_excl.py` | `teach_limits.py` im Terminal; braucht `pexpect`, `pyte`; zweites Argument = Ausgabedatei |

## Simulator-Tests (`sim/`)

**Nie im echten Projektordner ausführen** – `mkcfg.py` schreibt `config.yaml` und Limits-Dateien.

```bash
# 1. Kopie anlegen
rm -rf /tmp/np-sim && cp -r /home/linux/nexplane/NexPlane /tmp/np-sim
cp /home/linux/nexplane/NexPlane/devtests/sim/*.py /tmp/np-sim/
cd /tmp/np-sim && rm -f home_richtung.yaml orte.yaml

# 2. Simulator-Config (Ort 51.5 N / 7.5 E, Limits ±60°/±50°, Flugzeuge von Port 30013)
/home/linux/myvenv/bin/python3 mkcfg.py
printf 'web_port: 8802\n' >> config.yaml
# für Gamepad-Tests zusätzlich:
#   printf 'gamepad:\n    enabled: true\n    device: padfifo\n' >> config.yaml; mkfifo padfifo

# 3. Simulierte Flugzeuge (eigenes Terminal)
/home/linux/myvenv/bin/python3 fake_sbs2.py 30013 51.5 7.5

# 4. NexPlane mit simulierter Montierung (eigenes Terminal)
/home/linux/myvenv/bin/python3 nexplane.py --hootl --web --no-browser

# 5. Test ausführen, z. B.
/home/linux/myvenv/bin/python3 testalign_it.py
```

| Skript | Prüft | Braucht |
| --- | --- | --- |
| `testalign_it.py` | Testmodus Grobausrichtung zuhause | Playwright |
| `mapjog_it.py` | Stick bewegt Fadenkreuz in Kartenrichtung | Gamepad-FIFO |
| `refine_ui.py` | Grenzen verfeinern im Browser | Playwright |
| `pad_it.py`, `stick_it.py` | Gamepad-Belegung, Korrektur beim Verfolgen | Gamepad-FIFO, Flugzeuge |
| `aim_it.py`, `model_it.py` | Ausrichtung ohne Landmarke, Polfehler-Modell | Flugzeuge, ggf. FIFO |
| `i18n_ui.py`, `orte_ui.py`, `elev_ui.py`, `fs_ui.py` | Englisch, Orte-Editor, Höhenabfrage, Vollbild | Playwright |

UI-Tests brauchen `pip install playwright` und einen Chromium (`playwright install chromium`).
Einige Skripte setzen einen frisch gestarteten Simulator voraus (Montierung in Home); bei Bedarf
NexPlane neu starten. Die Simulator-Montierung ist ideal – Ergebnisse dort beweisen die Rechnung,
nicht die Genauigkeit am echten Himmel.

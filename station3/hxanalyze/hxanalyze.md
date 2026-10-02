<!--keywords[Analyzers, Testmode]-->

### Testmode mit Signal- und Event-Logger

- Das Waagenskript `hxFiBirdStateCt.py` hat einen SignalLogger (aktiv im Testmode), der `ramdisk/signal_hx.csv` produziert.
- Das Kameraskript `mainFoBird3.py` produziert `ramdisk/cam_events.csv`.
- beide .csv zusammen werden durch `hxanalyze/hxanalyze4srv.py` für das WebGUI (Button `actions - HX Analyze`) oder durch `hx_signalanalyzer.py -> hx_anal.bat` in Win11 ausgewertet. `hx-report.html` zeigt die Auswertung im WebGUI.
- beide .csv werden durch `cp2log.sh` beim Shutdown von `ramdisk/` nach `logs/` kopiert.

### LiveLogger im Testmode
- `hxFiBirdStateCt.py` und `mainFoBird3.py` enthalten beide einen *LiveLogger*, der das Gewichtssignal bzw. Lumensignal über einen Endpoint in `flaskBird3.py` durch `hxsignal.html` bzw. `luxsignal.html` im WebGUI darstellt (Button `action - HX Signal` bzw. `- Lux Signal`).
- Button `action - HX Reset` und `hx_reset.html` ermöglichen einen Reset der Waage, wenn sie gerade als leer beobachtet wird (innerhalb `hxFiBirdStateCt.py` via `flaskBird*.py & msgBird.py`). 


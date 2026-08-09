<!--keywords[__init__.py,import,Modul_import,PYTHONPATH]-->

**Python Import Pfade**

```
# Linux/macOS (z. B. in ~/.bashrc oder ~/.zshrc)
export PYTHONPATH="$PYTHONPATH:/pfad/zu/deinem/projekt"

# Windows (PowerShell)
$env:PYTHONPATH = "$env:PYTHONPATH;C:\pfad\zu\deinem\projekt"
```

- leeres (ohne Code) `__init__.py` macht den Ordner zum *Python Package*, der sonst ein *Namespace Package* ist.
- Python sucht beim Import in der Liste `sys.path`, siehe `listmodules.py`:
```
import sys
for p in sys.path:
    print(p)
```

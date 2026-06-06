Build Linux and Windows executables and push both to itch.io.

First, read the current version from CLAUDE.md (the line starting with `**v`), then run these commands in sequence, stopping if any step fails:

1. Build Linux:
```bash
.venv/bin/pyinstaller --onefile --noconsole --name uglycraft main.py
```

2. Build Windows:
```bash
WINEDEBUG=-all wine \
  ~/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python313/python.exe \
  -m PyInstaller --onefile --noconsole --name uglycraft main.py
```

3. Push Linux to itch.io (replace VERSION with the current version number, e.g. 1.0):
```bash
butler push dist/uglycraft dbausch/uglycraft:linux-64 --userversion VERSION
```

4. Push Windows to itch.io:
```bash
butler push dist/uglycraft.exe dbausch/uglycraft:windows-64 --userversion VERSION
```

Report the file sizes of both builds and confirm both butler pushes succeeded.

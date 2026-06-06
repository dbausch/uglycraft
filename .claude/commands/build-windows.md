Build a Windows executable using Wine + PyInstaller.

Run this command:

```bash
WINEDEBUG=-all wine \
  ~/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python313/python.exe \
  -m PyInstaller --onefile --noconsole --name uglycraft main.py
```

After it completes, confirm `dist/uglycraft.exe` exists and report its file size.

If the command fails because the Wine Python is not found, tell the user to follow the one-time setup in README.md first.

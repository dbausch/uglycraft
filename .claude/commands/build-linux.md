Build a Linux executable using PyInstaller.

Run this command:

```bash
.venv/bin/pyinstaller --onefile --noconsole --name uglycraft main.py
```

After it completes, confirm `dist/uglycraft` exists and report its file size.

If pyinstaller is not found, install it first:

```bash
.venv/bin/pip install pyinstaller
```

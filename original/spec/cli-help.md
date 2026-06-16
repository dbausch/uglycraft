# CLI help screen — --help / -h

## Status

- [ ] `resourcestring` entries for help text added to `UGLI_2_Core.inc`
- [ ] `CLIHelpText: string` function added to `UGLI_2_Core.inc`
- [ ] `ShowCLIHelp` procedure added to `UGLI_2_Core.inc`
- [ ] `TCliHelpTests` added to `UGLI_2_Test.pp` (red before implementation)
- [ ] `UGLI_2.pp` main block calls `LoadTranslation` early, then checks `-h`/`--help`
- [ ] `translations/de.po` updated with German strings; `de.mo` recompiled
- [ ] `poe build-original` passes
- [ ] `poe test-original` passes (all tests green, including new ones)
- [ ] `./UGLI_2 --help` prints correctly in English; `LANG=de_DE.UTF-8 ./UGLI_2 --help`
      prints correctly in German (confirmed by user)

---

## Output

```
UGLI 2 v2.3

Usage: UGLI_2 [options]

Options:
  -h, --help
      Show this help and exit.
  --stderr-log <file>
      Route ALSA/PortAudio messages to <file> (default: /dev/null).
      Useful when diagnosing sound hardware issues.
```

German (`LANG=de_DE.UTF-8`):
```
UGLI 2 v2.3

Verwendung: UGLI_2 [Optionen]

Optionen:
  -h, --help
      Diese Hilfe anzeigen und beenden.
  --stderr-log <Datei>
      ALSA/PortAudio-Meldungen in <Datei> schreiben (Standard: /dev/null).
      Nützlich zur Diagnose von Soundhardware-Problemen.
```

---

## What changes

### `UGLI_2_Core.inc` — new resourcestrings

```pascal
sCliUsage = 'Usage: UGLI_2 [options]';
sCliOptions = 'Options:';
sCliHelp  = 'Show this help and exit.';
sCliLog1  = 'Route ALSA/PortAudio messages to <file> (default: /dev/null).';
sCliLog2  = 'Useful when diagnosing sound hardware issues.';
```

### `UGLI_2_Core.inc` — new function and procedure

```pascal
function CLIHelpText: string;
begin
  Result :=
    'UGLI 2 v' + Version + LineEnding + LineEnding +
    sCliUsage + LineEnding + LineEnding +
    sCliOptions + LineEnding +
    '  -h, --help' + LineEnding +
    '      ' + sCliHelp + LineEnding +
    '  --stderr-log <file>' + LineEnding +
    '      ' + sCliLog1 + LineEnding +
    '      ' + sCliLog2 + LineEnding;
end;

procedure ShowCLIHelp;
begin
  Write(CLIHelpText);
  Halt(0);
end;
```

### `UGLI_2.pp` — main block prefix

Add before all existing startup code:

```pascal
LoadTranslation;
for I := 1 to ParamCount do
  if (ParamStr(I) = '--help') or (ParamStr(I) = '-h') then
    ShowCLIHelp;
```

`Init` already calls `LoadTranslation`; the early call here is purely so that
`--help` output is translated.  The double call is harmless (same locale →
same resourcestring values).

### `UGLI_2_Test.pp` — `TCliHelpTests`

| Test | Assertion |
|---|---|
| `TestHelpText_ContainsVersion` | `Pos(Version, CLIHelpText) > 0` |
| `TestHelpText_ContainsHelpFlag` | `Pos('--help', CLIHelpText) > 0` and `Pos('-h', CLIHelpText) > 0` |
| `TestHelpText_ContainsStderrLog` | `Pos('--stderr-log', CLIHelpText) > 0` |

### `translations/de.po`

New entries:

| English | German |
|---|---|
| `Usage: UGLI_2 [options]` | `Verwendung: UGLI_2 [Optionen]` |
| `Options:` | `Optionen:` |
| `Show this help and exit.` | `Diese Hilfe anzeigen und beenden.` |
| `Route ALSA/PortAudio messages to <file> (default: /dev/null).` | `ALSA/PortAudio-Meldungen in <Datei> schreiben (Standard: /dev/null).` |
| `Useful when diagnosing sound hardware issues.` | `Nützlich zur Diagnose von Soundhardware-Problemen.` |

Recompile: `msgfmt translations/de.po -o translations/de.mo`

---

## Done when

- [ ] `poe build-original` exits 0
- [ ] `poe test-original` exits 0, 128 tests pass (125 existing + 3 new)
- [ ] `./original/UGLI_2 --help` and `./original/UGLI_2 -h` both print the help
      text in English and exit 0 (confirmed by user)
- [ ] `LANG=de_DE.UTF-8 ./original/UGLI_2 --help` prints German text
      (confirmed by user)

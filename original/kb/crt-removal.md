# UGLI 2 — CRT Removal Rationale

## Why CRT Was Removed

FPC's `CRT` unit emits **SGR 1 (bold)** for bright foreground colours (indices 8–15) instead of the correct **high-intensity codes 90–97**. On many modern terminals (e.g. kitty with the Dracula theme) the Dracula palette has `color7` (LightGray) and `color15` (White) set to nearly identical values, so bold-on-base-colour makes LightGray and White visually indistinguishable. Similarly, Brown (CRT index 6) appeared as Yellow because the bold version of color6 in the Dracula theme is yellow.

CRT also emits SGR 5 (blink) for bright backgrounds (`Blink` on background), which is rarely wanted.

## What Was Added Instead

### Colour constants
Defined locally in `UGLI_2.pp` (not in the include):
```pascal
const
  Black = 0; Blue = 1; Green = 2; Cyan = 3; Red = 4; Magenta = 5; Brown = 6;
  LightGray = 7; DarkGray = 8; LightBlue = 9; LightGreen = 10; LightCyan = 11;
  LightRed = 12; LightMagenta = 13; Yellow = 14; White = 15; Blink = $80;
```

### `AnsiClr` mapping
```pascal
AnsiClr: array[0..7] of Byte = (0, 4, 2, 6, 1, 5, 3, 7);
```
Converts CRT colour index to ANSI SGR digit. Applied in `BufFlush`:
- Dark foreground (0–7): `30 + AnsiClr[Fg]`
- Bright foreground (8–15): `90 + AnsiClr[Fg - 8]`  ← correct high-intensity codes
- Background: `40 + AnsiClr[Bg and 7]`

### Terminal I/O replacements

| CRT call | Replacement |
|---|---|
| `TextColor` / `TextBackground` | `BufPutCell` (colours stored; emitted lazily in `BufFlush`) |
| `GotoXY(x, y)` | `ESC[y;xH` inside `BufFlush` (only for dirty cells) |
| `ClrScr` | `BufFill(Black, Black, ' ')` + `BufFlush`, or `ESC[2J ESC[H` directly |
| `ClrEol` | Not used — buffer approach makes it unnecessary |
| `KeyPressed` | `HasTTYByte` (uses `fpIoctl(FIONREAD)`) |
| `ReadKey` | `GetKey` (VT100 parser on `TTYFd`) |
| `Delay(ms)` | `Sleep(ms)` (from `SysUtils`) |

### `uses` clause change
Before: `CThreads, CRT, DOS, BaseUnix, SysUtils, gettext, UOSSound`  
After: `CThreads, DOS, BaseUnix, SysUtils, termio, gettext, UOSSound`

## VGA Palette

To ensure colours match the original DOS VGA palette (not the terminal's theme colours), `poe run-original` launches kitty with `-c original/ANSI-87.conf`, which loads a 16-colour VGA palette theme. `ANSI-87.conf` is fetched from `kovidgoyal/kitty-themes` by `poe build-original` and is not committed to the repo (`.gitignore`).

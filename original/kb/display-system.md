# UGLI 2 — Display System Reference

## Screen Buffer

`Screen[1..80, 1..25]` of `TScreenCell` (`Ch: String[4]; Fg, Bg: Byte`). Covers the full 80×25 terminal: 20 game rows + 5 key-help rows. Managed by `BufPutCell` / `BufFlush` / `BufFill`.

**Idempotency:** `BufPutCell` compares the new cell against the existing one. If all three fields match, no dirty flag is set. Redundant redraws after the first frame cost nothing.

**`BufFlush` sequence:**
1. Emit `ESC[?7l` (disable line wrap)
2. For each dirty cell (row-major): position cursor with `ESC[row;colH`, emit SGR only if colour changed from previous cell (lazy — avoids redundant SGR sequences), write character, clear dirty flag
3. Emit `ESC[?7h` (re-enable line wrap)

**`BufFlushEnabled = false`:** `BufFlush` clears all dirty flags but writes nothing to TTY. Used by the test suite.

## ANSI Colour Encoding

**Mapping array:**
```
AnsiClr[0..7] = (0, 4, 2, 6, 1, 5, 3, 7)
```
Maps CRT colour index → ANSI SGR digit. Crt order: Black Blue Green Cyan Red Magenta Brown LightGray → ANSI: 0 4 2 6 1 5 3 7.

**Foreground SGR:**
- Colours 0–7 (dark): `30 + AnsiClr[Fg]`
- Colours 8–15 (bright): `90 + AnsiClr[Fg - 8]`

**Background SGR:** always `40 + AnsiClr[Bg and 7]` — no bright backgrounds.

**Blink:** `BufFlush` does NOT emit SGR 5 — the `Blink = $80` bit is only supported in the `Intro` procedure's direct-TTY output via the local `SetFg` helper. Game rendering never produces blinking characters.

**SGR format emitted by BufFlush:** `ESC[0;FG;BGm` (resets to default then sets both fg and bg in one sequence).

## BufDesaturate

Called by `Dialog` before drawing any modal box. Effect on each cell:
- If `Fg ≠ White`: set `Fg = LightGray` (7)
- If `Bg ≠ Black`: set `Bg = LightGray` (7) — this makes non-black backgrounds visible as gray
- All `Dirty` flags set to true

Result: background appears grayed out. White-on-Black cells remain white-on-black.

## GetKey — VT100 Parser

Reads one byte from `TTYFd` via `fpRead`. If it is not `ESC` (27), returns it directly. On `ESC`, uses `fpIoctl(FIONREAD = $541B)` to check for buffered bytes without consuming them. If no bytes follow, returns `KeyEscape` (27). Otherwise reads and dispatches:

| Sequence | Return code | Meaning |
|---|---|---|
| `ESC [ A` | 72 `KeyUp` | |
| `ESC [ B` | 80 `KeyDown` | |
| `ESC [ C` | 77 `KeyRight` | |
| `ESC [ D` | 75 `KeyLeft` | |
| `ESC [ H` | 71 `KeyFaster` | Home (xterm CSI) |
| `ESC [ F` | 79 `KeySlower` | End (xterm CSI) |
| `ESC [ [ A` | 59 `KeyF1` | Linux console |
| `ESC [ [ B` | 60 `KeyF2` | Linux console |
| `ESC [ [ C` | 61 `KeyF3` | Linux console |
| `ESC [ [ D` | 62 `KeyF4` | Linux console |
| `ESC [ [ E` | 63 `KeyF5` | Linux console |
| `ESC [ 1 ~` | 71 `KeyFaster` | Home (vte/xterm) |
| `ESC [ 4 ~` | 79 `KeySlower` | End (vte/xterm) |
| `ESC [ 11 ~` | 59 `KeyF1` | xterm |
| `ESC [ 12 ~` | 60 `KeyF2` | xterm |
| `ESC [ 13 ~` | 61 `KeyF3` | xterm |
| `ESC [ 14 ~` | 62 `KeyF4` | xterm |
| `ESC [ 15 ~` | 63 `KeyF5` | xterm |
| `ESC O P` | 59 `KeyF1` | VT100/SS3 |
| `ESC O Q` | 60 `KeyF2` | VT100/SS3 |
| `ESC O R` | 61 `KeyF3` | VT100/SS3 |
| `ESC O S` | 62 `KeyF4` | VT100/SS3 |
| `ESC O H` | 71 `KeyFaster` | SS3 Home |
| `ESC O F` | 79 `KeySlower` | SS3 End |
| Unknown `ESC [ N ~` | 0 | |

Numeric sequences accumulate digits until `~` or no bytes remain.

## TTY Setup

Raw mode is set in the `begin` block of `UGLI_2.pp`:
- `fpOpen('/dev/tty', O_RDWR)` → `TTYFd`
- `tcgetattr` → saved as `SavedTio`
- Modify: clear `ICANON | ECHO | ISIG`; `VMIN=1`, `VTIME=0`; save as `RawTio`
- `tcsetattr(TTYFd, TCSANOW, RawTio)` to activate

Text file `TTY` is assigned to `/dev/tty` via `Assign`/`ReWrite` for `Write`/`WriteLn` output (separate from `TTYFd`).

`HighScoreEntry` temporarily switches back to cooked mode (`tcsetattr(SavedTio)`) for `ReadLn`, then restores raw mode before returning.

CleanUp restores saved terminal attributes and closes `TTYFd`.

## Intro Procedure

Writes directly to a local `ITTY` file handle (separate `Assign('/dev/tty')`), not via the buffer.

1. Constrain scroll region to rows 1–25: `ESC[1;25r`
2. Flash 8 background colours (indices 0–7), each with a `Ton(offset_Hz, 20 ms)` beep and 20 ms sleep
3. Sleep 100 ms
4. Slow curtain: 25 rows of a `|...|` pattern, Black on Black, 200 ms per row
5. "* DANISOFT * PRESENTS *" on row 25, Black on LightGray
6. UGLI block-letter logo, blink Red on LightGray, 200 ms per line
7. Welcome/version/copyright text, blink Black on LightGray
8. "PRESS ANY KEY" in Red (no blink); wait for keypress
9. Clear screen; ascending tone sweep (MIDI 40–50, 150 Hz each via `Ton`)
10. Reset scroll region: `ESC[r`

The blink flag (`Fg or Blink`) triggers `SetFg` to emit SGR 5 before the colour code. Reset clears blink via `ESC[0;...m`.

# BufFlush: drop consec-skip (cursor-pos for every dirty cell)

## Status

- [ ] Failing tests committed
- [ ] `BufFlush` in `UGLI_2_Core.inc` updated (consec-skip removed)
- [ ] `poe build-original` passes
- [ ] `poe test-original` passes
- [ ] `poe run-original` renders correctly (manual check — user must confirm)

---

## Root cause

V2b introduced two independent optimisations over the original single-cell
`Write(TTY, …)` approach:

1. **Single write** — all output is buffered in `WBuf` and sent with one
   `fpWrite(RawTTYFd, …)` call, eliminating per-cell kernel round-trips.
2. **Consecutive-column skip** — when the next dirty cell is at `(LastCol+1,
   LastRow)` the cursor-position escape `ESC[r;cH` is omitted, trusting the
   terminal cursor to already be there after the previous character.

Optimisation (2) is incorrect when the terminal renders a character in more
than one column.  Several characters used in the game have East Asian Width =
"Ambiguous" in Unicode:

| Character | Code point | Game use |
|-----------|-----------|----------|
| ☺ | U+263A | player smiley |
| ☻ | U+263B | enemy smiley |
| ☼ | U+263C | item 2 |
| ≡ | U+2261 | item 6 |
| ♦ | U+2666 | item 9 |
| ⌂ | U+2302 | item 10 |

Some terminal emulators (including kitty with default settings) render
Ambiguous-width characters as 2 columns wide.  After writing such a character
at column C, the physical cursor is at C+2, but `LastCol` only advances to
C+1.  The next consecutive dirty cell therefore has its character placed at
C+2 on the terminal (one column to the right of where it belongs), corrupting
the display for the remainder of that row.

The user observed this as HUD/interior content "blanked black" after picking
up an item at level 3.  The item-pickup frame accumulates dirty cells in the
interior (player/enemy movement) and on row 20 (DrawItemName), so the drift
becomes visible at that moment.

Optimisation (1) — the single `fpWrite` — is unaffected by this change and
provides the bulk of the performance improvement.

---

## What changes

### `original/UGLI_2_Core.inc` — `BufFlush`

Remove the consec-skip branch and the `LastCol`/`LastRow` tracking variables.
Emit `ESC[r;cH` unconditionally for every dirty cell:

```pascal
{ OLD — may skip cursor-pos when characters are >1 terminal column wide }
if (Col <> LastCol + 1) or (Row <> LastRow) then
  begin WB(#27'['); WBInt(Row); WB(';'); WBInt(Col); WB('H'); end;
WBCh(Screen[Col, Row].Ch);
LastCol := Col;
LastRow := Row;

{ NEW }
WB(#27'['); WBInt(Row); WB(';'); WBInt(Col); WB('H');
WBCh(Screen[Col, Row].Ch);
```

`LastCol` and `LastRow` are removed from the `var` block entirely.

The colour-skip optimisation (`LastFg`/`LastBg`) is kept unchanged.

### `original/UGLI_2_Test.pp` — `TBufFlushOutputTests`

| Old test | Change |
|---|---|
| `TestBufFlush_SameBytesAsV2b` | Repurposed: verify that adjacent dirty cells both receive an explicit cursor-position escape; renamed `TestBufFlush_ConsecCellsBothGetCursorPos` |
| `TestV2_TwoAdjacentCells_SkipsSecondCursorPos` | Remove the `BufFlush`/`BFOut` side; keep only the `V2` assertion (V2 variant retains consec-skip) |

---

## Done when

- [ ] `poe build-original` exits 0
- [ ] `poe test-original` exits 0, all tests pass (including the new
  `TestBufFlush_ConsecCellsBothGetCursorPos` which is red before the fix)
- [ ] `poe run-original` — user explicitly confirms the rendering artefact
  ("life counter and parts of adjacent line going black after item pickup")
  is gone

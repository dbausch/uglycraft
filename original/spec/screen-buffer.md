# Spec: Off-screen screen buffer

## Status

- [ ] `TScreenCell` type, `TScreenBuffer` type, `Screen` + `Dirty` globals declared
- [ ] `BufPutCell` — writes one character to buffer, marks cell dirty only on change
- [ ] `BufFlush` — emits dirty cells to TTY via raw ANSI; clears damage map
- [ ] `Draw` body rewritten to call `BufPutCell` per character; TTY writes removed
- [ ] `BufFill` — clears buffer to a given character/colour pair; marks all dirty
- [ ] `Redraw`: `BufFill` replaces `ClrScr`; `BufFlush` added at end
- [ ] Full-screen overlays (`ShowHelp`, `ShowStory`, `ShowItemDescriptions`, `HighScoreEntry`): `ClrScr` → `BufFill`; `BufFlush` before `WaitKey`
- [ ] `BufDesaturate` — desaturates all cells in-place (Fg → LightGray, Bg → Black); marks all dirty
- [ ] `Dialog`: `BufDesaturate` before box draw; single `BufFlush` renders dimmed background + box
- [ ] Main game loop: `BufFlush` called once per tick

---

## Motivation

Three problems with the current direct-write approach:

1. **`Redraw` flicker**: `Redraw` calls `ClrScr` (blank frame) then redraws 80×25 cells one by
   one. The clear is visible — particularly on level entry, after overlay screens, and when the
   player is caught.

2. **No dimming for dialogs**: `Dialog` currently draws its box over the live game content
   with no visual separation. A dimmed background would make it clear the game is suspended
   and where to look.

3. **No testability**: every draw call goes directly to the terminal; there is no way to
   inspect screen state in a test without parsing terminal output.

---

## Terminal dimensions

The game uses an 80×25 terminal (1-indexed). Add two constants:

```pascal
ScreenW = FieldW;  { = 80 }
ScreenH = 25;
```

The existing `FieldW = 80` / `FieldH = 20` remain; `ScreenH = 25` names the extra 5 rows
occupied by the key-help bar.

---

## Data structures

```pascal
type
  TScreenCell = record
    Ch: String[4];  { one UTF-8 character (1–3 bytes); empty = no character written yet }
    Fg: Byte;       { FPC CRT foreground colour constant (0–15) }
    Bg: Byte;       { FPC CRT background colour constant (0–7) }
  end;
  TScreenBuffer = array[1..ScreenW, 1..ScreenH] of TScreenCell;

var
  Screen : TScreenBuffer;
  Dirty  : array[1..ScreenW, 1..ScreenH] of Boolean;
```

`TScreenBuffer` is a named type (not just an array alias) so a local variable of this type
can hold a saved copy of the screen — used by `BufDesaturate` / test harnesses.

---

## Procedures and functions

### `BufPutCell(Col, Row: Integer; Fg, Bg: Byte; const Ch: String[4])`

Writes one character to the buffer. Marks `Dirty[Col, Row] := true` **only if** the new
`Ch`, `Fg`, or `Bg` differs from the stored values. This change-detection means that
`DrawInner`'s full 78×18 repaint does not dirty cells whose content has not changed —
substantially reducing the amount `BufFlush` needs to emit.

Ignores calls where `Col` or `Row` is out of `[1..ScreenW, 1..ScreenH]`.

### `Draw(Col, Row, Fg, Bg: Integer; S: String)` — body replaced

The existing public signature is unchanged. The body is rewritten to:

1. Iterate `S` as UTF-8 bytes (same 1/2/3-byte detection as today).
2. For each character, call `BufPutCell(C, Row, Fg, Bg, Ch)`.
3. Increment `C`.

All direct TTY writes (`Write(TTY, ...)`, `Flush(TTY)`, `TextColor`, `TextBackground`,
autowrap escapes, GotoXY calls) are removed from `Draw`. They move into `BufFlush`.

`DrawHLine` and `DrawParagraph` are unchanged — they already call `Draw`.

### `BufFill(Fg, Bg: Integer; Ch: String[4])`

Fills every cell of `Screen` with the given character and colours, marks every cell dirty.
Used in place of `ClrScr`. Typical call: `BufFill(FieldBg, FieldBg, ' ')`.

### `BufFlush`

The sole routine that writes to the terminal. Iterates `Dirty` left-to-right,
top-to-bottom. For each dirty cell:

1. Emit `ESC[Row;ColH` (cursor position, direct to TTY).
2. Emit SGR: `ESC[0;FgCode;BgCodem` where `FgCode = if Fg < 8 then 30+Fg else 90+(Fg−8)`
   and `BgCode = 40+Bg`.
3. Emit `Screen[Col,Row].Ch`.
4. Set `Dirty[Col,Row] := false`.

Wrap-around protection is kept: disable autowrap (`ESC[?7l`) before the loop, re-enable
(`ESC[?7h`) after. All output goes to `TTY` so there is no double-buffering with CRT.

After the loop, sync the FPC CRT tracker: `GotoXY(1,1)`.

Consecutive dirty cells in the same row with the same Fg/Bg may be batched under one
positioning + SGR sequence to reduce terminal I/O. This is an optimisation; correctness
does not require it.

**Testing hook**: a module-level `BufFlushEnabled: Boolean = true` variable. When `false`,
`BufFlush` skips all TTY writes but still clears `Dirty`. Tests can set this flag, call
drawing procedures, and inspect `Screen` directly.

### `BufDesaturate`

Sets `Fg := LightGray` (7) and `Bg := Black` (0) for every cell in `Screen`. Marks all
cells dirty. Does not erase content — the desaturated characters remain visible as a dim
background through the dialog box.

### `BufCopy(out Dst: TScreenBuffer)`

Copies `Screen` to `Dst`. Used by test harnesses to snapshot display state.

---

## Integration points

### `Redraw`

```pascal
procedure Redraw;
begin
  BufFill(FieldBg, FieldBg, ' ');
  DrawBorder;
  DrawKeys;
  DrawInner;
  BufFlush;
end;
```

`ClrScr` and the stray `TextBackground(FieldBg)` call before it are removed. The buffer
fill + single flush replaces the clear-then-draw-cell-by-cell pattern that caused flicker.

### `ShowHelp`, `ShowStory`

```pascal
{ before }
ClrScr;
Draw(…); …

{ after }
BufFill(FieldBg, FieldBg, ' ');
Draw(…); …
BufFlush;
WaitKey;
{ Redraw call at end is unchanged — it already does BufFill + BufFlush }
```

`ClrScr` replaced by `BufFill`. `BufFlush` inserted immediately before `WaitKey` so the
completed overlay is rendered atomically.

### `ShowItemDescriptions`

This screen uses `ItemDescBg = LightGray` as background, not `FieldBg`. On large terminal
windows the area outside the 80×25 game grid is visible; `BufFill` only covers the 80×25
buffer and cannot paint outside it.

`ShowItemDescriptions` therefore calls `FillScreen(ItemDescBg)` — a dedicated procedure
that emits the ANSI background SGR and `ESC[2J` directly to TTY, filling the entire
terminal window — before any `Draw` calls. `FillScreen` also syncs the FPC CRT colour
tracker (`TextBackground` + `GotoXY`).

After `WaitKey`, `Init` calls `FillScreen(FieldBg)` to transition the terminal background
back to black before `Redraw` takes over.

With the buffer: `FillScreen` calls remain as-is (they are not replaced by `BufFill`).
Add `BufFill(ItemDescBg, ItemDescBg, ' ')` after `FillScreen(ItemDescBg)` to reset the
buffer state, then `BufFlush` before `WaitKey`.

### `Dialog`

```pascal
function Dialog(Title, Prompt: String): Integer;
begin
  BufDesaturate;
  { … compute geometry, call Draw/DrawHLine for box … }
  BufFlush;           { dimmed background + dialog box in one update }
  Dialog := WaitKey;
  DrawInner;
  BufFlush;           { restore interior }
end;
```

The net result: the transition from live game → dimmed-game-with-dialog is a single
terminal update with no intermediate blank frame.

### `HighScoreEntry`

Contains `ClrScr`, direct `GotoXY`/`Write`/`ReadLn` calls, and a final `ClrScr` before
file display. These use FPC CRT I/O rather than `Draw`. This procedure is excluded from
this change: it operates in a distinct "text input" mode outside the game render loop.
`ClrScr` inside `HighScoreEntry` is acceptable because the game does not return to play
after it.

### `CleanUp` (program exit)

```pascal
Write(TTY, #27'[0m'); Flush(TTY);  { reset attributes first }
ClrScr;                              { clear with terminal default colours }
MyCursorOn;
Close(TTY);
```

Attributes are reset before `ClrScr` so the clear fills with the terminal's default
background rather than whatever colour was last active. `ClrScr` here is intentional and
is not replaced by `BufFill` or `BufFlush`.

### `Intro`

The animated intro writes directly to `TTY` with its own ANSI sequences and does not use
`Draw`. It runs before `Init` and before the buffer is meaningful. Excluded from this
change.

### Main game loop (tick-level updates)

The game loop currently calls `Draw` for each incremental update (player move, enemy move,
block place, score change). With the buffer, those `Draw` calls write to the buffer; the
cell is flushed to the terminal only when `BufFlush` is called.

Add a single `BufFlush` call at the end of each game tick (after `MovePlayer`,
`EnemyMove`, pickup checks, and any HUD counter draws). This bundles all per-tick updates
into one terminal write, eliminating the visible sequence of individual cell updates.

The call site is just after `DrawItem` in the main loop's `Delay`/`HandleInput`/
`EnemyMove` sequence — the exact position depends on reading the loop body during
implementation.

---

## Commit order

1. **This spec** — `original/spec/screen-buffer.md`
2. **Types + globals + `BufPutCell` + `BufFill` + `BufFlush`**: add data structures and
   primitive buffer operations; `BufFlushEnabled` flag. No call-site changes yet; game
   still draws directly via the old `Draw`.
3. **`Draw` body rewrite**: `Draw` calls `BufPutCell`; TTY writes removed from `Draw`. Add
   `BufFlush` at the end of `Redraw`, `ShowHelp`, `ShowStory`, `ShowItemDescriptions`.
   Game functional; flicker reduced.
4. **`Dialog` dimming**: add `BufDesaturate` + `BufCopy`; wire into `Dialog`. Confirm
   dimmed-background rendering.
5. **Main loop flush point**: single `BufFlush` per tick replaces per-Draw TTY writes in
   the game loop.

---

## Done when

- [ ] `Redraw` produces no visible blank frame between the clear and the finished scene
  (confirmed by watching level entry and screen restoration after F1/F2). — _commit 3_
- [ ] `Dialog` shows a dim desaturated game behind the box, not the full-colour live game
  — _commit 4_
- [ ] `BufFlush` with `BufFlushEnabled = false` leaves `Screen` populated and `Dirty` clear
  without writing to the terminal — verified in a test run. — _commit 2_
- [ ] All existing gameplay, HUD updates, overlays, and dialogs continue to work correctly
  in both English and German. — _commits 3–5_

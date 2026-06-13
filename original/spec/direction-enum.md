# Spec: TDirection enum — Direction type + KeyToDir + MovePlayer

## Status

- ✗ `TDirection = (DirRight, DirLeft, DirDown, DirUp)` type declared
- ✗ `Direction: TDirection` declared in `var` block (replaces `Direction: Char`)
- ✗ `KeyToDir(Code: Integer): TDirection` function added before `HandleInput`
- ✗ `MovePlayer` procedure extracted from `HandleInput`, added before `HandleInput`
- ✗ `InitLevelN` (1–9): `Key := Chr(KeyXxx)` replaced by `Direction := DirXxx`
- ✗ `InitLevel`: `Direction := Key` line removed
- ✗ `HandleInput` arrow-key branch: `Direction := Key` → `Direction := KeyToDir(KeyCode)`
- ✗ `LevelTransition` direction capture: `Direction := Chr(KeyCode)` → `Direction := KeyToDir(KeyCode)`

---

## Motivation

`Direction: Char` stores direction as a raw keyboard character (`Chr(KeyRight)` etc.),
coupling game-logic comparisons to scan codes. Every comparison requires `Ord(Direction)`
to decode it back to an integer. An enum makes the type self-documenting and removes the
`Ord()`/`Chr()` noise at all call sites.

---

## Type definition

```pascal
type
  TDirection = (DirRight, DirLeft, DirDown, DirUp);
```

Add a `type` section between the `const` section and the `var` section.

Declare `Direction: TDirection` in the `var` block in place of the current `Direction: Char`.
`Key: Char` stays as the keyboard temp variable in `HandleInput` and `LevelTransition`.

---

## `KeyToDir` function (add before `HandleInput`)

```pascal
function KeyToDir(Code: Integer): TDirection;
begin
  case Code of
    KeyRight: KeyToDir := DirRight;
    KeyLeft:  KeyToDir := DirLeft;
    KeyUp:    KeyToDir := DirUp;
    KeyDown:  KeyToDir := DirDown;
  end;
end;
```

Only called when `Code` is a known arrow-key constant — no default branch needed.

---

## `MovePlayer` procedure (add before `KeyToDir`)

The current `HandleInput` ends with a `case Ord(Direction) of` dispatch (lines 995–1000).
Extract it into a dedicated procedure:

```pascal
procedure MovePlayer;
begin
  case Direction of
    DirRight: MoveRight(X, Y);
    DirLeft:  MoveLeft(X, Y);
    DirUp:    MoveUp(X, Y);
    DirDown:  MoveDown(X, Y);
  end;
end;
```

`HandleInput` removes the `case Ord(Direction) of` block and calls `MovePlayer` in its place.

---

## Affected sites

### `InitLevelN` (all 9 procedures)

Replace the initial `Key := Chr(KeyXxx)` line with a direct `Direction` assignment.
The `Direction := Key` line in `InitLevel` (which was the indirection) is then removed.

| Procedure | Before | After |
|---|---|---|
| `InitLevel1` | `Key := Chr(KeyRight)` | `Direction := DirRight` |
| `InitLevel2` | `Key := Chr(KeyRight)` | `Direction := DirRight` |
| `InitLevel3` | `Key := Chr(KeyUp)` | `Direction := DirUp` |
| `InitLevel4` | `Key := Chr(KeyRight)` | `Direction := DirRight` |
| `InitLevel5` | `Key := Chr(KeyUp)` | `Direction := DirUp` |
| `InitLevel6` | `Key := Chr(KeyDown)` | `Direction := DirDown` |
| `InitLevel7` | `Key := Chr(KeyRight)` | `Direction := DirRight` |
| `InitLevel8` | `Key := Chr(KeyDown)` | `Direction := DirDown` |
| `InitLevel9` | `Key := Chr(KeyUp)` | `Direction := DirUp` |

### `InitLevel` dispatcher

```pascal
{ BEFORE }
procedure InitLevel(L: Integer);
begin
  case L of ... end;
  Direction := Key;      { ← remove this line }
end;
```

### `HandleInput` arrow-key branch

```pascal
{ BEFORE }
KeyRight, KeyLeft, KeyUp, KeyDown: Direction := Key;

{ AFTER }
KeyRight, KeyLeft, KeyUp, KeyDown: Direction := KeyToDir(KeyCode);
```

### `LevelTransition` direction capture

After the dialog refactor (Spec 1), `LevelTransition` has:

```pascal
if KeyCode in [KeyRight, KeyLeft, KeyUp, KeyDown] then
  Direction := Chr(KeyCode);
```

After this spec:
```pascal
if KeyCode in [KeyRight, KeyLeft, KeyUp, KeyDown] then
  Direction := KeyToDir(KeyCode);
```

---

## Files changed

`original/UGLI_2.pp` only.

---

## Done when

- ✗ `poe build-original` compiles with no errors or warnings
- ✗ `poe run-original`:
  - Direction keys work correctly (player moves in the pressed direction on all 9 levels)
  - Each level starts with the correct initial direction (check levels 1, 3, 5, 6, 8, 9 which differ)
  - Pressing a direction key during the level-transition splash sets that direction correctly
  - No regressions in movement, block placement, or enemy behaviour

# UGLI 2 — Game Mechanics Reference

## Scoring

**Item pickup:** `Score += ItemNo * 100`. Item 1 = 100 pts, item 9 = 900 pts. `ItemNo` resets to 1 on death, so catching resets the per-pickup multiplier too.

**Death penalty:** `Score -= ItemNo * 1000`, then clamped to 0. At ItemNo 9 this is −9000 pts — more than 10 full rounds of that item. The quadratic drag is intentional.

**Block placement:** −20 pts per block. `Laying` auto-disables if `Score < 20` or `BlocksRemaining = 0`.

**Life purchase (F3):** −5000 pts, +1 life. Succeeds at exactly 5000 (leaves player at 0).

**Final score:** `Score * Lives` (written to `UGLI.HSC`).

## Lives

- Start: 10
- Gain: +1 on level completion (`LevelComplete`)
- Gain: +1 via F3 during play (costs 5000 pts)
- Loss: −1 when player and enemy share the same tile
- Game over at `Lives = 0`

## Speed and Timing

**`MoveDelay`** (default 100 ms) is passed to `Sleep` at the top of every game loop iteration. There is no separate clock — player input, enemy movement, and rendering all live in the same loop body.

**Enemy tick:** `EnemyTick` is incremented each iteration and the enemy only moves when `EnemyTick mod 2 = 0`. Effective enemy speed is always exactly half the player speed, regardless of `MoveDelay`.

**Home (KeyFaster = 71):** `MoveDelay -= 1` down to 0. At 0 the game runs at CPU speed with no sleep.

**End (KeySlower = 79):** `MoveDelay += 1`. No upper cap.

## Enemy AI

`EnemyMove` is purely greedy — no pathfinding:

1. Compute `DX = X − EX`, `DY = Y − EY` (delta from enemy toward player).
2. If `Abs(DX) > Abs(DY)`: try horizontal first, fall back to vertical.
3. Otherwise: try vertical first, fall back to horizontal.
4. Each attempt either moves and exits, or is blocked and continues. If both axes are blocked the enemy does not move that tick.

**Stuck bug:** a single wall can block the enemy permanently — it cannot navigate around corners. When `|DX| == |DY|`, vertical is preferred.

## Item / Treasure System

`ItemNo` runs 1–9 per level. Pickup increments it; when it reaches 10 the level is complete.

**Crown:** only appears on the 9th pickup of level 9:
```pascal
Idx := ItemNo;
if (ItemNo = 9) and (Level = 9) then Idx := 10;
```
There is no level 10 in the Pascal game; `WinScreen` fires when completing level 9.

**`RandomPos`:** picks `ItemX ∈ [2..78+]`, `ItemY ∈ [2..18+]` (formula: `Round(Random * 77 + 2)` etc.), repeating until a non-blocked tile is found. The range includes col 79 and row 19 (inner border edge), but border cells are blocked so the repeat loop rejects them.

**`ItemX := 0`** is set on pickup and at `NewGame` (but NOT at `StartLevel`). `DrawItem` skips drawing when `ItemX = 0`.

## Block Placement System

- `BlocksRemaining` starts at 2000, is global, and is never reset between levels.
- Space toggles `Laying`. While `Laying = true`, `PlaceBlock` fires every loop iteration, drawing a continuous trail of `█`.
- `BlockX/BlockY` tracks only the **most recently placed block**. The Move* procedures redraw it as a wall every tick to prevent erasure when the player steps off it. Initialized to (1,1) at `NewGame`/`PrepareLevel` — a harmless write to the border.
- `RemoveBlocks` (F5): clears all interior `Blocked[2..79, 2..19]`, then calls `InitLevel` to restore level walls. Player position, direction, and enemy are untouched. No refund of score or budget.

## Pause System

- `PausesRemaining` starts at 20, global, never reset between levels.
- P key: if `PausesRemaining > 0`, decrements and calls `Sleep(5000)`. Completely blocks the game loop for 5 seconds — no input, no animation.

## Level Progression

**On pickup when `ItemNo = 10`:** `Lives += 1; ItemNo := 1; BlockX := 1; BlockY := 1; PrepareLevel; LevelTransition`. Score, `BlocksRemaining`, `PausesRemaining`, and `MoveDelay` all carry over.

**On caught:** `Score -= ItemNo * 1000 (min 0); ItemNo := 1; Lives -= 1; PrepareLevel`. Level does not advance. `PrepareLevel` resets all interior `Blocked` (player-placed blocks disappear) and repositions player at `StartX/StartY`.

## High Score File (`UGLI.HSC`)

Format: one line per entry, `FirstName LastName    score` (4 spaces before score). No entry limit — the file is appended to and never trimmed or sorted. After entry, the raw file content is dumped to the terminal. File is written relative to the current working directory of the binary.

## HandleInput Notes

- `KeySlower = 79 = Ord('O')` and `KeyFaster = 71 = Ord('G')` — these are also ASCII printable characters. The VT100 `GetKey` parser normally produces these scan codes only from terminal escape sequences, so there is no conflict in practice.
- `Draw(X, Y, PlayerFg, FieldBg, '☺')` is called unconditionally at the end of `HandleInput` every tick. It's redundant when the player moved (Move* already redrew the player), but necessary when `Laying = true` since `PlaceBlock` may have drawn a block on top of the player character.

# Codebase Findings — Bugs, Quirks, and Differences

## Pascal vs Python Differences

| Feature | Pascal (UGLI 2) | Python (UGLYCRAFT) |
|---|---|---|
| Lives at start | 10 | 9 |
| Death penalty | `ItemNo × 1000` pts (variable, max −9000) | Flat 500 pts |
| `item_no` on death | Reset to 1 | NOT reset; sequence continues |
| Block placement | Space toggles continuous mode; costs 20 pts/block; 2000 budget | Space places one block; costs 1 placement credit earned by breaking |
| Speed | Single `MoveDelay` loop variable; Home/End adjust in-game | Per-level `move_ms`/`enemy_ms` from 1.07^(10−level) formula |
| Enemy-to-player speed ratio | Always exactly 2:1 | Roughly 2:1 at level 10; varies |
| Enemy AI when `|dx| == |dy|` | Prefers vertical (strict `>`) | Prefers horizontal (`>=`) |
| Number of levels | 9 | 10 (level 10 adds boss) |
| Crown | Level 9, 9th item | Level 10, 9th item; fixed spawn position |
| High score format | Appended flat text; no limit; no sort | Top-10 JSON-like; sorted; rewritten on save |
| Final score | `Score * Lives` | `score * max(1, lives)` |
| Pause | P, 5 s sleep, 20 uses | P, toggle pause state, unlimited |
| Shield | None | Enter, 250 pts, 10 s |
| Difficulty | Single mode | Easy (greedy) / Hard (BFS) |
| Buy a life | F3, 5000 pts | None |

## Known Bugs and Quirks

### Pascal

**`BlockX/BlockY` initialised to (1,1):** At game start and after each `PrepareLevel`, the "last placed block" tracker is set to (1,1) — the top-left border corner. The Move* procedures unconditionally redraw that cell as a wall every tick until a real block is placed. Harmless because (1,1) is already a wall, but technically redundant.

**`RandomPos` formula includes inner border cells:** `Round(Random * 77 + 2)` can produce ItemX = 79 (right inner edge). Border cells are blocked, so the repeat loop rejects them, but the formula's range is misleading.

**Level 9 player start in a 1-cell corridor:** Player starts at (40, 10) — between the two divider walls at cols 39 and 41. Col 40, row 10 is open (the divider walls run rows 5–15, and the horizontal arms don't close row 10). Moving immediately left or right bumps a wall.

**`WinScreen` plays sound after showing dialog:** `Dialog(sYouWon)` → `SoundWon` → `HighScoreEntry`. The win sound plays during the name-entry screen, not before it.

**`HandleInput` redraws player unconditionally:** The final `Draw(X, Y, PlayerFg, FieldBg, '☺')` fires every tick regardless of movement. Necessary when `Laying = true` (block placement overwrites the player character), redundant otherwise.

### Python

**FIXED (spec 0054) — Level generation depended on PYTHONHASHSEED (BL-40):**
the same game seed produced different Act 2 level content in different
Python processes — `get_level(13)` under `set_game_seed(777)` yielded 4
distinct canonical hashes for `PYTHONHASHSEED=0..3`, making the golden
`act2_L13_walk` flip per process. Cause: `PYTHONHASHSEED` salts **str**
hashing only (int/tuple hashes are process-stable), so iteration over
str-sets of node names fed `rng.choice` pools in per-process order — five
sites in `LevelGraphBuilder` (`_reachable`, `_current_grid_rooms`). Fixed by
making `_reachable` a dict-as-ordered-set and `_current_grid_rooms` a list;
dead `_assign_items` (same pattern, no callers) deleted. Draw sequence
unchanged, only pool ordering. Guard: `tests/test_generation_determinism.py`
runs the canonical-hash probe `tests/_gen_hash.py` in subprocesses under
different hash seeds. Rule of thumb for future generator code: **never let a
set of strings reach an rng pool or placement order — use dict-as-ordered-set
or a list; sets of int tuples are safe.**

**`_respawn_enemy` may leave enemy on player tile:** If BFS finds no tile ≥ 8 tiles away AND no tile ≥ 4 tiles away, the enemy is not moved. On the next update tick, the player-on-enemy check will immediately trigger another catch (instant repeated death).

**Level 9 player start near the divider:** Player starts at (15, 8). The double divider walls are at cols 14 and 15, but only for rows 1–5 and 10–14. Row 8 is open at col 15, so the start is valid — but the player is one step from the divider, mirroring the Pascal original's tight start position.

**`_full_reset` and `_start_level` both set `item_no = 0`:** `_full_reset` calls `_start_level(1)`, so the second assignment is redundant. No functional impact.

**FIXED (spec 0048) — Water is invisible to the push-puzzle solver but solid at runtime (BL-13/BL-14):**
`puzzle_passable` (block placement) and `validate_push_puzzles` both omit
`water_tiles`, treating water as walkable floor, while the runtime
made unbridged water solid (pre-0047 `_build_walls_multiroom`; today
`World.blocked` over the cell model — same semantics). A block placed beside
an inter-room water stream can therefore be "solvable" on paper yet wall-flanked
in play. This — not any lossy graph transform — is why the runtime
`_verify_blocks` net still catches unplayable levels. Empirically every stuck
block found was water-caused (2/175 block-bearing multi-grid levels). Every
*other* thing the net can fire on (block/closed gate/locked door in the sole push
axis) is a false positive the solver already accounted for. → see
`kb/architecture.md` "Playability validation: the model boundary (BL-13)" and
BL-04 for the related water-crossing looseness.

**STORY state is unreachable:** The `STORY` game state has a renderer and event handler but no transition into it. No code sets `self.state = STORY` except inside the STORY handler itself. The only way to see it is to manually set the state in code.

**Music deduplication on same level:** `start_music(key)` returns early if `_current_key == key`. Dying and restarting on the same level does not restart the music — it continues mid-track. This is intentional for smooth UX, not a bug.

**`item_no` NOT reset on death:** Unlike the Pascal version, UGLYCRAFT continues the item sequence after a death. The player resumes collecting from whatever `item_no` they were on. The penalty is purely score-based (−500 pts).

**Bridge placement silently consumes extras:** When the player has crafted multiple bridges and tries to place them, only the first placement succeeds. Subsequent attempts consume the bridge item from inventory without placing anything in the world. Root cause unknown — likely in the bridge placement / water-tile check logic. **RESOLVED as
unreproducible (BL-39, 2026-07-12):** on current code every refusal path in
`_try_auto_bridge` returns before `inventory.use_item`; a permanent guard
test (`test_refused_bridge_never_consumes_the_item`) pins the ordering.
Probably died with spec 0029's replacement of the old per-grid bridge cap.

**Stairs sprite drawn at ordinary passages (FIXED, spec 0056 / BL-12):** The staircase sprite used to be blitted unconditionally at every grid-border exit. Since spec 0056 the border-exit loop draws the sprite selected by `border_exit_sprite` (game.py) from the room's `border_barriers` record — locked door / gate mirroring the source barrier's live state, **nothing** for an open border (the gap in the border wall is the marker). Design rule from that review: **stairs are reserved for floor-to-floor travel; no same-floor entry/exit may ever show the staircase sprite.** → see `spec/0056-grid-entry-tile-type.md`.

**Stairs design notes (for future implementation):**
- A staircase tile is a normal interior floor tile; it is NOT restricted to the 30×16 grid border. It can appear anywhere inside a room or corridor.
- Each staircase goes in one direction only: **up** (to the layer above) or **down** (to the layer below) — never both.
- Connecting layer N to layer N+1 therefore requires two separate stair nodes: one "stairs down" in layer N and one "stairs up" in layer N+1.

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

**Key inventory "looked wrong" — resolved, no standalone bug (spec 0071, BL-27):**
The BL-27 observation that "during play the key inventory sometimes looked wrong"
was investigated and closed as an artifact of a separate, already-fixed defect —
Daniel confirmed the key inventory renders correctly in recent play (2026-07-12).
The key-rendering path is sound: keys are **unique per colour** (`levelgraph.py:441`
builds a shuffled colour pool and `pop()`s one distinct colour per locked door, so
at most one key per colour), a used key (`use_key` → count 0) is filtered out of
the inventory list and never lingers, and each `icon_key_{colour}` matches its
label colour. The only genuine wart was cosmetic — a redundant `×1` count beside
each key — removed by spec 0071 D1 (inventory now shows `[icon] Name`, aligned
with the Tools list). Note the current, intended semantics: **keys are consumed on
door-open** (`world.py:518` `_try_auto_open_door` → `inventory.use_key`), so a
carried key disappears the instant its door is opened (not a bug; not a trophy
system). Spec 0071 also adds a fixed-width HUD key strip → see
`kb/uglycraft-display.md` "HUD Layout".

**Entrance-as-gate gotchas (spec 0066, BL-43):** modelling the level
entrance as a `Barrier('gate', channel=ENTRANCE_CHANNEL)` surfaced three
non-obvious interactions:
- **Gate overlay paints over the door.** `game.py`'s generic gate overlay
  (`for (gc, gr), gate in self.cells.barriers('gate')`) blits a portcullis
  over *every* gate barrier, drawn *after* the entrance sprite — so the
  entrance rendered as an open/closed gate, not a door. Fix: `continue` when
  `gate.channel == ENTRANCE_CHANNEL` (the entrance is drawn by the dedicated
  `level_entrance`/`level_entrance_open` path).
- **`_latch_channels` is a targeted relatch, not wholesale.** It does
  `self._channels = (self._channels - local) | pressed` where `local` is only
  *this room's* plate gate-ids — so a non-plate channel (like the entrance
  channel) survives every tick untouched. (An earlier spec draft wrongly
  claimed it recomputed `_channels` from scratch.) The one place that *does*
  wipe channels wholesale is `_reset_blocks` (death) — hence the explicit
  `self._channels & {ENTRANCE_CHANNEL}` preservation there.
- **Act 1 sequential treasure sprite lingers.** Act 2 loot is removed from
  the cell item layer on pickup, but Act 1's single roaming treasure is only
  a `treasure_pos` — collecting the 9th award used to advance immediately
  (clearing it); now that it opens the entrance instead, `treasure_pos` must
  be set to `None` on the last pickup or the collected coin stays on screen.

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

## Doomed push-blocks & the safe set (spec 0068 / BL-37)

A push-block that is pushed out of its plate's **safe area** lights a 5 s
red-glow fuse, then explodes (−500 pts, `BLOCK_EXPLOSION_PENALTY`) and respawns
at its start (or nearest open tile). Detection is a static membership check:
`(block tile) ∉ Room.safe_tile_set → ignite` in `World._light_doomed_fuses`,
run after every successful push. Blocks are confined to their room floor
(`World._room_floor`), may be pushed onto unsafe tiles (the old dead-square push
guard was removed), and stay movable while burning but can never re-enter the
safe area (once outside the reverse-reachable set, every tile one push away is
also outside it). On death, blocks are **not** reset — `_reset_blocks` was
deleted; dying preserves solved-puzzle progress (the spec 0067 player+enemy
reset stays; gates recompute via the plate latch).

### The safe set is player-reachability-bound — a hard-won invariant

`plate.safe_tiles` = the block positions from which the block can be pushed to
that plate, computed by `cells.safe_block_positions(floor, plate)`. The critical,
non-obvious facts (each cost a wrong attempt):

- **Confine the analysis to the room's OWN walkable floor** — `tile_owner` tiles
  minus walls/gates/doors/entrance. A **wall opening / gate / door is a way out,
  not a push-stand tile**: the player can never stand *in* a doorway to push a
  block off the adjacent wall. Using the grid-wide passable set (including the
  opening) wrongly marks the wall-adjacent row safe.
- **Track the player's zone, not just the stand tile.** A pull is legal only when
  the player can actually **walk** — around the block, within the room floor — to
  the tile it must push from. The block can block the player's *own only path*
  (e.g. a block above a 1-wide opening cuts the room from a corridor below it), so
  a standable tile beyond the block does not help. Plain reverse-reachability, a
  "dead-end stand" (≤1 neighbour) rule, and a 2-core rule all FAILED for this
  reason. The correct computation is a reverse Sokoban over `(block, player
  component)` states, seeded from `(plate, every component of floor−plate)`,
  validated tile-for-tile against a forward solver.
- **Accepted residual:** "solvable for *some* player start" (seeds all zones), so
  a single block that splits the room with the player stranded on the plate-less
  side is still counted safe — a maze-only case, absent in one-puzzle-per-room
  levels.
- The safe area **is** the still-solvable block positions, so the intended
  solution path is always safe; the floor tint marks it. Mazes must stay
  Sokoban-solvable: 1-wide winding corridors collapse the safe area (can't get
  behind the block at a bend); **2–3-wide floor with a few turns keeps most of
  the room safe**.

→ see `spec/0068-exploding-wedged-blocks.md` (Geometry section has computed
diagrams incl. the wall-opening case). Enemies never share a push-puzzle room
(R-P9, `kb/requirements.md`), so an exploded block's respawn need not avoid them.

# Spec 0078 — No block placement on a border passage tile (BL-58)

Backlog: **BL-58 (P2)**. A tester stood on the **passage tile of a grid border**
(a punched exit that joins this grid to a neighbouring one) and pressed SPACE.
A `'placed'` block was created there and drawn with the **border-wall** sprite,
not the block sprite — an incoherent, mirrored-across-the-border display state.

This is the same family as **BL-57 / spec 0077** ("no block on a door or gate
tile"): a tile that carries a special, later-drawn meaning must not accept a
placed block. The backlog flagged the handling approach as *undecided* —
(a) **disallow** building on a border passage tile, or (b) **make the block
render correctly on both mirrored sides**. This spec chooses **(a)**, for the
reasons in *Design decision* below, and implements it as one more refusal
predicate in `_place_block`, reusing the spec-0074 `'action_denied'` feedback —
exactly the shape of spec 0077's D6. → `kb/world-model-review.md` §5 (*store
identity/structure, derive state by query*).

## Status checklist

- [x] **B1** — `_place_block` refuses when the player stands on a **border tile**
  (a passable border tile is always a punched passage/exit or the entrance gate),
  via a new `_is_border_passage_tile(c, r)` predicate that returns
  `is_border(c, r)`. The refusal emits `'action_denied'` and spends no credit —
  no new event or sound. (`0211448`)
- [x] **B2** — No rendering change is made. Because a placed block can no longer
  land on a border tile, the `_render_field` priority that draws `border_wall`
  before `placed_block` (game.py:531–534) can never be reached for a placed
  block, so the reported border-wall-sprite bug is fixed **by prevention**.
  (`0211448`)
- [x] **B3** — All other placement behaviour is unchanged: the credit gate, the
  `blocked(c, r)` gate, the respawn-tile gate (spec 0067), the door/gate gate
  (spec 0077), and successful placement on any interior floor tile. (`0211448`)
- [x] **B4** — Verification: pygame-free `tests/test_world.py` asserts the
  refusal while standing on a border passage tile (emits exactly
  `['action_denied']`, no credit spent, no `'placed'` barrier written) and that
  interior-floor placement still succeeds (guards against an over-broad refusal).
  (`0211448`; full suite 893 passed)
- [x] **B5** — Daniel confirms in-game: standing on a border passage and pressing
  SPACE produces the denial sound and **no** block (nothing drawn as a border
  wall); building on ordinary interior floor still works. (user-accepted
  2026-07-15)

## Background — confirmed facts

Established by reading the code (self-contained; do not re-derive):

### What a "border passage tile" is

`is_border(col, row)` (`world.py:45`) is **purely positional** — it is `True` for
any tile on the outer ring (`col == 0 or col == COLS-1 or row == 0 or row ==
ROWS-1`; grid is 30×16, so the ring is cols 0/29 and rows 0/15). A border tile is
normally a **wall** (blocked). At stitch time the generator **punches one border
tile per shared boundary into a passage** (an `exits` entry), so it becomes
*passable* — this is the only way a border tile is walkable. The level
**entrance** is the one other passable border tile: it is a
`Barrier('gate', channel=ENTRANCE_CHANNEL)` on the ring (spec 0077 background),
already refused by `_is_door_or_gate_tile`.

So: **a border tile the player can stand on is always a punched passage (or the
entrance gate).** A positional `is_border(c, r)` test at the player's tile is
therefore exact — it can only ever match a passage/entrance, never a legitimate
interior placement.

### The passage tile is mirrored across the shared border

An exit is stitched onto **both** adjacent grids at the same offset — e.g. g1's
`exits={'right_8': 'g2'}` (passage tile `(29, 8)`) pairs with g2's
`exits={'left_8': 'g1'}` (passage tile `(0, 8)`), same row 8. The two grids are
**separate room-cell models**. A block placed on g1's passage tile writes only
g1's cells; g2's side is untouched — so the two mirrored halves of the same
doorway would disagree. This is the "mirrored to the opposite side of the grid"
snag the backlog names, and a second reason the interaction is incoherent.

### Why the block is drawn as a border wall (the reported symptom)

`_render_field` (`game.py:526–547`) iterates tiles; for a blocked tile it checks
**`is_border(c, r)` first** and blits `border_wall`, *before* the
`b.kind == 'placed'` branch that would blit `placed_block`:

```python
if self.blocked(c, r):
    b = self.cells.barrier(c, r)
    if is_border(c, r):
        self.surf.blit(sp['border_wall'], (x, y))       # ← wins for a border tile
    elif b is not None and b.kind == 'placed':
        self.surf.blit(sp['placed_block'], (x, y))      # ← never reached on the ring
    ...
```

A placed block makes the tile `blocked`, and on the ring `is_border` wins, so the
block is painted as a border-wall segment. Prevention (B1) makes this branch dead
for placed blocks, so no render change is needed.

### Placement is a refusal chain in `_place_block`

`_place_block` (`world.py:730`) already ANDs a chain of guards and emits
`'action_denied'` (spec 0074) on any failure:

```python
def _place_block(self):
    c, r = self.player.col, self.player.row
    if (self._block_credits > 0 and not self.blocked(c, r)
            and not self._is_respawn_tile(c, r)
            and not self._is_door_or_gate_tile(c, r)):
        self._block_credits -= 1
        self.cells.set_barrier((c, r), Barrier('placed'))
        self._emit('block_placed')
    else:
        self._emit('action_denied')   # no credit / blocked / respawn / door-gate
```

This spec adds one more `and not …` term. The refusal reuses the existing
`'action_denied'` → `'denied'` sound wiring; no new event or sound.

## Design decision — disallow (a), not mirror-and-render (b)

The backlog left the approach open. **(a) is chosen** for three reasons:

1. **Consistency with spec 0077.** BL-57 resolved the analogous "block on a
   door/gate tile" case by *refusing placement* and emitting `'action_denied'`.
   A border passage is another special, later-drawn tile; refusing is the same,
   already-shipped pattern (one predicate + the existing denial feedback).
2. **A border passage is a passage between rooms — re-sealing it is already "not
   a feature."** Spec 0077's *Out of scope* explicitly states: *"Allowing a block
   to re-seal an open gate/door — deliberately not a feature."* A block on a
   border passage would re-seal the passage joining two grids; that is the same
   class of action and is declined for the same reason.
3. **(b) is disproportionate and risky.** Rendering the block correctly on both
   sides would require (i) reworking the `_render_field` priority so `'placed'`
   beats `is_border`, **and** (ii) mirroring the placed block into the
   neighbouring grid's cells so the two doorway halves agree, **and**
   (iii) re-validating reachability — a sealed passage can break the connectivity
   invariants (`kb/requirements.md` R-S1: the corridor floor must reach a tile on
   each border side). That is a large, invariant-touching change to legitimise an
   edge-case interaction that (a) removes cleanly. No puzzle or generator change
   is needed under (a).

**This is the one open decision in this spec.** If Daniel prefers (b) at the
confirmation gate, the spec is rewritten around the render + mirror + reachability
work instead.

## B1 — Refuse placement on a border passage tile

Add a predicate mirroring `_is_door_or_gate_tile` (`world.py:721`), and one guard
term in `_place_block`:

```python
def _is_border_passage_tile(self, c, r):
    """A punched border tile — an open passage/exit to the neighbouring grid.
    A block placed here is drawn with the border-wall sprite (is_border wins in
    _render_field) and would re-seal a room passage — deliberately not a feature
    (spec 0077, mirrored across the shared border for BL-58).  A non-passage
    border tile is a wall and already fails `not blocked`, and the level
    entrance is a gate already refused by `_is_door_or_gate_tile`, so the bare
    positional `is_border` test is exact for a passable player tile."""
    return is_border(c, r)

def _place_block(self):
    c, r = self.player.col, self.player.row
    if (self._block_credits > 0 and not self.blocked(c, r)
            and not self._is_respawn_tile(c, r)
            and not self._is_door_or_gate_tile(c, r)
            and not self._is_border_passage_tile(c, r)):
        self._block_credits -= 1
        self.cells.set_barrier((c, r), Barrier('placed'))
        self._emit('block_placed')
    else:
        self._emit('action_denied')   # no credit / blocked / respawn / door-gate / border
```

`is_border` is already a module-level function in `world.py` (line 45) — no import
change.

## B2 — No rendering change

`_render_field`'s `is_border`-before-`'placed'` order (game.py:531–534) is left
exactly as-is. After B1 a placed barrier can never sit on a border tile, so the
branch that painted the block as `border_wall` is unreachable for placed blocks;
the reported symptom is fixed by prevention, not by re-ordering the renderer.
(Re-ordering would only matter under approach (b).)

## B3 — Preserve existing behaviour

Unchanged: the credit gate, the `blocked(c, r)` gate, the respawn-tile gate
(spec 0067), the door/gate gate (spec 0077), and successful placement on any
interior floor tile. The only new refusal is "player standing on a border tile".

## B4 — Verification

pygame-free unit tests in `tests/test_world.py`, using the existing
`tests/act2_fixtures.py::transition_level` (g1 has `exits={'right_8': 'g2'}` → the
passage tile is `(COLS-1, 8) = (29, 8)`; player starts at `(25, 8)` in g1) and
the `_fixture` / `_restore` helpers the spec-0074/0077 denial tests already use:

1. **Border passage refused** — load `transition_level`; put the player on the
   passage tile (`w.player.col, w.player.row = 29, 8`); grant one block credit;
   `place()` emits exactly `['action_denied']`, spends no credit, and
   `w.cells.barrier(29, 8)` is still `None` (no `'placed'` written).
2. **Interior floor still works** — on a plain interior floor tile with a credit,
   `place()` still emits `['block_placed']` and sets a `'placed'` barrier (guards
   the predicate against a false-positive that would break ordinary building).

Generator determinism (`test_generation_determinism`) and the golden
traces/screenshots stay green: the rng stream is untouched and **no golden run
places a block on a border tile**, so nothing re-records.

## Out of scope

- Approach (b): rendering a placed block correctly on both mirrored sides and
  cross-grid mirroring of the block. Declined above; would be a separate spec.
- Any change to how border passages, exits, or the entrance are *drawn*.
- Allowing a block to re-seal any passage, gate, or door (spec 0077 already
  declines this for gates/doors).

## Done when:

- [x] **B1** — `_place_block` refuses on a border tile via
  `_is_border_passage_tile`, emitting `'action_denied'` and spending no credit.
  (`0211448`)
- [x] **B2** — no rendering change; the border-wall-sprite symptom is unreachable
  for placed blocks. (`0211448`)
- [x] **B3** — every pre-existing placement behaviour (B3 list) is unchanged.
  (`0211448`)
- [x] **B4** — the two `test_world.py` cases pass; generator determinism +
  goldens stay green (no re-record). (`0211448`; full suite 893 passed)
- [x] **B5** — Daniel confirms in-game: denial sound fires, no block appears, and
  interior building still works. (user-accepted 2026-07-15)

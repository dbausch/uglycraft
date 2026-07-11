# Spec 0050 — Behaviour dispatch + signal channels (refactor Stage 4, BL-35)

Stage 4 of the world-model refactor (→ `kb/world-model-review.md` §3
Stage 4, §5 R2): behaviour that today lives in per-kind if-chains and
parallel list scans moves into **dispatch on the cell model**, and gate
state moves from the stored `_gate_open` set to a **signal-channel
table**. Zero behaviour change, proven by byte-identical spec-0044
goldens; the payoff is kb review P3 — adding an element kind stops
costing ~10 touch points.

## Status

- [x] Q1 — Signal channels: plates are emitters, `World.channel(name)` is
      the query, gates receive; the channel table is **latched once per
      tick at exactly the point `_update_pressure_plates` runs today**
      (and re-latched in `_reset_blocks`), so gate-opening timing is
      byte-identical; `_gate_open` is deleted
- [x] Q2 — Bump dispatch: `_register_bump`'s kind-chain becomes barrier
      policy dispatch (door → key-open, breakable → damage/break,
      border/reinforced/gate → inert) + water-terrain → bridge attempt;
      precedence provably identical
- [x] Q3 — Items become a cell layer: treasures/materials/keys move from
      the three per-room list-dicts into `cells` (item layer, indexed by
      position); collection dispatches on item kind **at the two existing
      collection points** (loot before enemy collision, pickups at tick
      end), at most one item per category per tick, exactly as today;
      `RoomState` drops three more fields
- [x] Q4 — Render dispatch: barrier-kind → sprite and item-kind → sprite
      come from tables; blit **category order stays hardcoded and
      identical** (golden screenshots pin the pixels)
- [x] Q5 — All goldens byte-identical; unit tests red-first (channel
      latch, barrier policies, item dispatch)
- [x] Q6 — Docs: kb review Stage 4 done, feature-inventory, BL-35 note

## Motivation

`_register_bump` re-derives what a barrier does from its kind string;
`_collect_loot`/`_collect_materials`/`_collect_keys` are three list
scans per tick over three parallel per-room dicts; `_render_field` has
one hand-written loop per element kind; `_gate_open` is stored state
mutated in two places. Every new interactive element (BL-37's exploding
blocks, the spec-0007 machines: levers, buttons, valves, pistons) pays
all of these costs. After Stage 4: one barrier policy, one item-kind
entry, one sprite-table entry, and — for anything switchable — one
channel, uniformly queried via `world.channel(name)`.

## Design

### Q1 — channels, latched for timing fidelity

The kb review (R2) wants plate pressed-ness *derived* — but deriving it
at query time would change **when** a gate opening becomes visible to
collisions (mid-enemy-loop instead of at the plate pass), which is why
Stage 3 deferred it. The resolution: derive, but **latch**.

```python
# World
self._channels = set()          # high channel names, recomputed wholesale

def channel(self, name):        # receivers ask this — nothing else
    return name in self._channels

def _latch_channels(self):      # THE plate pass (was _update_pressure_plates)
    occupied = {player} | {enemies} 
    self._channels = {gate_id for plates (pc, pr, gate_id) of the room
                      if (pc, pr) in occupied or (pc, pr) in blocks}
```

- `_latch_channels` runs at the **exact position in `update` where
  `_update_pressure_plates` runs today**, and `_reset_blocks` calls it
  after resetting (today it clears `_gate_open` there). Every consumer
  therefore sees exactly the state it saw before — same information,
  same time.
- `cells.blocked(c, r, gate_open)` keeps its signature, now fed
  `self._channels`; the parameter is renamed `channels` (the solver
  keeps passing `∅` = all gates closed, conservative as today).
- `_gate_open` is deleted (facade entry too; the golden-test reads of
  `h.game._gate_open` become `h.game.world._channels` — allowed test
  edit, goldens untouched).
- Future levers/buttons/valves are emitters folded into the same latch;
  traced wiring nets (player-laid wire) stay future work (kb R2).

### Q2 — bump dispatch

`_register_bump` keeps its role and its *sequence* but stops switching
on kind strings:

```
door attempt      → barrier is a door: key match → open (as today)
bridge attempt    → no barrier + WATER terrain → _try_auto_bridge
border            → positional check, unchanged
barrier dispatch  → BARRIER_POLICY[kind]: inert (reinforced/gate/border)
                    or breakable(hits_to_break) → damage / break
```

Policies live on/next to `Barrier` in `cells.py` (pygame-free, plain
data + functions). Equivalence note: today the bridge attempt precedes
the border return, but water never lies on grid-border tiles (WATER
edges are intra-grid partitions — kb), so dispatching barrier-first is
observably identical; the goldens and the water unit tests pin it.

### Q3 — items as a cell layer

`RoomCells` gains an item layer: `items(c, r)` → list of
`Item(kind, payload)` (kind ∈ treasure/material/key; payload = item_no /
material type / colour), built by `build_room_cells` from the room dict,
insertion-ordered. The three per-room dicts (`_room_treasures`,
`_room_materials`, `_room_keys`) and their `RoomState` fields die;
persistence rides on `cells` exactly like barriers already do.

Collection keeps the **two existing call points and their per-category
semantics** (the goldens pin sound order):

- loot pass (before enemy collision): at most one `treasure` at the
  player's tile → score + `collected` event + loot counting → possible
  `advance_level` (sequential-mode Act 1 treasure stays `treasure_pos`,
  untouched — it was never in the room lists).
- pickup pass (tick end): at most one `material`, then at most one
  `key` — dispatch by kind into the inventory, `collected` event each.

`_loot_total` counting at `start_level` reads the room dicts as today.

### Q4 — render dispatch

`game.py` gets kind → sprite-key tables (strings only — pygame stays in
`game.py`): barrier base sprites (already half-table via
`_WALL_SPRITE`), gate/door sprites by kind + orientation, item sprites
by kind + payload. The per-category loops collapse into iteration over
`cells.barriers(kind)` / `cells.items_of_kind(...)` indexes — but the
**category blit order is kept hardcoded and identical** (plates, gates,
blocks, water, flames, doors, opened doors, keys, materials), because
the golden screenshots compare pixels. Facade drops the three dead item
dicts and `_gate_open`.

## Non-goals

- **BL-12 / edge-type plumbing** (stairs sprite vs actual barrier type):
  deliberately NOT here despite the kb review mentioning it — it is a
  *visual behaviour change* requiring screenshot re-records, so it gets
  its own small spec after this behaviour-preserving stage.
- Traced wiring nets, momentary buttons with timers (future machines
  spec); flame jets as ray-cast fields (kb R3); blocks as occupant
  entities and Room objects (Stage 5).
- No new element kinds — this stage only makes them cheap.

## Verification

1. `poe test` green with **zero golden diffs** (traces and screenshots);
   no `UGLYCRAFT_REGOLD`.
2. New unit tests red-first: channel latch equivalence (pressed/released
   plate timing incl. `_reset_blocks`), barrier policy table (each kind's
   bump outcome), item-layer collection (per-category one-per-tick,
   order).
3. Manual gate: user plays — Act 1 sanity plus an Act 2 gated level
   (plate/gate timing feel) and a pickup-heavy level.

## Done when:

- [x] Q1 — channels latched, `_gate_open` deleted (401ac18; **errata
      cad68ba**: the first latch recomputed wholesale and wiped channels
      held high from other grids — cross-grid gated barriers closed on
      grid entry.  Neither goldens nor the 23-test net covered cross-grid
      channel persistence; found during Stage 5 design review, fixed
      red-first: the latch now touches only the local plates' channels,
      exactly the old add/discard scope)
- [x] Q2 — bump via barrier policies, kind-chain gone (401ac18)
- [x] Q3 — items in cells, three room dicts + RoomState fields deleted
      (401ac18)
- [x] Q4 — render tables, category order pinned (401ac18)
- [x] Q5 — suite green, goldens byte-identical, unit tests red→green
      (401ac18 — 23-test net: 18 behaviour locks + 5 API pins; cad68ba
      adds the cross-grid channel lock; 517 passed)
- [x] Q6 — docs + BL-35 updated (cd2309a, dd858af)

User acceptance 2026-07-12: played — "plates and gates feel fine".
The cross-grid errata (cad68ba) was found and fixed after that session;
in a follow-up play session the user then hit the exact scenario — a
push puzzle controlling a gate on another grid — and confirmed it
opened and **stayed open** correctly. Errata verified in play on top of
its red-first regression test.

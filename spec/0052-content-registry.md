# Spec 0052 — Content registry, consolidation only (world model Stage 6, BL-38)

Implements kb/world-model-review.md **§7** minus the new-element half, per
Daniel's direction (2026-07-12): *"do stage 6, but without introducing new
features yet."* Everything that is still its own special category — plates,
flame jets, pushable blocks, and the hand-written parser — joins the cell
model and a registry; **no behaviour changes**, byte-identical spec-0044
goldens, and no new element kinds. The payoff is banked now; the lever (or
any §7 machine) cashes it in a later feature spec.

## Status

- [ ] G1 — Parse registry: `build_room_cells` iterates `CONTENT_PARSERS`
      (one `(dict_key, parser)` entry per content kind — border, walls,
      doors, gates, water, items, plates, flame nozzles); adding a kind
      stops touching the parser body
- [ ] G2 — Generic non-blocking `Fixture(kind, payload)` layer in
      `RoomCells`; **plates** (payload = channel) and **flame nozzles**
      (payload = the jet dict, tiles still precomputed) become fixtures;
      `Room.plates` / `Room.flame_jets` fields die (thin compat
      properties read the cells)
- [ ] G3 — Pushable **blocks become occupants**: `Block(Entity)` in
      `entities.py`, `Room.blocks` holds objects with identity
      (`blocks_initial` stays positions); passability/push/latch/reset/
      render read `(b.col, b.row)` — the identity BL-37's countdown
      will need
- [ ] G4 — Sprite dispatch consolidated: item/fixture kind → sprite-key
      table in `game.py` (strings only; category blit order pinned by
      the golden screenshots)
- [ ] G5 — `World.update`'s pinned system order documented in its
      docstring (timers → input → enemies → collect → collision →
      flames → latch → pickups) — the determinism contract future
      registry entries must respect
- [ ] G6 — Red-first tests (fixture layer API, plate/nozzle parity,
      Block identity, registry completeness); all goldens byte-identical
- [ ] G7 — Docs: §7 status note, feature-inventory, BL-38

## Design

### G1 — one registry, one parser loop

```python
# cells.py
CONTENT_PARSERS = (
    ('walls',           _parse_walls),        # barriers: stone/wooden/reinforced
    ('locked_doors',    _parse_doors),
    ('gates',           _parse_gates),
    ('water_tiles',     _parse_water),        # + water_tile_room payload
    ('treasures',       _parse_items('treasure')),
    ('materials',       _parse_items('material')),
    ('keys',            _parse_items('key')),
    ('pressure_plates', _parse_plates),
    ('flame_jets',      _parse_nozzles),
)
```

`build_room_cells` becomes border handling + this loop. Each parser owns
its record shape (the tuple-arity knowledge that today lives inline).
Blocks are deliberately *not* parsed into cells — they are occupants and
belong to `Room.from_data` (G3), exactly as enemies do.

### G2 — plates and nozzles as fixtures

`RoomCells` gains `_fixtures: pos → [Fixture(kind, payload)]` with
`fixtures_of_kind(kind)` iteration (insertion order = room-data order,
as for items). Both new fixture kinds are **non-blocking**, so
`RoomCells.blocked` is untouched — the one-blocking-fixture-per-cell
placement rule keeps barriers in their specialized store (unifying that
store is *not* attempted; §5 allows placement rules to restrict what the
model permits).

- plate: `Fixture('plate', channel)` at the plate tile. The channel
  latch iterates `cells.fixtures_of_kind('plate')`; the spec-0049
  bridge-refusal check reads the same. `Room.plates` field dies.
- flame nozzle: `Fixture('flame_nozzle', jet_dict)` at the jet's source
  tile. The jet dict keeps its precomputed `tiles`/`_tile_set` —
  **ray-cast beam derivation is explicitly out of scope**: occlusion by
  pushed blocks would be a behaviour change (a feature), deferred to the
  spec that wants it. Damage pass and renderer iterate the fixtures.
  `Room.flame_jets` field dies; a compat property serves the facade.

### G3 — blocks get identity

```python
class Block(Entity):     # entities.py — occupants move; Entity has col/row
    pass
```

`Room.from_data` builds `[Block(c, r) ...]`; `blocks_initial` stays a
tuple of positions; `_reset_blocks` rebuilds fresh `Block`s from it.
Consumers switch from tuple membership to position comparison (small
lists — same cost). Tests asserting `room.blocks == [(6, 8)]` switch to
a position view (allowed test edits; goldens untouched). This is pure
representation: no observable change, but BL-37's per-block countdown
state gets the object it needs.

### G4/G5 — sprite table, pinned order

`game.py`: `_ITEM_SPRITE = {'treasure': …, 'material': …, 'key': …}` and
fixture sprites keyed by kind — replacing the last per-kind f-string
scatter. Blit category order stays hardcoded (screenshots pin pixels).
`World.update`'s docstring states the system order as the contract.

## Non-goals

- **No new element kinds** (levers/buttons/machines — future feature
  specs validate the registry then).
- **No ray-cast fields** (behaviour change; kb R3 stays future).
- No barrier-store unification, no BL-12 edge types, no dead-squares
  reclassification (solver metadata, not content).

## Verification

1. `poe test` green, **zero golden diffs**, no `UGLYCRAFT_REGOLD`.
2. Red-first: fixture-layer API; plate latch + 0049 refusal via
   fixtures; flame damage/render parity; `Block` identity (push moves
   the same object; reset creates fresh ones); registry covers every
   room-dict content key (a completeness assertion against a fixture
   dict using all kinds).
3. Manual gate: user plays an Act 2 level with plates, flames, and
   blocks — nothing should feel different at all.

## Done when:

- [ ] G1 — parser loop over `CONTENT_PARSERS`
- [ ] G2 — plate + nozzle fixtures; Room fields replaced
- [ ] G3 — `Block` occupants with identity
- [ ] G4 — sprite tables; blit order pinned
- [ ] G5 — system-order contract documented
- [ ] G6 — tests red→green; goldens byte-identical
- [ ] G7 — docs + backlog updated

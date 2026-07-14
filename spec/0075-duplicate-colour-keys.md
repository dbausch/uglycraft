# Spec 0075 — Duplicate-colour keys: cap 4 per colour + stacked HUD key icons

Backlog: **BL-56 (P2)**. A tester was shown levels containing multiple keys of
the same colour. Decision (Daniel, 2026-07-14): **live with duplicate-colour
keys** — reducing locked-room counts drastically to force uniqueness is not
wanted — but (a) put a **hard cap of 4 keys per colour** on the generator, and
(b) make the duplication **legible in the HUD** by drawing a stack of overlaid
key icons per colour (1–4), showing how many exist and how many are held,
without growing the HUD horizontally.

Supersedes the "keys are unique — at most one of each colour" assumption stated
in spec 0071 and `kb/requirements.md` R-K1; that was only ever true for levels
with ≤7 locked doors.

## Status checklist

- [x] **D1** — Generator caps locked doors at **4 per colour** per level:
  `_next_color()` never returns a colour already used 4 times; when all 7
  colours are capped (a would-be 29th locked door) the offending edge is created
  as an **open** passage instead (no lock, no key). Hard limit: **28** locked
  doors per level. *(8c5aec6)*
- [ ] **D2** — HUD key strip draws, per colour present in the level, a **stack
  of `total` key icons** (total = doors of that colour in the level), overlaid
  down-right at `index*2` px, with the `held` front ones drawn as normal keys
  and the rest as opaque ghost keys. Same per-colour slot pitch as today (no
  horizontal growth, no reflow during play). *(ab8bd52 — code+tests done,
  awaiting in-game acceptance)*
- [x] **D3** — `kb/requirements.md` R-K1/R-K2 and `kb/findings.md` updated:
  per-colour `#keys == #locked doors` still holds, but a colour may now
  legitimately have **1–4** keys/doors (not unique). Spec 0071's "keys are
  unique" note corrected.
- [ ] **D4** — Verification: statistical sweep asserts `≤4` keys per colour and
  `≤28` locked doors across many generated levels (detector validated on a
  forced `>28`-door feature set: pre-fix yields 5+/colour, post-fix caps at 4 +
  opened overflow, no orphan keys); HUD render smoke test; affected Act 2 goldens
  re-recorded; user confirmation in-game. *(tests/test_dup_colour.py +
  tests/test_render.py green, goldens re-recorded; awaiting in-game acceptance)*

## Background — confirmed facts (self-contained; do not re-derive)

**Key model** (`crafting.py`): `Inventory.keys` is a `{colour: count}` dict —
already supports multiple keys of one colour. `add_key` increments, `use_key`
decrements, `has_key` tests `> 0`. Colours are the seven strings
`red, blue, green, yellow, cyan, purple, orange` (`KEY_COLORS` / `KEY_NAMES`).

**Doors consume keys** (`world.py` `_try_auto_open_door`): bumping a locked door
with a matching key calls `inventory.use_key(colour)` and removes the barrier;
`_opened_doors` records `(room, col, row, colour)`. Colour is the *only* pairing
— any key of colour X opens any door of colour X. So a level with 2 blue doors
gives 2 blue keys and either opens either; R-K1 (`#keys == #doors` per colour)
keeps it solvable.

**Colour assignment** (`levelgraph.py:441` `generate`): a shuffled pool of the 7
colours; `_next_color()` `pop()`s one per locked door, refilling+reshuffling when
empty. Because the pool empties all 7 before refilling, colours are distributed
**evenly**: after a level's `T` locked doors, every colour has been used
`floor(T/7)` or `ceil(T/7)` times, so the max per colour is exactly `ceil(T/7)`.
`_next_color()` is called at two sites: interior locked rooms
(`_add_room`, `et == EdgeType.LOCKED` → `add_locked_room(_next_color())`,
~line 462) and border-passage locks (`_barrier_kw`,
`{'barrier':'locked','key_colour': _next_color()}`, ~line 478).

**Consequence** (measured — `scratchpad/sweep_dup_colour.py`, 300 levels,
seeds 0–29, levels 11–20):
- 46% of levels have duplicate-colour keys/doors; frequency scales with level
  (0% at L11–13, ~40% at L16, ~97% at L20).
- Per-colour counts observed: 62.2% of colour-slots hold 1 key, 30.8% hold 2,
  6.7% hold 3, 0.2% hold 4. **Max ever = 4** (never 5, because `ceil(T/7) ≤ 4`
  for `T ≤ 28`, and the largest observed `T` was 24).
- So the common 2–4/colour duplication is *already within* the intended cap.
  The generator change (D1) only guards the unobserved `T > 28` tail; the HUD
  change (D2) is what actually resolves the tester's confusion.

**Current HUD key strip** (`game.py` `_key_strip_element`, `world.py:325`):
`World._level_key_colours` is the ordered list of distinct colours present as
keys in the level; the strip draws one 20 px icon per colour in a fixed
`_KEY_SLOT = 23` px slot, lit when `inventory.keys[colour] > 0`, else ghosted at
`_KEY_GHOST_ALPHA = 38` (transparent). No per-colour count is shown, so 2 blue
keys + 2 blue doors look identical to 1+1. HUD row is `STATUS_H = 28` px tall;
the strip must not reflow during play (spec 0071/0072) and cannot grow
horizontally (row is near-full).

## D1 — Generator: 4-per-colour cap, hard limit 28

Add `MAX_KEYS_PER_COLOUR = 4` (module constant in `levelgraph.py`).

In `generate`, track per-colour usage and skip capped colours:

```python
color_counts = {c: 0 for c in KEY_COLORS}

def _next_color():
    # None when every colour has hit the cap (a would-be 29th locked door)
    if all(color_counts[c] >= MAX_KEYS_PER_COLOUR for c in all_colors):
        return None
    while True:
        if not color_pool:
            color_pool.extend(all_colors)
            rng.shuffle(color_pool)
        c = color_pool.pop()
        if color_counts[c] < MAX_KEYS_PER_COLOUR:
            color_counts[c] += 1
            return c
```

Callers handle `None` by creating an **open** passage instead of a locked one:
- interior (`_add_room`): `colour = _next_color();` if `None` →
  `b.add_open_room(size=size)` else `b.add_locked_room(colour, size=size)`.
- border (`_barrier_kw`): `colour = _next_color();` if `None` → `return {}`
  (open border) else `return {'barrier':'locked','key_colour': colour}`.

This is a deliberate downgrade (no key placed, no lock) — **not** a silent door
elision of the BL-44/BL-46 class (there is no orphaned key, because the lock was
never created). It fires only above 28 locked doors, which the sweep never
reached; it exists so the invariant is guaranteed, not merely usually true.

**Even-distribution note:** because the existing pool already yields
`max = ceil(T/7)`, the cap's skip branch only ever triggers at `T ≥ 29`; for
`T ≤ 28` the draw sequence is byte-identical to today, so only levels that would
have exceeded 28 change. Determinism (BL-40) preserved — the cap uses only
`color_counts` and the existing seeded `rng`.

## D2 — HUD: stacked multi-key icons per colour

Replace the single-icon-per-colour render with a **stack** per colour. Exact
compositing (approved via `scratchpad/key_final_mockups.py`, look confirmed by
Daniel 2026-07-14):

```
for index in range(total):            # total = doors of this colour in level
    pos = (index*2, index*2)          # down-right, fixed shape
    if total - held > index:
        draw GHOST key at pos         # index 0..(total-held-1): the back ones
    else:
        draw NORMAL key at pos        # the front `held` ones, drawn last = on top
```

- **Order/occlusion:** higher `index` is drawn later, so the front-most
  (bottom-right) keys are on top. The `held` keys occupy the high indices and are
  fully visible in front; unheld **ghost** keys occupy the low indices and recede
  up-left behind, barely visible. "I hold at least one" is always the crisp
  front element.
- **Ghost key:** the key sprite recoloured to **15% key-colour / 85% HUD_BG**,
  **full alpha (opaque)** — *not* the old transparent ghost. Opaque ghosts
  occlude cleanly (no see-through smearing). Build: bg-coloured silhouette from
  the key's alpha mask, then the key blitted over it at 15% alpha.
- **Rim:** every key (normal and ghost) keeps a **1 px dark rim**
  `(12, 10, 8)` (as in the approved `diag-dr-2` mock), built by blitting a dark
  silhouette at the 8 neighbour offsets under the key. The rim keeps overlapping
  same-colour keys countable. (This adds a subtle outline to the single-key case
  vs. today; accepted.)
- **Icon size:** 20 px keys (as today) → a 4-stack spans `20 + 3*2 = 26` px
  (28 with rim). Vertically it fits the 28 px row. Horizontally it exceeds the
  23 px slot by ~3 px; keep the **slot pitch at its current value** (no strip
  widening) and let the stack bleed into the inter-element padding. If in-game
  the rightmost colour's stack collides with the neighbouring HUD element,
  fall back to a smaller offset; this is a **user-acceptance** item.

**Count semantics — fixed total, 2-state (decided, matches the approved mock):**
- `total` = number of keys of that colour in the level (== doors, R-K1), constant
  for the level → strip never reflows.
- `held` = `inventory.keys.get(colour, 0)` — keys **currently in hand**.
- Lit = held; ghost = not currently held. After a key is spent on a door, `held`
  drops and the front dims back toward ghost — this is truthful (you no longer
  hold it). *Considered and deferred:* a progress-preserving 3-state variant
  (opened doors stay permanently lit via `_opened_doors`) — not adopted, to match
  the 2-state look approved; may be revisited if Daniel prefers it at review.

**Plumbing:**
- `world.py`: add `World._level_key_counts` (a `{colour: total}` dict built the
  same pass as `_level_key_colours`); add it to the `__slots__`/reset list
  (alongside `_level_key_colours`).
- `sprites.py`: provide rimmed **lit** and **ghost** 20 px key icons per colour
  (e.g. `icon_key_<c>` gains a rim; add `icon_key_<c>_ghost`), or expose a small
  builder Game can call once per level.
- `game.py`: a `_key_stack_surface(colour, total, held)` helper runs the loop
  above and returns a Surface; the HUD element places one per colour at the
  fixed slot pitch. The per-colour lit/ghost base icons are pre-rendered once per
  level; only the cheap blit-loop runs per frame (held changes as keys are
  collected/spent). Keep the "no strip when the level has no keys" behaviour.

## D3 — Docs

- `kb/requirements.md` **R-K1**: keep `#keys == #locked doors` per colour; state
  that a colour may hold **1–4** keys/doors (capped at
  `MAX_KEYS_PER_COLOUR = 4`, hard limit 28 doors/level); drop any "unique per
  colour" wording. Cross-reference this spec.
- `kb/findings.md`: record that duplicate-colour keys are by-design (≤4/colour),
  with the even-distribution `ceil(T/7)` mechanism and the sweep numbers.
- Correct the spec 0071 "keys are unique / count is always 1" note (add an errata
  pointer to spec 0075).
- `kb/uglycraft-display.md` HUD-layout section: document the stacked key render.

## Verification

- **Sweep (detector-validated):** extend `scratchpad/sweep_dup_colour.py` into a
  pytest (`tests/test_key_placement.py` R-K1 section, or a new
  `tests/test_dup_colour.py`) asserting, over many seeds × levels 11–20,
  `max(keys_per_colour) ≤ 4` and `total_locked_doors ≤ 28`. Validate the detector
  on a **forced** feature set (all-LOCKED, room_count high enough to demand
  `>28` doors): confirm the *pre-fix* generator produces `≥5` of some colour and
  `>28` doors, and the *post-fix* generator caps at 4 with the overflow edges
  opened and **no orphan keys** (per-colour `#keys == #doors` still holds).
- **HUD:** a headless render smoke test (build a level with a known
  per-colour count, render the HUD, assert no exception and the strip width is
  unchanged from the single-icon strip). Screenshot golden for a stacked strip.
- **Goldens:** re-record any Act 2 `act2_L*_walk` goldens whose stream changes
  (only levels that would have exceeded 28 doors, if any; likely none for the
  pinned seeds). Run the full suite in the background.
- **User acceptance (D2/D4):** Daniel confirms in-game that the stacked key HUD
  reads correctly and does not collide with neighbouring HUD elements.

## Done when

- [x] **D1** `_next_color()` enforces `MAX_KEYS_PER_COLOUR = 4`, returns `None`
  when all colours are capped, and both call sites downgrade to an open passage;
  no level exceeds 28 locked doors or 4 keys of any colour. *(8c5aec6)*
- [ ] **D2** HUD draws the per-colour key stack via the exact loop (opaque 15%
  ghosts, 1 px rim, `index*2` down-right offset, held-in-front), at the current
  slot pitch, no reflow; strip omitted when the level has no keys. *(ab8bd52;
  awaiting user in-game acceptance)*
- [x] **D3** R-K1/R-K2 / findings / display KB and the spec 0071 errata updated.
  *(this commit)*
- [ ] **D4** Detector-validated sweep test green (≤4/colour, ≤28 doors, no orphan
  keys on the forced overflow case); HUD render smoke green; affected goldens
  re-recorded; full suite green. *(tests green; awaiting user in-game acceptance
  to close)*

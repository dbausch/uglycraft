# Spec 0074 — Shared "action denied" SFX

Backlog: **BL-52 (P2)**. When the player attempts a *deliberate* action that the
rules refuse, the game is currently silent. Add **one** shared sound — the same for
every case — that plays whenever such an attempt is rejected. This is about refused
deliberate actions (SPACE / RETURN / bump-to-interact), **not** walking into a plain
wall (that already has the `bump` sound and would be too noisy) and **not** bumping an
inert barrier (normal navigation).

## Status checklist

- [ ] **D1** — A single `'action_denied'` world event is emitted at each refusal site
  (locked door without key, bridge refused, block placement refused, buy-shield
  refused); held-key bumps fire it at most once per press; inert-barrier bumps and
  plain wall-mining never fire it.
- [ ] **D2** — One new `sfx_denied` ("wrongbeep") added to `sounds.py`, mapped
  `'action_denied' → 'denied'` in `game.py`'s `_EVENT_SOUNDS`.
- [ ] **D3** — Verification: world unit tests assert the event at each site and its
  absence at the out-of-scope sites; the spam-gate holds; affected event-trace goldens
  re-recorded.
- [ ] **D4** — Daniel confirms the denial sound in-game (and that it is not spammy).

## Background — confirmed facts

Established by reading the code after spec 0073 (self-contained; do not re-derive):

### Input model (`game.py`)

In the PLAYING key handler (`game.py` ~349–378): **SPACE** → `world.place()` and
**RETURN** → `world.buy_shield()` fire on `KEYDOWN` only — they are *not* in
`self._key_repeat` (only the four arrow keys are), so holding them does **not** repeat
the call. Direction keys are re-fired each tick by `_key_repeat_phase`, so a *held*
direction key drives `_register_bump` every tick.

### Bump dispatch + the `_bump_consumed` gate (`world.py` `_register_bump`)

```
if key in self._bump_consumed: return          # key not released since last hit
barrier = self.cells.barrier(col, row)
if barrier is None:
    self._try_auto_bridge(col, row); return    # water bridge attempt OR inert block
action = BARRIER_BUMP[barrier.kind]
if action == 'key':  self._try_auto_open_door(col, row); return   # a door
if action is None:   return                    # border/reinforced/gate: inert
self._bump_consumed.add(key)                    # breakable wall: one hit per press
...
```

Only the breakable-wall path adds `key` to `_bump_consumed`; the door and bridge paths
re-check every tick while the key is held. `key_released(key)` discards it, so the next
press bumps again. `is_water(col,row)` distinguishes a genuine water/bridge attempt
from an inert pushable-block bump (the push already failed upstream).

### The refusal sites today (all currently silent)

- **Locked door without key** — `_try_auto_open_door` (`world.py:557`):
  `if not self.inventory.has_key(barrier.colour): return False`. Reached from
  `_register_bump`'s `action == 'key'` branch, so the barrier is definitely a door.
- **Bridge refused** — `_try_auto_bridge` (`world.py:571`): after confirming
  `is_water`, it returns `False` when the water room is already bridged, a landing tile
  carries a plate, `self._bridge_credits <= 0`, or the far side is blocked (spec 0073
  made the credit the gate).
- **Block placement refused** — `_place_block` (`world.py`): the guard
  `if _block_credits > 0 and not blocked(c,r) and not _is_respawn_tile(c,r)` fails →
  nothing happens. Covers *no credit*, *target blocked*, and *respawn/`player_start`
  tile* (spec 0067). This is the only placement path after spec 0073.
- **Buy shield refused** — `buy_shield` (`world.py`):
  `if not self.shield and self.score >= SHIELD_COST_PTS` fails → refused (already
  shielded **or** insufficient score).

### Out of scope (no denial sound)

- **Inert-barrier bumps** — border / reinforced / closed gate (`BARRIER_BUMP[kind] is
  None`): normal navigation, confirmed out of scope (Daniel, 2026-07-12).
- **Plain breakable-wall bump** — that is progress (mining), already has `bump`/`break`.
- **Inert pushable-block bump** — the failed push is normal navigation.
- **Craft without materials** — the inventory/crafting menu is **disabled** since spec
  0073 D5 (`ENABLE_INVENTORY_MENU = False`), so `game.py`'s crafting handler is
  unreachable; nothing to wire. (If the menu is ever re-enabled, add the denial there.)

### Sound wiring

`game.py` `_EVENT_SOUNDS` maps world-event kinds → SFX keys; `_pump_world` plays the
mapped sound for each drained event. `sounds.py` `_build_sfx(np)` defines each
`sfx_*()` and returns a dict keyed by SFX name (e.g. `'place_block': sfx_place_block()`);
helpers `_sq`, `_env`, `_saturate`, `_to_sound`, `_RATE` are available.

### Chosen SFX — "wrongbeep" (Daniel, 2026-07-14)

A flat low square-wave beep with a fast rasp tremolo (auditioned against five
alternatives). Recipe:

- square wave at **147 Hz**, ~**180 ms**
- × a 32 Hz half-amplitude square tremolo: `trem = 1.0 + 0.5*sign(sin(2π·32·t))`
- ADSR `env(atk=0.003, dec=0.02, sus=0.85, rel=0.06)`
- soft-saturate, drive ~**2.5**

## D1 — The `'action_denied'` event

Add one world event, `'action_denied'`, to the event docstring list, emitted at each
refusal site immediately before its early return. The **spam gate** differs by input:

**Bump-based sites (door, bridge) — one denial per press.** Restructure `_register_bump`
so a *deliberate* bump attempt consumes the key (like the wall path) and emits the
denial when the attempt is refused:

```python
def _register_bump(self, key, col, row):
    if key in self._bump_consumed:
        return
    barrier = self.cells.barrier(col, row)
    if barrier is None:
        if self.cells.is_water(col, row):           # a deliberate bridge attempt
            self._bump_consumed.add(key)
            if not self._try_auto_bridge(col, row):
                self._emit('action_denied')
        return                                       # non-water: inert push, no denial
    action = BARRIER_BUMP[barrier.kind]
    if action == 'key':                              # a locked door
        self._bump_consumed.add(key)
        if not self._try_auto_open_door(col, row):
            self._emit('action_denied')
        return
    if action is None:
        return                                       # inert barrier: no denial
    # breakable wall: unchanged (mining)
    self._bump_consumed.add(key)
    ...
```

`_try_auto_open_door` / `_try_auto_bridge` keep returning `True`/`False` and no longer
need to emit anything themselves; the caller decides. Because the key is now consumed
on a refused door/bridge bump, a held key fires the denial exactly once (until
release) — the same rhythm walls already have. *(Consequence: a held direction key no
longer auto-opens a door / builds a bridge the instant the key or credit is acquired;
the player releases and re-presses — which they do anyway, since collecting the
key/planks requires moving off the bump. Acceptable and consistent with walls.)*

**Key-press sites (SPACE, RETURN) — one denial per press, no gate needed** (KEYDOWN
does not repeat):

- `_place_block`: emit `'action_denied'` in the `else` of the placement guard.
- `buy_shield`: emit `'action_denied'` in the `else` of the purchase guard.

```python
def _place_block(self):
    c, r = self.player.col, self.player.row
    if self._block_credits > 0 and not self.blocked(c, r) and not self._is_respawn_tile(c, r):
        self._block_credits -= 1
        self.cells.set_barrier((c, r), Barrier('placed'))
        self._emit('block_placed')
    else:
        self._emit('action_denied')

def buy_shield(self):
    if not self.shield and self.score >= SHIELD_COST_PTS:
        ...                        # unchanged
        self._emit('shield_bought')
    else:
        self._emit('action_denied')
```

## D2 — The `sfx_denied` sound

Add `sfx_denied()` to `_build_sfx` in `sounds.py` using the wrongbeep recipe, register
it under `'denied'` in the returned dict, and map `'action_denied': 'denied'` in
`game.py`'s `_EVENT_SOUNDS`:

```python
def sfx_denied():
    n = round(_RATE * 0.18)
    t = np.arange(n, dtype=np.float32) / _RATE
    trem = 1.0 + 0.5 * np.sign(np.sin(2*np.pi*32.0*t))
    sig = _sq(np, 147.0, n, 0.4) * trem * _env(np, n, 0.003, 0.02, 0.85, 0.06)
    return _to_sound(np, _saturate(np, sig, 2.5))
```

(Exact numbers may be nudged for level-matching against the other SFX; the character —
low square + 32 Hz rasp — is fixed.)

## D3 — Verification

pygame-free world unit tests (`tests/test_world.py`) assert the event stream; the
`SoundManager` builds all SFX at construction (a smoke check that `'denied'` exists).

1. **Emitted at each site** — `'action_denied'` appears when: bumping a locked door
   without the key; bumping water with no bridge credit / an already-bridged room / a
   plate-adjacent landing / a blocked far side; pressing SPACE with no block credit, on
   a blocked tile, and on the respawn tile; pressing RETURN with < 250 pts and while
   already shielded.
2. **Not emitted (out of scope)** — bumping an inert barrier (border/reinforced/closed
   gate); mining a breakable wall; a successful door-open / bridge / block-place /
   shield-buy emits its normal event and **no** `'action_denied'`.
3. **Spam gate** — holding a direction key into a locked door (multiple
   `_register_bump` ticks) yields exactly **one** `'action_denied'` until
   `key_released`; after release + re-press it fires again.
4. **Sound present** — `SoundManager().sfx` (or equivalent) contains `'denied'`;
   `_EVENT_SOUNDS['action_denied'] == 'denied'`.
5. **Goldens** — any existing event-trace golden whose scripted run now hits a refusal
   gains an `'action_denied'` / `'denied'` entry; re-record and review (expect these to
   be few — most golden runs take only successful actions).
6. **Manual check** — Daniel plays and confirms the denial sound fires on a refused
   door/bridge/block/shield, is not spammy on held keys, and stays silent on inert-wall
   navigation.

## Out of scope

- Distinct sounds per refusal type (one shared sound is the whole point).
- Re-enabling / wiring the crafting menu's craft-without-materials denial (menu disabled
  since spec 0073 D5).
- Visual feedback (flash/shake) for denials — audio only.
- The future "no placing next to an entrance" rule (none exists yet); when added, it
  routes through `_place_block`'s refusal and gets the sound for free.

## Done when:

- [ ] **D1** — `'action_denied'` emitted at the four refusal sites; bump sites gated to
  one-per-press via `_bump_consumed`; inert/mining sites silent. *(commit: ____)*
- [ ] **D2** — `sfx_denied` ("wrongbeep") in `sounds.py`; `'action_denied' → 'denied'`
  in `_EVENT_SOUNDS`. *(commit: ____)*
- [ ] **D3** — unit tests for every in-scope and out-of-scope site + the spam gate pass;
  affected goldens re-recorded and reviewed. *(commit: ____)*
- [ ] **D4** — Daniel confirms the denial sound in-game (fires on refusals, not spammy,
  silent on plain navigation). *(commit: ____)*

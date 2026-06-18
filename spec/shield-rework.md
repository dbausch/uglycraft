# Shield rework & shop removal

## Status

- [x] Shop state and extra-life purchase removed
- [x] Enter instantly buys a shield for 250 pts (no shop screen)
- [x] Shield expires automatically after 10 seconds
- [x] On any hit: hitting enemy always respawns far away
- [x] If shielded when hit: shield consumed, no life lost
- [x] If unshielded when hit: lose a life, player returns to start

## Design

**Shield purchase:** Pressing Enter while playing immediately deducts 250 pts and
activates the shield, provided score ≥ 250 and no shield is already active.
No modal screen is opened.

**Shield lifetime:** 10 seconds (10 000 ms). The HUD shows remaining seconds
(e.g. "SHIELD 7s"). The timer is cleared when the shield is consumed by a hit.

**Hit mechanics:** When any enemy occupies the same tile as the player:

1. The hitting enemy is teleported to an open tile at BFS distance ≥ 8 from the
   player (fallback: ≥ 4 if nothing qualifies at ≥ 8).
2. If shielded: shield consumed, player stays in place, no life lost.
3. If unshielded: lose a life (score − 500, min 0), player returns to
   `player_start` for the current level.

**Removed:**
- `SHOP` game state and all associated rendering/event code
- `LIFE_COST_PTS` constant
- `_shop_event()`, `_render_shop()`
- `_respawn_boss()` — replaced by the general `_respawn_enemy(enemy)`

## Done when

- [x] Shop state removed from all code paths; `LIFE_COST_PTS` gone from constants.py — 4c83854, 7d9091b
- [x] Pressing Enter in-game instantly buys shield (250 pts) with no screen change — 7d9091b
- [x] Shield auto-expires after 10 s; HUD shows live countdown in whole seconds — 7d9091b, 91f8317
- [x] On any collision the hitting enemy is teleported to BFS distance ≥ 8 (fallback ≥ 4) — 7d9091b
- [x] Shielded hit: shield consumed, enemy respawned, no life lost — 7d9091b
- [x] Unshielded hit: life lost, player to start, hitting enemy still respawned — 7d9071b

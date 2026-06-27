# Ogre enemies

## Status

- [x] Ghost sprites removed; replaced by three distinct ogre sprites
- [x] Boss ghost replaced by animated boss ogre (4 phases)
- [x] Enemy sprite selection by level group (1–3 / 4–6 / 7–9 / 10)
- [x] All four enemy types shown in title-screen corners, bouncing randomly

## Design

**Ogre 1 (levels 1–3):** Simple green ogre. No horns. Round white eyes with black
pupils. Simple mouth with two teeth. Friendly-ish.

**Ogre 2 (levels 4–6):** Orange-brown ogre. Two small upward horns. Angled brow,
squinting yellow eyes. Wide grinning mouth with row of teeth and side tusks.

**Ogre 3 (levels 7–9):** Dark purple ogre. Larger curved horns. Heavy brow, glowing
red eyes. Red diagonal war-paint slashes on cheeks. Snarling mouth with big tusks.

**Boss ogre (level 10, 4-frame animation):**
Dark red skin, gold triple-pronged crown, armour shoulder plates, scar.
Animation (phase 0–3): eye size and colour cycle (orange → bright → deep red →
yellow flare); mouth alternates closed (phases 0, 2) and open (phases 1, 3).

**Enemy sprite selection:** `enemy_{(level-1)//3 + 1}` for levels 1–9; boss sprites
for level 10.

**Title screen corners:**
- Top-left: ogre 1; top-right: ogre 2; bottom-left: ogre 3; bottom-right: boss.
- Each bounces within its corner region (~80×80 px) at ~50–80 px/s.
- Boss uses the same 4-phase animation as in-game.

## Done when

- [x] `draw_enemy()` and `draw_boss()` removed; `draw_ogre_1/2/3()` and `draw_boss_ogre(phase)` in place — 5ea193c
- [x] `create_sprites()` exposes `enemy_1`, `enemy_2`, `enemy_3`, `boss_0`–`boss_3` — 5ea193c
- [x] `_render_field()` picks the right sprite key for the current level — 145b565
- [x] `_title_init()` sets up 4 corner ogre states; `update()` moves them; `_render_title()` draws them — 145b565, 7bf3699, 05cd46e, 457d790

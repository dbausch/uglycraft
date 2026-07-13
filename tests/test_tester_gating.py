"""Tester-build gating tests (spec 0073, BL-26).

D4: no scrap metal in generated levels (ENABLE_METAL is False).
D5: the inventory / crafting menu is fully disabled (ENABLE_INVENTORY_MENU).
"""
import pygame

import levels
from levels import ACT2_FEATURE_SETS
from crafting import MAT_METAL
from tests import act2_fixtures as fx
from tests.harness import Harness


# ── D4: metal gate ────────────────────────────────────────────────────────────

def test_no_metal_in_feature_sets():
    """add_materials can only place types listed here, so this is the source
    of truth: with metal gated, no feature set offers it."""
    assert all(MAT_METAL not in fs['material_types'] for fs in ACT2_FEATURE_SETS)


def test_generated_levels_drop_no_metal():
    """A generated level (levels that used to carry metal) contains no metal
    material anywhere."""
    levels.set_game_seed(4242)
    for lvl in (12, 13, 14, 17):
        d = levels.regenerate_level(lvl)
        for room in d['rooms'].values():
            assert all(m[2] != 'metal' for m in room.get('materials', [])), \
                f'metal found in generated level {lvl}'


# ── D3: more rubble ───────────────────────────────────────────────────────────

def test_rubble_budget_boosted():
    """Every feature set's rubble floor is raised (was 4–10 before D3)."""
    assert all(fs['material_count'][0] >= 8 for fs in ACT2_FEATURE_SETS)


def test_generated_levels_have_ample_rubble():
    """Since blocks are earned from rubble (2 = 1) and breakable walls are
    scarce, generated levels carry plenty of it."""
    levels.set_game_seed(2024)
    for lvl in (11, 15, 20):
        d = levels.regenerate_level(lvl)
        rubble = sum(1 for room in d['rooms'].values()
                     for m in room.get('materials', []) if m[2] == 'rocks')
        assert rubble >= 6, f'level {lvl} had only {rubble} rubble'


# ── D5: inventory / crafting menu disabled ────────────────────────────────────

def test_tab_does_not_open_inventory_menu():
    """With ENABLE_INVENTORY_MENU=False, pressing TAB while playing does not
    enter the INVENTORY state (the overlay is never shown)."""
    from game import PLAYING, INVENTORY
    with Harness(level_dict=fx.showcase_level(), seed=42) as h:
        h.run(['wait:2'])
        assert h.game.state == PLAYING
        h.run(['key:tab', 'wait:1'])
        assert h.game.state == PLAYING          # TAB ignored
        assert h.game.state != INVENTORY

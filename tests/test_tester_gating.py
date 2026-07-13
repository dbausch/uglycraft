"""Tester-build gating tests (spec 0073, BL-26).

D4: no scrap metal in generated levels (ENABLE_METAL is False).
D5: the inventory / crafting menu is fully disabled (ENABLE_INVENTORY_MENU).
"""
import levels
from levels import ACT2_FEATURE_SETS
from crafting import MAT_METAL


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

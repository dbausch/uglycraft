"""Tests for lazy per-level Act 2 generation (spec 0028, BL-11).

Act 2 levels (11-20) must be generated one at a time, on first access, and
cached for the rest of the game. No generation happens at import time, and a
new game reshuffles the levels without any up-front cost.
"""
import importlib

from uglycraft import levels


def _fresh():
    """Reload the levels module to get a pristine, un-touched cache."""
    return importlib.reload(levels)


def test_no_generation_at_import():
    L = _fresh()
    # Only the 10 hand-authored Act 1 levels exist after import.
    assert len(L.LEVELS) == L._ACT1_COUNT == 10
    # Nothing in the Act 2 cache yet.
    assert L._act2_cache == {}


def test_total_levels_constant():
    L = _fresh()
    assert L.TOTAL_LEVELS == 20


def test_act1_returns_handauthored_dict():
    L = _fresh()
    for n in range(1, L._ACT1_COUNT + 1):
        assert L.get_level(n) is L.LEVELS[n - 1]


def test_act2_generated_and_cached():
    L = _fresh()
    lvl = L.get_level(11)
    assert isinstance(lvl, dict)
    assert 'rooms' in lvl and 'player_start' in lvl
    # Second access returns the very same cached object.
    assert L.get_level(11) is lvl


def test_access_is_lazy():
    L = _fresh()
    L.get_level(11)
    # Accessing level 11 must not have generated 12-20.
    assert set(L._act2_cache) == {11}


def test_generation_is_deterministic_for_fixed_seed():
    L = _fresh()
    seed = 4242
    L._game_seed = seed
    L._act2_cache.clear()
    a = L.get_level(13)
    # Drop the cache but keep the seed -> regenerating must reproduce the level.
    L._act2_cache.clear()
    b = L.get_level(13)
    assert a['player_start'] == b['player_start']
    assert sorted(a['rooms']) == sorted(b['rooms'])
    for rk in a['rooms']:
        assert sorted(a['rooms'][rk]['walls']) == sorted(b['rooms'][rk]['walls'])


def test_new_game_levels_reshuffles_without_generating():
    L = _fresh()
    L.get_level(11)
    assert L._act2_cache != {}
    old_seed = L._game_seed
    L.new_game_levels()
    # Cache cleared, fresh seed, and still nothing generated up front.
    assert L._act2_cache == {}
    assert L._game_seed != old_seed


def test_progress_callback_reports_per_grid():
    """A multi-grid Act 2 level reports progress as (done, total) per grid."""
    L = _fresh()
    reports = []
    # Level 20 has grid_count 10 -> total should be 10.
    L.get_level(20, progress=lambda done, total: reports.append((done, total)))
    assert reports, "progress callback was never called"
    totals = {t for _, t in reports}
    assert totals == {10}
    # done values are non-decreasing within the final successful attempt and reach total.
    assert reports[-1] == (10, 10)

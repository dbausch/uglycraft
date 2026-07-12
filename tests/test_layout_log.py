"""Layout failure log + dict-level renderer (spec 0065 D2 / BL-46, BL-48(a)).

Every LayoutError that escapes the top-level build_level_dict call appends
a diagnostic entry to levellayout.LAYOUT_LOG_PATH before propagating into
the fresh-seed retry; per-strategy candidates absorbed inside _build_grid
never log.  leveldump.render_rooms is the public dict-level renderer
(no World, no get_level) that draws the entry's annotated super-grid
canvas — the BL-48(a) enabler.
"""
import random

import pytest

import levellayout
from constants import COLS, ROWS
from levelgraph import LevelGraph
from levellayout import LayoutError, build_level_dict
from tests.conftest import FS_ALL


# ── renderer unit (BL-48(a) enabler) ─────────────────────────────────────────

def _bare_room():
    """Minimal room dict: empty interior; the parser draws the border."""
    return {'walls': {}, 'tile_owner': {}}


def test_render_rooms_canvas():
    """Two hand-written room dicts at explicit (non-normalised) super
    positions plus a failed grid: blocks land at the right canvas
    offsets, the failed grid's index line carries '<-- FAILED', and a
    !-bordered placeholder with FAILED centred sits at its position."""
    from leveldump import render_rooms
    rooms = {'grid_a': _bare_room(), 'grid_1': _bare_room()}
    positions = {'grid_a': (2, 1), 'grid_1': (1, 1), 'grid_2': (1, 2)}
    msg = "no strategy placed grid 'room_7'"
    out = render_rooms(rooms, positions, failed=('grid_2', msg))

    head, _, canvas = out.partition('\n\n')
    index = head.splitlines()
    assert len(index) == 3
    assert index[0].startswith('grid_a @ ') and 'exits:' in index[0]
    assert index[1].startswith('grid_1 @ ') and 'exits:' in index[1]
    assert index[2].startswith('grid_2 @ ') and f'<-- FAILED: {msg}' in index[2]

    lines = canvas.rstrip('\n').splitlines()

    def cell(x, y):
        return lines[y][x] if y < len(lines) and x < len(lines[y]) else ' '

    # normalised: grid_1 -> (0,0), grid_a -> (1,0), grid_2 -> (0,1)
    for name, (gx, gy) in (('grid_1', (0, 0)), ('grid_a', (1, 0))):
        ox, oy = gx * (COLS + 1), gy * (ROWS + 1)
        for c, r in ((0, 0), (COLS - 1, 0), (0, ROWS - 1), (COLS - 1, ROWS - 1)):
            assert cell(ox + c, oy + r) == '#', f'{name}: corner ({c},{r})'
    ox, oy = 0, ROWS + 1
    for c, r in ((0, 0), (COLS - 1, 0), (0, ROWS - 1), (COLS - 1, ROWS - 1)):
        assert cell(ox + c, oy + r) == '!', f'placeholder corner ({c},{r})'
    mid_row = ''.join(cell(ox + c, oy + ROWS // 2) for c in range(COLS))
    assert 'FAILED' in mid_row
    # the empty super-cell (1,1) stays blank
    region = ''.join(cell((COLS + 1) + c, (ROWS + 1) + r)
                     for c in range(COLS) for r in range(ROWS))
    assert region.strip() == ''


def test_render_rooms_no_failed():
    """failed=None renders index + canvas with no FAILED annotations."""
    from leveldump import render_rooms
    out = render_rooms({'grid_a': _bare_room()}, {'grid_a': (0, 0)})
    assert 'FAILED' not in out
    assert out.startswith('grid_a @ (0, 0)')


# ── log integration ──────────────────────────────────────────────────────────

def _redirect(tmp_path, monkeypatch):
    path = tmp_path / 'uglycraft-layout.log'
    monkeypatch.setattr(levellayout, 'LAYOUT_LOG_PATH', str(path))
    return path


def test_log_entry_for_locked_edge_raise(tmp_path, monkeypatch):
    """The pinned BL-46 failure (FS_ALL seed 584, first retry attempt —
    see test_key_placement.test_pinned_dropped_locked_room) appends one
    entry: timestamp header, `grid: main`, the LOCKED-edge message."""
    path = _redirect(tmp_path, monkeypatch)
    base = random.Random(584)
    rng = random.Random(base.randint(0, 2 ** 31))
    g = LevelGraph.generate(FS_ALL, rng)
    with pytest.raises(LayoutError):
        build_level_dict(g, rng=rng)
    content = path.read_text()
    assert content.count('== LayoutError ') == 1
    assert 'grid: main' in content
    assert 'LOCKED edge' in content and 'cyan' in content
    assert 'BL-46' in content


def test_no_spam_on_multi_grid_build(tmp_path, monkeypatch):
    """Healthy multi-grid build (level-13 set, seed 777): per-strategy
    candidate failures inside _build_grid never log — the log stays empty
    when the build succeeds first try, and otherwise contains exactly one
    whole-attempt entry per escaping LayoutError."""
    import levels as _levels
    path = _redirect(tmp_path, monkeypatch)
    fs = _levels.ACT2_FEATURE_SETS[2]
    base = random.Random(777)
    failures = 0
    for _ in range(60):
        rng = random.Random(base.randint(0, 2 ** 31))
        g = LevelGraph.generate(fs, rng)
        try:
            build_level_dict(g, rng=rng,
                             strategies=fs.get('layout_strategies'))
            break
        except LayoutError:
            failures += 1
    else:
        raise AssertionError('build never succeeded')
    content = path.read_text() if path.exists() else ''
    assert content.count('== LayoutError ') == failures

"""Render-path tests: smoke + golden screenshots (spec 0044 H7/H8).

Screenshot goldens are the deliberately fragile tier (spec 0044): pixel
hashes recorded on this machine (font rasterisation may differ across
freetype/SDL versions). Re-record with UGLYCRAFT_REGOLD=1 after any
intentional visual change; drop or reduce these if they cost more than
they catch.
"""
from tests.harness import Harness


def test_act1_render_smoke():
    """Rendering an Act 1 playing field must not raise.

    Red when written: _render_field reads self._current_room_data
    unconditionally (game.py:1230), which is only assigned on the Act 2
    path -> AttributeError on every Act 1 render (BL-33, regression from
    04be23e).
    """
    with Harness(level=1, seed=1234) as h:
        h.run(['wait:3'])
        h.game.render()

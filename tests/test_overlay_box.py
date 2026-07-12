"""Spec 0059 (BL-24) — win message "YOU  WON!"; overlay box fits its text.

overlay_box_width(title_w, sub_w) =
    min(max(420, title_w + 2*PAD, sub_w + 2*PAD), LOGICAL_W - 40)

Red when written: the helper does not exist, and game.py still carries
the retired forge message behind a dead conditional.
"""
import pathlib

import tests.harness  # noqa: F401 — sets the dummy SDL drivers
import pygame

from constants import LOGICAL_W

PAD = 24
_ROOT = pathlib.Path(__file__).resolve().parent.parent

# The retired forge string stays here as the canonical overlong fixture.
OVERLONG = "THE  FORGE  IS  DEFEATED!"


# ── Formula properties (pure, no pygame) ─────────────────────────────────────

def test_formula_short_texts_keep_420():
    from game import overlay_box_width
    assert overlay_box_width(0, 0) == 420
    assert overlay_box_width(171, 180) == 420   # YOU  WON! + max score sub


def test_formula_wide_title():
    from game import overlay_box_width
    assert overlay_box_width(475, 180) == 475 + 2 * PAD


def test_formula_wide_sub_dominates():
    from game import overlay_box_width
    assert overlay_box_width(100, 500) == 500 + 2 * PAD


def test_formula_clamped_to_screen():
    from game import overlay_box_width
    assert overlay_box_width(5000, 0) == LOGICAL_W - 40
    assert overlay_box_width(0, 5000) == LOGICAL_W - 40


# ── Real-font fit: every call-site title + the overlong fixture ─────────────

def test_real_font_titles_fit_their_box():
    from game import overlay_box_width
    pygame.font.init()
    font = pygame.font.Font(str(_ROOT / 'fonts' / 'ShareTechMono-Regular.ttf'),
                            36)
    titles = ["LEVEL  20", "PAUSED", "GAME  OVER", "YOU  WON!",
              "PLAY AGAIN?", OVERLONG]
    for title in titles:
        w = font.render(title, True, (255, 255, 255)).get_width()
        bw = overlay_box_width(w, 0)
        assert w + 2 * PAD <= bw <= LOGICAL_W - 40, (
            f"{title!r}: rendered {w}px, box {bw}px")


# ── The win message (spec 0059 review: one unconditional sentence) ───────────

def test_win_message_is_you_won():
    src = (_ROOT / 'game.py').read_text()
    assert 'FORGE  IS  DEFEATED' not in src, (
        "the retired forge win message is still in game.py")
    assert '"YOU  WON!"' in src

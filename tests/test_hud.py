"""Unit tests for the HUD layout primitives (spec 0072 D3/D4).

Pure pygame-surface tests — no Game, no Harness driving.  Importing the
harness module here only to inherit its dummy SDL video/audio drivers so
pygame is initialised headlessly.
"""
import pygame

from tests import harness  # noqa: F401  (side effect: headless pygame.init)
from hud import HudElement, LabelValue, IconStrip, HBox


def _font():
    return pygame.font.Font(None, 16)


def _elt(w, h=20):
    return HudElement(pygame.Surface((w, h), pygame.SRCALPHA))


# ── LabelValue ────────────────────────────────────────────────────────────────

def test_labelvalue_width_matches_rendered_text():
    f = _font()
    col = (255, 255, 255)
    lv = LabelValue(f, "SCORE", "  1234", col)
    assert lv.width == f.render("SCORE   1234", True, col).get_width()


def test_labelvalue_label_only_when_value_empty():
    f = _font()
    col = (255, 0, 255)
    lv = LabelValue(f, "BOSS", "", col)
    assert lv.width == f.render("BOSS", True, col).get_width()


# ── HBox even-gap layout ──────────────────────────────────────────────────────

def test_hbox_positions_span_margins_with_equal_gaps():
    elems = [_elt(100), _elt(80), _elt(60), _elt(40)]
    box = HBox(960, margin=10)
    xs = box.positions(elems)
    assert xs[0] == 10                                   # first at margin
    assert round(xs[-1] + elems[-1].width) == 960 - 10   # last ends at width-margin
    gaps = [xs[i + 1] - (xs[i] + elems[i].width) for i in range(len(elems) - 1)]
    assert max(gaps) - min(gaps) < 1e-6                  # gaps equal


def test_hbox_single_element_no_division_by_zero():
    box = HBox(960, margin=10)
    xs = box.positions([_elt(100)])
    assert xs == [10.0]


def test_hbox_blit_smoke():
    target = pygame.Surface((960, 28), pygame.SRCALPHA)
    HBox(960, margin=10).blit(target, [_elt(100), _elt(80)], 0, 28)  # must not raise

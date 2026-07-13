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


# ── HBox gap bands (spec 0072 D4) ─────────────────────────────────────────────

GAP = (18, 18, 26)
INSET = 6


def _band_columns(box, elements, row_h=28):
    """Render onto a black surface and, per inter-element gap, report whether
    its whole vertical extent at the gap midpoint is filled with GAP."""
    target = pygame.Surface((box.width, row_h))
    target.fill((0, 0, 0))
    box.blit(target, elements, 0, row_h)
    xs = box.positions(elements)
    cols = []
    for i in range(len(elements) - 1):
        mid = round((xs[i] + elements[i].width + xs[i + 1]) / 2)
        full = all(target.get_at((mid, y))[:3] == GAP for y in range(row_h))
        cols.append(full)
    return cols


def test_hbox_fills_every_inner_gap_full_height():
    elems = [_elt(100), _elt(80), _elt(60)]
    box = HBox(960, margin=10, gap_color=GAP)
    cols = _band_columns(box, elems)
    assert cols == [True, True]                       # both gaps filled, full height


def test_hbox_no_band_when_gap_color_none():
    elems = [_elt(100), _elt(80), _elt(60)]
    box = HBox(960, margin=10, gap_color=None)
    assert _band_columns(box, elems) == [False, False]


def test_hbox_band_does_not_paint_outer_margins():
    """The band fills only inter-element gaps, never the outer margins."""
    elems = [_elt(100), _elt(80)]
    box = HBox(960, margin=10, gap_color=GAP)
    target = pygame.Surface((box.width, 28))
    target.fill((0, 0, 0))
    box.blit(target, elems, 0, 28)
    assert target.get_at((2, 14))[:3] == (0, 0, 0)            # left margin: unpainted
    assert target.get_at((box.width - 3, 14))[:3] == (0, 0, 0)  # right margin: unpainted


def test_hbox_band_is_inset_from_element_edges():
    """The band is inset gap_inset px from each element: the strip right next to
    an element edge stays background, and the band begins after the inset."""
    elems = [_elt(100), _elt(80)]
    box = HBox(960, margin=10, gap_color=GAP, gap_inset=INSET)
    target = pygame.Surface((box.width, 28))
    target.fill((0, 0, 0))
    box.blit(target, elems, 0, 28)
    xs = box.positions(elems)
    left_edge = round(xs[0] + elems[0].width)
    right_edge = round(xs[1])
    assert target.get_at((left_edge + 1, 14))[:3] == (0, 0, 0)          # inset: blank
    assert target.get_at((left_edge + INSET + 1, 14))[:3] == GAP        # band begun
    assert target.get_at((right_edge - INSET - 1, 14))[:3] == GAP       # band still on
    assert target.get_at((right_edge - 1, 14))[:3] == (0, 0, 0)         # inset: blank


def test_hbox_band_skips_gap_too_narrow_for_inset():
    """A gap narrower than 2*inset draws no band."""
    elems = [_elt(468), _elt(468)]   # gap = 960-20-936 = 4 < 2*6 -> skipped
    box = HBox(960, margin=10, gap_color=GAP, gap_inset=INSET)
    assert _band_columns(box, elems) == [False]

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


# ── HBox gap separators (spec 0072 D4) ────────────────────────────────────────

SEP = (80, 80, 96)


def _count_gap_lines(box, elements, row_h=28):
    """Render onto a black surface and count gaps that received a SEP line by
    probing each gap's midpoint at the centre row."""
    target = pygame.Surface((box.width, row_h))
    target.fill((0, 0, 0))
    box.blit(target, elements, 0, row_h)
    xs = box.positions(elements)
    cy = row_h // 2
    hits = 0
    for i in range(len(elements) - 1):
        mid = round((xs[i] + elements[i].width + xs[i + 1]) / 2)
        if target.get_at((mid, cy))[:3] == SEP:
            hits += 1
    return hits


def test_hbox_draws_one_line_per_inner_gap():
    elems = [_elt(100), _elt(80), _elt(60)]
    box = HBox(960, margin=10, sep_color=SEP)
    assert _count_gap_lines(box, elems) == len(elems) - 1     # exactly n-1 lines


def test_hbox_no_lines_when_sep_color_none():
    elems = [_elt(100), _elt(80), _elt(60)]
    box = HBox(960, margin=10, sep_color=None)
    assert _count_gap_lines(box, elems) == 0


def test_hbox_separator_vertically_centred_and_inset():
    """The line sits on the centre row and stays inside the gap minus inset:
    just past the left element's edge is background, the gap midpoint is lit."""
    elems = [_elt(100), _elt(80)]
    box = HBox(960, margin=10, sep_color=SEP, sep_inset=6)
    target = pygame.Surface((box.width, 28))
    target.fill((0, 0, 0))
    box.blit(target, elems, 0, 28)
    xs = box.positions(elems)
    cy = 28 // 2
    left_edge = round(xs[0] + elems[0].width)
    assert target.get_at((left_edge + 1, cy))[:3] == (0, 0, 0)     # inset gap: blank
    assert target.get_at((left_edge + 6, cy))[:3] == SEP           # line has begun


def test_hbox_skips_gap_narrower_than_sep_min():
    """A gap too small to hold a line (after insets) draws nothing there."""
    # Fill almost all the width so the single gap is tiny.
    elems = [_elt(460), _elt(460)]
    box = HBox(960, margin=10, sep_color=SEP, sep_inset=6, sep_min=4)
    # gap = 960 - 20 - 920 = 20; span = 20 - 12 = 8 >= 4 -> drawn; shrink further:
    elems = [_elt(465), _elt(465)]   # gap = 10, span = 10-12 = -2 < 4 -> skipped
    assert _count_gap_lines(box, elems) == 0

"""HUD layout primitives — a tiny GUI-toolkit-style horizontal box (spec 0072).

The status line is a row of elements, each of which reports its own tight
width; an ``HBox`` lays them out left-to-right and distributes the leftover
horizontal space evenly across the ``n-1`` inter-element gaps.  This replaces
the old ``_render_hud`` machinery that built ``(text, colour)`` tuples and then
spliced the key-strip surface in by a hard-coded index.

Everything here is presentation (pygame) code, parallel to ``sprites.py``.
``LabelValue`` covers the dominant ``LABEL value`` element; ``IconStrip`` is the
key tracker; conditional elements are simply omitted from the element list
handed to the box — there is no ``None`` sentinel and no magic index.
"""
import re

import pygame

from constants import HUD_TEXT

_SPACE_RUN = re.compile(r' {3,}')


def dash_fill(s):
    """Turn padding runs into dash leaders, **preserving length** (spec 0072).

    Any run of > 2 spaces becomes ``" " + "-"*(n-2) + " "`` — one space, the
    padding as dashes, one space — so a right-justified value stays linked to its
    label (``SCORE ----- 0``) without changing the (monospace) width, i.e. no
    reflow. A remaining trailing space then becomes a ``-`` (so left-justified
    padding like ``SEEK: Coin␣␣␣`` reads ``SEEK: Coin ----``). Runs of ≤ 2 spaces
    (e.g. ``LEVEL  1``) are left alone."""
    s = _SPACE_RUN.sub(lambda m: ' ' + '-' * (len(m.group(0)) - 2) + ' ', s)
    if s.endswith(' '):
        s = s[:-1] + '-'
    return s


class HudElement:
    """One HUD item.  Owns a pre-rendered surface and reports its tight width.

    Subclasses build the surface in ``__init__`` and call ``super().__init__``.
    """

    def __init__(self, surface):
        self.surface = surface

    @property
    def width(self):
        return self.surface.get_width()

    def blit(self, target, x, top, row_h):
        """Blit at ``x``, vertically centred by our own height in the row."""
        cy = top + (row_h - self.surface.get_height()) // 2
        target.blit(self.surface, (round(x), cy))


class LabelValue(HudElement):
    """The dominant ``LABEL value`` element (single colour).

    Renders ``f"{label} {value}"`` (tidied by :func:`dash_fill`), or just
    ``label`` when ``value`` is "". Fixed-width value padding stays the caller's
    responsibility via format strings.

    ``tail_block`` appends a drawn **lower-half block** one character wide after
    the text — the HUD font has no block-drawing glyph, so it is rendered as a
    filled rectangle in the lower half of the line (spec 0072: half an earned
    credit / half a bridge).
    """

    def __init__(self, font, label, value="", color=HUD_TEXT, tail_block=False):
        text = dash_fill(f"{label} {value}" if value != "" else label)
        surf = font.render(text, True, color)
        if tail_block:
            adv = font.size('0')[0]
            h = surf.get_height()
            comp = pygame.Surface((surf.get_width() + adv, h), pygame.SRCALPHA)
            comp.blit(surf, (0, 0))
            pygame.draw.rect(comp, color,
                             (surf.get_width() + 1, h // 2, adv - 2, h - h // 2))
            surf = comp
        super().__init__(surf)


class IconStrip(HudElement):
    """A row of fixed-width icon slots (the key tracker).

    ``icons`` is a list of ``(surface, lit)`` pairs.  A ``lit`` icon is drawn at
    full opacity; a non-``lit`` one is ghosted to ``ghost_alpha`` (the icons
    carry per-pixel alpha, so a BLEND_RGBA_MULT fill on a copy is used —
    ``set_alpha`` would be ignored).  Width is ``slot_w * len(icons)`` so the
    strip never reflows as icons light up or dim.
    """

    def __init__(self, icons, slot_w, icon_h, ghost_alpha):
        surface = pygame.Surface((slot_w * len(icons), icon_h), pygame.SRCALPHA)
        for i, (icon, lit) in enumerate(icons):
            if not lit:
                icon = icon.copy()
                icon.fill((255, 255, 255, ghost_alpha),
                          special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(icon, (i * slot_w, 0))
        super().__init__(surface)


def _compose_key_stack(lit, ghost, total, held, offset=2):
    """Overlay `total` key icons down-right at `index*offset` px (spec 0075).

    Loop index 0..total-1: draw a ghost key while ``total - held > index``
    (the back keys), else a normal key.  Higher indices are drawn last, so the
    `held` keys land on top, in front (bottom-right); un-held ghosts recede
    up-left behind, barely visible.  Icons carry their own rim/alpha.
    """
    iw, ih = lit.get_size()
    span = offset * (total - 1)
    surf = pygame.Surface((iw + span, ih + span), pygame.SRCALPHA)
    for index in range(total):
        icon = ghost if (total - held) > index else lit
        surf.blit(icon, (index * offset, index * offset))
    return surf


class KeyStackStrip(HudElement):
    """The HUD key tracker: one stacked-key slot per colour present in a level.

    ``entries`` is a list of ``(lit_icon, ghost_icon, total, held)`` — ``total``
    keys of that colour exist in the level, ``held`` are in hand.  Each stack is
    **centred** (both axes) on where a single icon would sit in its slot (pitch
    ``slot_w``, matching :class:`IconStrip`), so growing the stack stays centred
    on the icon rather than drifting down-right.  The strip width is the current
    per-colour pitch plus the widest stack's overhang (a stack of up to 4 keys is
    a few px wider than a single slot), split evenly as side padding; it stays
    constant during play (``total`` is fixed per level).
    """

    def __init__(self, entries, slot_w, offset=2):
        stacks = [_compose_key_stack(l, g, t, h, offset) for (l, g, t, h) in entries]
        if not stacks:
            super().__init__(pygame.Surface((0, 0), pygame.SRCALPHA))
            return
        iw, ih = entries[0][0].get_size()   # single-icon size (all icons equal)
        totals = [t for (_l, _g, t, _h) in entries]
        max_span = offset * (max(totals) - 1)
        pad = (max_span + 1) // 2           # keeps the widest stack from clipping
        surf_w = 2 * pad + (len(stacks) - 1) * slot_w + iw
        surf_h = ih + 2 * pad
        surface = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cy = surf_h // 2
        for i, s in enumerate(stacks):
            # centre each stack on where a single icon would sit in its slot,
            # so growing the stack stays centred instead of drifting down-right
            cx = pad + i * slot_w + iw // 2
            surface.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2))
        super().__init__(surface)


class HBox:
    """Lay elements out horizontally, distributing slack across the gaps.

    ``blit`` places each element left-to-right starting at ``margin`` and spreads
    the leftover width evenly across the ``n-1`` inter-element gaps (the same
    even-spacing the old HUD computed).  When ``gap_color`` is given, each
    inter-element gap is filled with a full-height rectangle of that colour,
    inset ``gap_inset`` px from the flanking elements — a subtle brighter band
    that separates elements without the visual noise of a line (spec 0072 D4).
    The outer margins are never filled, and a gap too narrow for the inset draws
    nothing.
    """

    def __init__(self, width, margin=10, gap_color=None, gap_inset=6):
        self.width = width
        self.margin = margin
        self.gap_color = gap_color
        self.gap_inset = gap_inset

    def positions(self, elements):
        """Left-edge x offset of each element under even-gap layout.

        The leftover width after the tight element widths is spread evenly
        across the ``n-1`` gaps; the first element sits at ``margin`` and the
        last ends at ``width - margin``.
        """
        tight = sum(e.width for e in elements)
        gap = (self.width - 2 * self.margin - tight) / max(len(elements) - 1, 1)
        xs = []
        x = float(self.margin)
        for e in elements:
            xs.append(x)
            x += e.width + gap
        return xs

    def blit(self, target, elements, top, row_h):
        if not elements:
            return
        xs = self.positions(elements)
        # Gap bands first (behind), then the elements on top.
        if self.gap_color is not None:
            for i in range(len(elements) - 1):
                gx0 = round(xs[i] + elements[i].width + self.gap_inset)
                gx1 = round(xs[i + 1] - self.gap_inset)
                if gx1 > gx0:
                    target.fill(self.gap_color, (gx0, top, gx1 - gx0, row_h))
        for e, x in zip(elements, xs):
            e.blit(target, x, top, row_h)

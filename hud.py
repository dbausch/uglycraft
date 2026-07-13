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
import pygame

from constants import HUD_TEXT


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

    Renders ``f"{label} {value}"``, or just ``label`` when ``value`` is "".
    Fixed-width value padding (fields that must not reflow) stays the caller's
    responsibility via format strings, exactly as the old HUD did.
    """

    def __init__(self, font, label, value="", color=HUD_TEXT):
        text = f"{label} {value}" if value != "" else label
        super().__init__(font.render(text, True, color))


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

# Backlog

Ideas recorded for future consideration.  None of these are planned or
scheduled; they need a spec before any implementation begins.

---

## Generalised corridor construction

All corridor shapes can be derived from a single generative model:

1. Start with one arm orthogonal to a border side, at any position along that
   border.  The arm has a variable length.
2. The arm can **end** (dead-end corridor) or continue:
   - Extend straight to the **opposite border** → straight corridor
   - **Turn left or right** to meet one of the borders parallel to the first
     arm → L-shape
3. The turned segment can be **shorter** (not reaching its border), allowing a
   second turn back toward the original direction → Z/S-shape
4. Add a **third arm** branching off the main stroke → T-shape
5. Add a **fourth arm** → double-T; the two stems may be aligned or offset

One parametrised algorithm that generates the corridor floor tiles and derives
all zone boundaries from the arm positions and lengths could replace the
current family of separate `_layout_*` functions.

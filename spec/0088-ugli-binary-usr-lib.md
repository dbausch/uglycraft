# Spec 0088 — Install the UGLI_2 binary under `/usr/lib/ugli` (BL-68)

The compiled `UGLI_2` ELF executable is installed to
`/usr/share/ugli/UGLI_2`. `/usr/share` is for architecture-independent data;
a private, wrapper-invoked binary idiomatically belongs in `/usr/lib/ugli/`.
namcap flags the current placement ("ELF file in /usr/share"). Move the
binary; the data files stay.

→ Audit: `kb/arch-packaging.md` (P3 section). → Backlog: BL-68.
→ `.SRCINFO` regeneration mechanism: spec 0084 (no metadata change expected —
the install path lives in function bodies; regenerate-and-diff to confirm).

## Status checklist

- [ ] **D1** — all three PKGBUILDs (`packaging/PKGBUILD`, `PKGBUILD-git`,
  `PKGBUILD-dev`) install the binary to `/usr/lib/ugli/UGLI_2` in their
  `package_ugli*()` functions (currently
  `install -Dm755 original/UGLI_2 "$pkgdir/usr/share/ugli/UGLI_2"`,
  `PKGBUILD:82` / `PKGBUILD-git:86` / the `-dev` equivalent).
- [ ] **D2** — `packaging/ugli.sh` line 2 becomes
  `UGLI=/usr/lib/ugli/UGLI_2`. Everything else in the wrapper is untouched —
  in particular the two `-c /usr/share/ugli/ANSI-87.conf` kitty arguments,
  because the theme stays in `/usr/share/ugli`.
- [ ] **D3** — data files stay where they are: `ANSI-87.conf` and
  `translations/` (`.mo` + `history_*.txt`) remain under `/usr/share/ugli/`.
- [ ] **D4** — verified: `poe package-dev` builds; the `ugli-dev` package tree
  has `usr/lib/ugli/UGLI_2` (mode 755) and **no** ELF under `usr/share/`;
  namcap no longer emits the ELF-in-/usr/share warning; the extracted wrapper
  script's `UGLI=` path agrees with the installed binary location. A real
  launch check (the game opens in a terminal) is user acceptance.
- [ ] **D5** — regenerated `.SRCINFO`/`.SRCINFO-git` (spec 0084) show **no**
  diff — confirming this is a function-body-only change.

## Background — confirmed facts

- The wrapper (`packaging/ugli.sh`, installed as `/usr/bin/ugli`) hardcodes
  `UGLI=/usr/share/ugli/UGLI_2` on line 2 and references
  `/usr/share/ugli/ANSI-87.conf` twice for the kitty launcher — only the
  `UGLI=` line moves.
- The game finds its translations relative to its own binary? **No** — the
  wrapper `cd`s into `$XDG_DATA_HOME/ugli` for the high-score file, and the
  FPC binary locates `translations/` relative to the **executable path**
  (`/usr/lib/ugli/translations` after the move) — this must be checked at
  implementation time: if `UGLI_2` resolves translations relative to its own
  location rather than a compiled-in path, the `translations/` install must
  move along with it (adjust D3 accordingly and record which way it went).
  This is the one open question; resolve it by reading
  `original/UGLI_2.pp`'s translation-path logic (or `original/CLAUDE.md`)
  before touching the install lines.

## Done when:

- [ ] **D1** — binary installed to `/usr/lib/ugli/UGLI_2` in all three
  PKGBUILDs.
- [ ] **D2** — `ugli.sh` points at the new path.
- [ ] **D3** — data files' location settled per the translation-path check
  (stay in `/usr/share/ugli`, or documented move).
- [ ] **D4** — dev-package tree + namcap verified; launch check by Daniel.
- [ ] **D5** — `.SRCINFO` regeneration shows no metadata diff.

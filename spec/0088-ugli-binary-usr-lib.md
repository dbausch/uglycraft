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

- [x] **D1** — all three PKGBUILDs (`packaging/PKGBUILD`, `PKGBUILD-git`,
  `PKGBUILD-dev`) install the binary to `/usr/lib/ugli/UGLI_2` in their
  `package_ugli*()` functions (currently
  `install -Dm755 original/UGLI_2 "$pkgdir/usr/share/ugli/UGLI_2"`,
  `PKGBUILD:82` / `PKGBUILD-git:86` / the `-dev` equivalent). — b49b587
- [x] **D2** — `packaging/ugli.sh` line 2 becomes
  `UGLI=/usr/lib/ugli/UGLI_2`. Everything else in the wrapper is untouched —
  in particular the two `-c /usr/share/ugli/ANSI-87.conf` kitty arguments,
  because the theme stays in `/usr/share/ugli`. — b49b587
- [x] **D3** — resolved: `translations/` (`.mo` + `history_*.txt`) **moves**
  with the binary to `/usr/lib/ugli/translations/`, because the FPC binary
  locates it relative to its own executable path (`ParamStr(0)`), not a
  compiled-in `/usr/share` path. `ANSI-87.conf` **stays** under
  `/usr/share/ugli/` — it is never read by the Pascal binary, only passed by
  `packaging/ugli.sh` to kitty via `-c /usr/share/ugli/ANSI-87.conf`. —
  b49b587
- [ ] **D4** — verified: `poe package-dev` builds; the `ugli-dev` package tree
  has `usr/lib/ugli/UGLI_2` (mode 755), `usr/lib/ugli/translations/*.mo` and
  `usr/lib/ugli/translations/history_*.txt`, `usr/share/ugli/ANSI-87.conf`,
  and **no** ELF or other files under `usr/share/ugli/` besides
  `ANSI-87.conf`; namcap no longer emits the ELF-in-/usr/share warning; the
  extracted wrapper script's `UGLI=` path agrees with the installed binary
  location. A real launch check (the game opens in a terminal) is user
  acceptance. — package tree, mode, and wrapper-path checks all confirmed
  (see Background); additionally, running the extracted binary from an
  unrelated CWD (`/tmp`) with `LANGUAGE=de LANG=de_DE.UTF-8` produced fully
  German `--help` output, positively proving the `ExeDir`-relative
  translation lookup finds `usr/lib/ugli/translations/de.mo` in its new
  location (confirmed no other XDG locale path on this machine could have
  supplied it). namcap half now confirmed: built user-locally in a venv (pip
  install of pyalpm/pyelftools/license-expression + the namcap sources
  themselves against the system's libalpm, no system-wide install) and run
  against `ugli-dev-1.5.r696.ga9f6282-1-x86_64.pkg.tar.zst` — no
  ELF-outside-allowed-dirs error (namcap's `elfpaths` rule allows
  `usr/lib/` but not `usr/share/`, and `UGLI_2` is now under `usr/lib/ugli/`);
  the only ELF-related output was pre-existing, unrelated `lacks FULL RELRO`
  / `lacks PIE` warnings (compiler-flag hardening, out of scope for this
  spec). The real terminal launch check is user acceptance and stays open.
- [x] **D5** — regenerated `.SRCINFO`/`.SRCINFO-git` (spec 0084) show **no**
  diff — confirming this is a function-body-only change. — b49b587

## Background — confirmed facts

- The wrapper (`packaging/ugli.sh`, installed as `/usr/bin/ugli`) hardcodes
  `UGLI=/usr/share/ugli/UGLI_2` on line 2 and references
  `/usr/share/ugli/ANSI-87.conf` twice for the kitty launcher — only the
  `UGLI=` line moves.
- **Resolved** — the game finds its translations relative to its own binary:
  **yes**. A read-only research pass into `original/UGLI_2_Core.inc` confirmed
  both `LoadTranslation` (lines 1978–2007) and `LoadHistoryText` (lines
  1524–1568) build their file paths as `ExeDir + 'translations/...'`, i.e.
  relative to `ParamStr(0)`, the binary's own executable path — not a
  compiled-in `/usr/share` constant. The wrapper's `cd` into
  `$XDG_DATA_HOME/ugli` only affects the high-score file (CWD-relative,
  unaffected by this move); `ExeDir` tracks wherever the binary itself lives.
  Therefore `translations/` **moves with the binary** to
  `/usr/lib/ugli/translations/`, while `ANSI-87.conf` — read only by the
  wrapper script, never by the FPC binary — **stays** under
  `/usr/share/ugli/`. This was the one open question and it is now settled;
  no Pascal source change was needed.

## Done when:

- [x] **D1** — binary installed to `/usr/lib/ugli/UGLI_2` in all three
  PKGBUILDs. — b49b587
- [x] **D2** — `ugli.sh` points at the new path. — b49b587
- [x] **D3** — data files' location settled per the translation-path check:
  `translations/` moves to `/usr/lib/ugli/translations/`, `ANSI-87.conf` stays
  in `/usr/share/ugli/`. — b49b587
- [ ] **D4** — dev-package tree, mode, and wrapper-path confirmed; the
  `ExeDir`-relative translation lookup was positively verified by running the
  extracted binary from an unrelated CWD with a forced German locale and
  seeing translated `--help` output. namcap half now confirmed clean (built
  user-locally in a venv, no ELF-in-/usr/share warning); the real terminal
  launch check is user acceptance and stays open.
- [x] **D5** — `.SRCINFO` regeneration shows no metadata diff. — b49b587

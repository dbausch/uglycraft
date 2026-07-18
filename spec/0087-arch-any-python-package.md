# Spec 0087 — `arch=('any')` for the pure-Python uglycraft split packages (BL-67)

The `uglycraft` split package is pure Python (no C extensions; sprites are
drawn procedurally, sound is numpy-generated) and therefore
architecture-independent, but inherits `arch=('x86_64')` from pkgbase. `arch`
is overridable per split package — declare `any` so the package installs on
aarch64 etc., while the compiled-FPC `ugli` packages correctly stay `x86_64`.

→ Audit: `kb/arch-packaging.md` (P3 section). → Backlog: BL-67.
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [x] **D1** — `arch=('any')` added inside `package_uglycraft()`
  (`packaging/PKGBUILD`), `package_uglycraft-git()` (`PKGBUILD-git`), and
  `package_uglycraft-dev()` (`PKGBUILD-dev`). — c7b4e7a
- [x] **D2** — pkgbase-level `arch=('x86_64')` stays in all three (the pkgbase
  array must cover every arch any split member needs; `ugli*` are compiled
  x86_64 ELF binaries). — c7b4e7a; confirmed by diff (pkgbase-level `arch=`
  lines untouched in all three files).
- [x] **D3** — `ugli` / `ugli-git` / `ugli-dev` split packages unchanged
  (implicit x86_64 from pkgbase). — c7b4e7a; confirmed by diff and by the
  built `ugli-dev` package's `.PKGINFO` showing `arch = x86_64`.
- [x] **D4** — `.SRCINFO` and `.SRCINFO-git` regenerated (spec 0084) in the
  same commit; the `pkgname = uglycraft`(`-git`) sections show `arch = any`.
  — c7b4e7a; `makepkg --printsrcinfo` diffs for both PKGBUILDs showed exactly
  one added `arch = any` line each, nothing else.
- [x] **D5** — verified: `poe package-dev` produces
  `uglycraft-dev-…-any.pkg.tar.zst` alongside the x86_64 `ugli-dev` package;
  both build from one `makepkg` run; the extracted `any` package still runs the
  headless `--dump-level` check. namcap raises no arch-related warning on the
  `uglycraft` package. — build produced
  `uglycraft-dev-1.5.r690.gc7b4e7a-1-any.pkg.tar.zst` (`.PKGINFO`: `arch =
  any`) and `ugli-dev-1.5.r690.gc7b4e7a-1-x86_64.pkg.tar.zst` from the same
  `makepkg -p PKGBUILD-dev -f` run; extracting the `any` package and running
  `SDL_VIDEODRIVER=dummy PYTHONPATH=<site-packages> python3 -m uglycraft
  --dump-level 1 --seed 42` produced a correct ASCII level dump. namcap not
  installed on this machine, so the namcap half is unverified.

## Background — confirmed facts

- `arch=('x86_64')` at pkgbase level: `PKGBUILD:5`, `PKGBUILD-git:5`,
  `PKGBUILD-dev:11`; no per-package override anywhere.
- The installed `uglycraft` tree is `.py` sources + byte-compiled `.pyc`
  + a `.ttf` + a `.txt` — nothing architecture-specific. Its runtime deps
  (`python`, `python-pygame`, `python-numpy`) carry the native code.
- One subtlety: byte-compiled `.pyc` files are tied to the **Python version**
  (cpython-3.14 magic), not the architecture — that is already the case today
  and is unchanged by this spec (the package pins no Python version; a Python
  major bump on Arch triggers a rebuild via the usual rebuild machinery, same
  as for any `any` Python package).
- makepkg names split packages per their own `arch`; the `uglycraft` artifact
  becomes `…-any.pkg.tar.zst`.

## Done when:

- [x] **D1–D3** — override present in the three `package_uglycraft*()`
  functions; pkgbase arrays and `ugli*` packages untouched. — c7b4e7a
- [x] **D4** — both `.SRCINFO` files regenerated in the same commit. — c7b4e7a
- [ ] **D5** — one `poe package-dev` run yields an `any` uglycraft-dev package
  and an x86_64 ugli-dev package; headless run from the extracted `any`
  package passes; namcap clean on this point. — package build, arch check, and
  headless `--dump-level` run all confirmed; namcap not installed on this
  machine, so only the namcap half is unverified.

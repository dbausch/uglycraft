# Spec 0087 — `arch=('any')` for the pure-Python uglycraft split packages (BL-67)

The `uglycraft` split package is pure Python (no C extensions; sprites are
drawn procedurally, sound is numpy-generated) and therefore
architecture-independent, but inherits `arch=('x86_64')` from pkgbase. `arch`
is overridable per split package — declare `any` so the package installs on
aarch64 etc., while the compiled-FPC `ugli` packages correctly stay `x86_64`.

→ Audit: `kb/arch-packaging.md` (P3 section). → Backlog: BL-67.
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [ ] **D1** — `arch=('any')` added inside `package_uglycraft()`
  (`packaging/PKGBUILD`), `package_uglycraft-git()` (`PKGBUILD-git`), and
  `package_uglycraft-dev()` (`PKGBUILD-dev`).
- [ ] **D2** — pkgbase-level `arch=('x86_64')` stays in all three (the pkgbase
  array must cover every arch any split member needs; `ugli*` are compiled
  x86_64 ELF binaries).
- [ ] **D3** — `ugli` / `ugli-git` / `ugli-dev` split packages unchanged
  (implicit x86_64 from pkgbase).
- [ ] **D4** — `.SRCINFO` and `.SRCINFO-git` regenerated (spec 0084) in the
  same commit; the `pkgname = uglycraft`(`-git`) sections show `arch = any`.
- [ ] **D5** — verified: `poe package-dev` produces
  `uglycraft-dev-…-any.pkg.tar.zst` alongside the x86_64 `ugli-dev` package;
  both build from one `makepkg` run; the extracted `any` package still runs the
  headless `--dump-level` check. namcap raises no arch-related warning on the
  `uglycraft` package.

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

- [ ] **D1–D3** — override present in the three `package_uglycraft*()`
  functions; pkgbase arrays and `ugli*` packages untouched.
- [ ] **D4** — both `.SRCINFO` files regenerated in the same commit.
- [ ] **D5** — one `poe package-dev` run yields an `any` uglycraft-dev package
  and an x86_64 ugli-dev package; headless run from the extracted `any`
  package passes; namcap clean on this point.

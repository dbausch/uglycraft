# Spec 0085 — Drop redundant `provides=($pkgname)` from the release PKGBUILD (BL-62)

Arch guideline: *"Do not add `$pkgname` to provides, as it is always implicitly
provided."* The release PKGBUILD violates this in both split packages; the
`-git` and `-dev` variants do **not** (there the provided name differs from
`$pkgname`) and must stay untouched.

→ Audit: `kb/arch-packaging.md` (P2 section). → Backlog: BL-62.
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [x] **D1** — `packaging/PKGBUILD`: delete `provides=('uglycraft')` from
  `package_uglycraft()` (line 41) and `provides=('ugli')` from `package_ugli()`
  (line 75). The `conflicts=('uglycraft-git')` / `conflicts=('ugli-git')` lines
  stay. — 96a60f2
- [x] **D2** — `PKGBUILD-git` and `PKGBUILD-dev` are **unchanged** (their
  `provides=('uglycraft')`/`provides=('ugli')` are correct and load-bearing:
  `$pkgname` there is `uglycraft-git`/`-dev` etc., so providing the plain name
  is what lets them satisfy dependencies on it and pair with their
  `conflicts`). — 96a60f2 verified: `git status --short packaging/` showed only
  `PKGBUILD`/`.SRCINFO` modified, `PKGBUILD-git`/`PKGBUILD-dev` untouched.
- [x] **D3** — `packaging/.SRCINFO` regenerated (spec 0084 mechanism) and
  committed in the same commit; the two `provides =` lines disappear from it.
  — 96a60f2; `makepkg --printsrcinfo | diff - .SRCINFO` showed exactly
  `provides = uglycraft` and `provides = ugli` removed, nothing else.
- [ ] **D4** — verified: `namcap` on the PKGBUILD raises no provides-related
  warning; a `poe package-dev`-style build is *not* needed (the release
  PKGBUILD builds from the GitHub tag — metadata-only change, verified via
  `.SRCINFO` diff + namcap). — **namcap is not installed on this machine**
  (`pacman -Q namcap` → not found) and was not installed per the no-system-wide-
  install constraint, so the namcap half of D4 is unverified. The `.SRCINFO`
  diff half is confirmed (see D3).

## Background — confirmed facts

Current lines (verified 2026-07-18):

- `PKGBUILD:41` `provides=('uglycraft')` inside `package_uglycraft()` where
  `$pkgname` **is** `uglycraft` → redundant.
- `PKGBUILD:75` `provides=('ugli')` inside `package_ugli()` where `$pkgname`
  **is** `ugli` → redundant.
- `PKGBUILD-git:45,79` and `PKGBUILD-dev:52,86` provide the non-`$pkgname`
  plain names → correct, keep.

## Done when:

- [x] **D1** — the two redundant `provides` lines are gone from `PKGBUILD`.
  — 96a60f2
- [x] **D2** — `-git`/`-dev` PKGBUILDs untouched. — 96a60f2
- [x] **D3** — `.SRCINFO` regenerated in the same commit. — 96a60f2
- [ ] **D4** — namcap clean on this point; `.SRCINFO` diff shows exactly the
  two `provides` lines removed. — `.SRCINFO` diff half confirmed (96a60f2);
  namcap not installed on this machine, so the namcap half is unverified.

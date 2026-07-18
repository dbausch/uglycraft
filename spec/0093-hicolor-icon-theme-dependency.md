# Spec 0093 — hicolor-icon-theme dependency for the icon-installing split packages (BL-73)

namcap flags: `Dependency hicolor-icon-theme detected and not included
(needed for hicolor theme hierarchy)` on the `uglycraft` package. All four
split packages (`uglycraft`, `ugli`, and their `-git` equivalents; `-dev`
too, for consistency) install a `.svg` under
`/usr/share/icons/hicolor/scalable/apps/` but none declares a `depends` on
`hicolor-icon-theme`, the package that owns that directory hierarchy and its
`gtk-update-icon-cache` trigger.

→ Audit: `kb/arch-packaging.md` ("Operational notes for the first push",
BL-72–BL-74). → Backlog: BL-73.
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [x] **D1** — `hicolor-icon-theme` added to `depends` of
  `package_uglycraft()` and `package_ugli()` in `packaging/PKGBUILD`.
- [x] **D2** — same addition to `package_uglycraft-git()` and
  `package_ugli-git()` in `packaging/PKGBUILD-git`.
- [x] **D3** — same addition to `package_uglycraft-dev()` and
  `package_ugli-dev()` in `packaging/PKGBUILD-dev`, for consistency (never
  deployed, but should not drift from the other two).
- [x] **D4** — `.SRCINFO` and `.SRCINFO-git` regenerated (spec 0084
  mechanism) to reflect the new `depends` entries.
- [x] **D5** — verified: `namcap` run against the built packages (via `poe
  package-dev`) no longer emits the `hicolor-icon-theme` finding; `poe
  package-dev` still builds successfully.
- [x] **D6** — `hicolor-icon-theme` also added to pkgbase-level `makedepends`
  in all three PKGBUILDs — required by namcap's `SplitPkgMakedepsRule` (see
  spec 0092): a subpackage `depends` entry must be covered by the pkgbase
  `makedepends` closure; discovered during implementation when the D1–D3
  edits re-triggered the split-makedeps error.

## Background — confirmed facts

- namcap's finding text: `Dependency hicolor-icon-theme detected and not
  included (needed for hicolor theme hierarchy)`. This comes from
  `Namcap.rules.pathdepends` (the built, installed-package analysis rule
  that scans a package's file list for well-known paths and requires a
  matching dependency; `pathdepends.py:19-27`): any file matching
  `^usr/share/icons/hicolor$` requires a `hicolor-icon-theme` dependency,
  tagged `hicolor-icon-theme-needed-for-hicolor-dir`. This package owns the
  hicolor directory tree and runs the `gtk-update-icon-cache` hook other
  tools rely on to pick up new icons.
- Verified against the already-built local packages
  (`packaging/uglycraft-dev-1.5.r703.ga369f7e-1-any.pkg.tar.zst` and
  `packaging/ugli-dev-1.5.r703.ga369f7e-1-x86_64.pkg.tar.zst`, gitignored
  build artifacts from a prior `poe package-dev` run): `namcap
  uglycraft-dev-*.pkg.tar.zst` reports the finding as an **error** (`E:
  Dependency hicolor-icon-theme detected and not included`) — `uglycraft`
  has no path to `hicolor-icon-theme` at all. `namcap ugli-dev-*.pkg.tar.zst`
  reports it only as a **warning** (`W: Dependency hicolor-icon-theme
  detected and implicitly satisfied but optional`) — `ugli`'s `optdepends`
  includes `kitty` (`PKGBUILD:76`), and `kitty` itself transitively
  depends on `hicolor-icon-theme`, so namcap's `getcovered()` traversal
  (see spec 0092's investigation of the same mechanism) finds the
  dependency already reachable through that *optional* dependency's own
  dependency tree. This transitive/optional path is not a substitute for an
  explicit `depends` entry — a user without `kitty` installed has no
  declared route to `hicolor-icon-theme` for `ugli` either — so the fix
  below still adds it explicitly to both `package_uglycraft*()` and
  `package_ugli*()` in all three PKGBUILDs, per the guideline that a package
  installing into a shared directory hierarchy must depend on the package
  that owns it, regardless of what happens to be installed already.
- All four split packages install an icon into that hierarchy:
  - `packaging/PKGBUILD:64-65` (`package_uglycraft`): `install -Dm644
    packaging/uglycraft.svg
    "$pkgdir/usr/share/icons/hicolor/scalable/apps/uglycraft.svg"`.
  - `packaging/PKGBUILD:94-95` (`package_ugli`): `install -Dm644
    packaging/ugli.svg
    "$pkgdir/usr/share/icons/hicolor/scalable/apps/ugli.svg"`.
  - `packaging/PKGBUILD-git:69-70` / `:100-101` — identical installs in
    `package_uglycraft-git()` / `package_ugli-git()`.
  - `packaging/PKGBUILD-dev:76-77` / `:107-108` — identical installs in
    `package_uglycraft-dev()` / `package_ugli-dev()`.
- None of the corresponding `depends`/`optdepends` arrays currently list
  `hicolor-icon-theme`:
  - `package_uglycraft()` (`PKGBUILD:44`): `depends=('python'
    'python-pygame' 'python-numpy')` — no icon-theme dependency.
  - `package_ugli()` (`PKGBUILD:75-77`): only `optdepends`
    (`portaudio`, `kitty`, `ttf-liberation`) — no `depends` array at all, and
    no icon-theme dependency.
  - Same absence in the `-git` (`PKGBUILD-git:48`, `:80-82`) and `-dev`
    (`PKGBUILD-dev:55`, `:87-89`) equivalents.
- `hicolor-icon-theme` is a small, near-universal desktop dependency (part of
  the `xdg-desktop-portal`/freedesktop stack that most graphical Arch systems
  already have installed via some other desktop package), so this is a
  correctness/guideline fix rather than a functional bug users are likely to
  hit in practice — but it is the correct, guideline-conformant dependency
  declaration and is what namcap checks for.
- `ugli` currently has no `depends` array at all (only `optdepends`), so
  adding this dependency introduces the array for that split package for the
  first time in `PKGBUILD`; `-git`/`-dev` are the same.
- **D6 — pkgbase-makedepends interaction, found during implementation.**
  After D1–D3 were committed (adding `hicolor-icon-theme` to each
  `package_*()` function's `depends`), a re-run of `namcap packaging/PKGBUILD`
  and `namcap packaging/PKGBUILD-git` produced a *new* instance of the same
  rule spec 0092 fixed for `python`/`python-numpy`/`python-pygame`: `E: Split
  PKGBUILD needs additional makedepends ['hicolor-icon-theme'] to work
  properly`. This is the identical mechanism spec 0092 documented in depth
  (`Namcap.rules.splitpkgbuild.SplitPkgMakedepsRule`,
  `Namcap/rules/splitpkgbuild.py:29-62`): the rule requires every name a
  subpackage lists in `depends`/`makedepends` to be reachable from the
  pkgbase-level `makedepends` array (directly, or via the transitive
  dependency closure `Namcap.depends.getcovered()` resolves against the local
  pacman database). Adding `hicolor-icon-theme` to the eight `package_*()`
  `depends` arrays satisfies the *packaging guideline* this spec exists to
  fix, but simultaneously creates a new entry in each subpackage's
  `local_deps` that pkgbase-level `makedepends` does not cover — so the same
  heuristic that spec 0092 silenced for the three Python packages fires again
  for this one. Empirically confirmed: temporarily appending
  `'hicolor-icon-theme'` to `packaging/PKGBUILD`'s pkgbase-level `makedepends`
  array and re-running namcap leaves only the expected benign findings
  (`Missing Maintainer tag`, `description contains name`) — the split-makedeps
  finding is fully silenced by the one-line addition, mirroring spec 0092's
  own verified fix exactly. D6 applies that same addition permanently to all
  three PKGBUILDs.

## The fix

Add `depends=('hicolor-icon-theme')` (or append to an existing `depends`
array) inside each of the eight `package_*()` functions across the three
PKGBUILDs:

- `package_uglycraft()` — extend the existing `depends` array:
  `depends=('python' 'python-pygame' 'python-numpy' 'hicolor-icon-theme')`.
- `package_ugli()` — add a new `depends=('hicolor-icon-theme')` array
  (alongside the existing `optdepends`).
- Same two edits, mechanically identical, in `package_uglycraft-git()` /
  `package_ugli-git()` (`PKGBUILD-git`) and `package_uglycraft-dev()` /
  `package_ugli-dev()` (`PKGBUILD-dev`).

No change to `arch`, `license`, `provides`, or `conflicts` — this is purely a
`depends` addition, scoped identically to how spec 0086 (BL-64, OFL license)
and spec 0087 (BL-67, `arch=any`) each scoped their per-split-package
overrides.

## Done when:

- [x] **D1–D3** — `hicolor-icon-theme` present in `depends` of all eight
  `package_*()` functions across the three PKGBUILDs (release, `-git`,
  `-dev`); no other fields touched. Implemented in `c0d7973`.
- [x] **D4** — `.SRCINFO`/`.SRCINFO-git` regenerated in the same commit,
  showing the new `depends = hicolor-icon-theme` lines. `c0d7973`.
- [x] **D5** — a `poe package-dev` build followed by namcap against the
  built `uglycraft-dev`/`ugli-dev` packages shows no `hicolor-icon-theme`
  finding. Verified against `uglycraft-dev`/`ugli-dev`
  1.5.r713.gc0d7973-1: `.PKGINFO` for both packages lists `depend =
  hicolor-icon-theme`, and namcap on the built `.pkg.tar.zst` files shows
  no `hicolor-icon-theme` finding (only benign `bash`/glibc
  implicitly-satisfied notes and the pre-existing RELRO/PIE warnings,
  BL-74, out of scope).
- [x] **D6** — pkgbase-level `makedepends` in all three PKGBUILDs includes
  `hicolor-icon-theme` (alongside the entries spec 0092 added); `.SRCINFO`/
  `.SRCINFO-git` regenerated to show the new pkgbase-level `makedepends =
  hicolor-icon-theme` line; `namcap packaging/PKGBUILD` and `namcap
  packaging/PKGBUILD-git` run clean of all split-makedeps findings.
  Spec amendment in `ad56f62`, fix implemented in `8f3c117`. Re-verified:
  `namcap packaging/PKGBUILD` → only `Missing Maintainer tag`; `namcap
  packaging/PKGBUILD-git` → only `Missing Maintainer tag`; both fully clean
  of every split-makedeps finding. `makepkg --printsrcinfo` diffed against
  the committed `.SRCINFO`/`.SRCINFO-git` with no differences.

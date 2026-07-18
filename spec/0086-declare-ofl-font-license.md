# Spec 0086 — Declare OFL-1.1 for the bundled font in the uglycraft packages (BL-64)

The `uglycraft` split packages ship `fonts/ShareTechMono-Regular.ttf` (SIL Open
Font License 1.1) inside the site-packages tree, plus the OFL license text
under `/usr/share/licenses/`, but declare only `GPL-3.0-only`. The Arch
`license` field must list the licenses of **all distributed content** — add a
per-split-package override.

→ Audit: `kb/arch-packaging.md` (P2 section). → Backlog: BL-64.
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [x] **D1** — `license=('GPL-3.0-only' 'OFL-1.1')` added inside
  `package_uglycraft()` (`packaging/PKGBUILD`), overriding the pkgbase-level
  `license=('GPL-3.0-only')` for this split package only. — eaf3976
- [x] **D2** — same override in `package_uglycraft-git()` (`PKGBUILD-git`) and
  `package_uglycraft-dev()` (`PKGBUILD-dev`) — all three ship the identical
  package tree with the font inside. — eaf3976
- [x] **D3** — the `ugli` / `ugli-git` / `ugli-dev` split packages stay
  GPL-only (no font shipped — verified: they install the compiled binary, the
  kitty theme, and `.mo`/history translations only). — eaf3976; confirmed by
  diff (only the three `package_uglycraft*()` functions touched) and by the
  built `ugli-dev` package's `.PKGINFO` showing only `license = GPL-3.0-only`.
- [x] **D4** — `.SRCINFO` and `.SRCINFO-git` regenerated (spec 0084) in the
  same commit; each shows the two `license =` lines under the `pkgname =
  uglycraft`(`-git`) section. — eaf3976; `makepkg --printsrcinfo` diffs for
  both PKGBUILDs showed exactly the two added `license =` lines, nothing else.
- [x] **D5** — verified: `poe package-dev` builds; `.PKGINFO` of the built
  `uglycraft-dev` package lists both licenses (`tar -xOf … .PKGINFO | grep
  license`); namcap raises no license warning. — build produced
  `uglycraft-dev-1.5.r690.gc7b4e7a-1-any.pkg.tar.zst` whose `.PKGINFO` has
  `license = GPL-3.0-only` and `license = OFL-1.1`; namcap (built user-locally
  in a venv: pyalpm + pyelftools + license-expression against the system's
  libalpm/SPDX data, no system-wide install) run against the current build
  (`uglycraft-dev-1.5.r696.ga9f6282-1-any.pkg.tar.zst`) raised no license
  warning — both `GPL-3.0-only` and `OFL-1.1` resolved as known SPDX
  identifiers with license files present under `usr/share/licenses/`.

## Background — confirmed facts

- `license=('GPL-3.0-only')` is set once at pkgbase level in all three
  PKGBUILDs (`PKGBUILD:7`, `PKGBUILD-git:7`, `PKGBUILD-dev:13`) and never
  overridden.
- `package_uglycraft*()` installs the font via `cp -r src/uglycraft` (it lives
  at `uglycraft/fonts/ShareTechMono-Regular.ttf`) **and** installs
  `LICENSES/OFL-1.1-ShareTechMono.txt` into
  `/usr/share/licenses/$pkgname/` — the packaging already acknowledges the OFL
  content; only the `license` array is missing it.
- pygame/numpy are runtime **dependencies**, not bundled content — their
  licenses do not belong in the array (unlike the PyInstaller distributables,
  which do bundle them and handle this via `LICENSES/NOTICE.txt`).
- Arch's `license` field uses SPDX identifiers; `OFL-1.1` is the correct SPDX
  id for SIL Open Font License 1.1.

## Done when:

- [x] **D1–D3** — override present in the three `package_uglycraft*()`
  functions; `ugli*` untouched. — eaf3976
- [x] **D4** — both `.SRCINFO` files regenerated in the same commit. — eaf3976
- [x] **D5** — built dev package's `.PKGINFO` carries both licenses; namcap
  clean on this point. — `.PKGINFO` half confirmed (eaf3976 build); namcap
  (built user-locally in a venv) raised no license warning on the current dev
  build.

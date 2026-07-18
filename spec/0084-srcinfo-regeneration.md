# Spec 0084 — Regenerate `.SRCINFO` in the deploy tasks (BL-66)

Stop hand-copying static `.SRCINFO` files: the deploy tasks regenerate them
from the PKGBUILDs with `makepkg --printsrcinfo` so they can never drift
again. This is the **infrastructure spec** for the AUR compliance pass —
specs 0085–0090 all end with "regenerate `.SRCINFO`", and this spec is the
mechanism they ride on. Implement it first.

→ Audit: `kb/arch-packaging.md`. → Backlog: BL-66 (also applies BL-71 Part A's
rule to the deploy tasks).

## Status checklist

- [x] **D1** — `poe deploy-aur` regenerates `packaging/.SRCINFO` via
  `makepkg --printsrcinfo` before copying it to the AUR sibling repo. — c31b855
- [x] **D2** — `poe deploy-aur-git` likewise regenerates
  `packaging/.SRCINFO-git` from `PKGBUILD-git`. — c31b855
- [x] **D3** — both deploy tasks carry `executor = "simple"` (BL-71 Part A rule:
  every poe task that shells out to `makepkg` pins the no-op executor so the
  project venv can never leak into the build environment). — c31b855
- [x] **D4** — the currently stale `packaging/.SRCINFO-git` is regenerated once
  now and committed (drift: it said `pkgver = 1.4.r0.gf95b776`, the PKGBUILD
  says `1.4.r20.g21ad119`). — c31b855
- [x] **D5** — verified: `makepkg --printsrcinfo` output matches the committed
  files byte-for-byte for both PKGBUILDs after D4. — c31b855; the release
  `.SRCINFO` already matched before this change and needed no regeneration.

## Background — confirmed facts

- `deploy-aur` / `deploy-aur-git` (`pyproject.toml`) currently `cp` the static,
  hand-maintained `packaging/.SRCINFO` / `.SRCINFO-git` into the AUR sibling
  repos. Any PKGBUILD edit silently drifts them; the AUR reads **only**
  `.SRCINFO` for package metadata, so drift means wrong metadata on the AUR.
- Live proof of the failure mode: `.SRCINFO-git:2` is `pkgver =
  1.4.r0.gf95b776` while `PKGBUILD-git:3` says `pkgver=1.4.r20.g21ad119`.
- `makepkg --printsrcinfo` parses the PKGBUILD statically (sources it, prints
  metadata). It does **not** run `pkgver()` — for the VCS package the printed
  `pkgver` is whatever the `pkgver=` line last recorded from a real `makepkg`
  run. That is the normal AUR convention for VCS packages (the value is a
  hint; the real version is computed at build time).
- `PKGBUILD-dev` (spec 0083) is local-only and deliberately has **no**
  `.SRCINFO` — out of scope here.

## Change

In `pyproject.toml`, `deploy-aur` gains one line before the `cp`:

```bash
(cd packaging && makepkg --printsrcinfo > .SRCINFO)
```

and `deploy-aur-git` correspondingly:

```bash
(cd packaging && makepkg --printsrcinfo -p PKGBUILD-git > .SRCINFO-git)
```

Both tasks get `executor = "simple"` (D3). If regeneration changes the tracked
file, `git status` shows it — the working-copy diff is the drift surfaced;
commit it together with whatever PKGBUILD change caused it (the CLAUDE.md
maintenance rule).

## Verification

`cd packaging && makepkg --printsrcinfo | diff - .SRCINFO` (empty diff) and the
`-p PKGBUILD-git` equivalent against `.SRCINFO-git`. No AUR push needed —
this spec changes task text and one stale metadata file only.

## Out of scope

- A `.SRCINFO` for `PKGBUILD-dev` (never deployed, spec 0083).
- Any metadata *content* fixes — those are specs 0085–0090; this spec only
  fixes the copying mechanism plus the one already-stale file.

## Done when:

- [x] **D1** — `deploy-aur` regenerates `.SRCINFO` before copying. — c31b855
- [x] **D2** — `deploy-aur-git` regenerates `.SRCINFO-git` before copying. — c31b855
- [x] **D3** — both tasks pinned to `executor = "simple"`. — c31b855
- [x] **D4** — stale `.SRCINFO-git` regenerated and committed. — c31b855
- [x] **D5** — `makepkg --printsrcinfo` output matches both committed files.
  — c31b855; verified with `cd packaging && makepkg --printsrcinfo | diff -
  .SRCINFO` and the `-p PKGBUILD-git` equivalent against `.SRCINFO-git`, both
  empty diffs.

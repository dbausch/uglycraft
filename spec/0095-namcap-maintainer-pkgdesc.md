# Spec 0095 — Silence the two remaining namcap PKGBUILD warnings (BL-77)

## Status

- [x] D1 — `# Maintainer:` comment on line 1 of all three PKGBUILDs
- [x] D2 — both splits' `pkgdesc` reworded per Daniel's wording (all three PKGBUILDs)
- [x] D3 — `.SRCINFO` / `.SRCINFO-git` regenerated (pkgdesc is mirrored metadata)
- [x] D4 — namcap on `packaging/PKGBUILD` and `packaging/PKGBUILD-git`: zero warnings

## Background

After specs 0092/0093 closed BL-72/BL-73, `namcap` (3.6.0) leaves exactly two
warnings on the PKGBUILDs (→ see `kb/backlog.md` BL-77,
`kb/arch-packaging.md` operational notes):

1. **`W: Missing Maintainer tag`** — fires on both `packaging/PKGBUILD` and
   `packaging/PKGBUILD-git`. AUR convention is a `# Maintainer: Name <email>`
   comment on line 1; namcap checks for its presence.
2. **`PKGBUILD (ugli) W: Description should not contain the package name.`** —
   the `ugli` split package's `pkgdesc` begins with "UGLI 2 (1996) — …". The
   Arch guideline says the description must not redundantly repeat the
   package name.

Both should be resolved before the first AUR push so the published PKGBUILDs
are namcap-clean.

## Changes

### D1 — Maintainer comment

Add as **line 1** of `packaging/PKGBUILD`, `packaging/PKGBUILD-git`, and
`packaging/PKGBUILD-dev` (the dev variant is local-only, included for
consistency):

```bash
# Maintainer: Daniel Bausch <db@edv-bausch.de>
```

Notes:

- The comment does **not** appear in `.SRCINFO` (only real metadata fields are
  mirrored), so this half of the fix touches only the PKGBUILD files.
- This deliberately publishes a name + email in a tracked file. That is the
  point of the Maintainer tag — it is the AUR-facing contact — and is treated
  as an intentional exception to the "no personal details in tracked docs"
  rule. The address is the one every commit in this repo already uses
  (`git log` shows a single author identity, 1167 commits), so it is already
  public in the repository history.

### D2 — pkgdesc reword (both splits)

Wording chosen by Daniel (2026-07-19). Base descriptions:

- `ugli*`: `'Terminal treasure hunting game'`
- `uglycraft*`: `'Retro style treasure hunting game with various puzzles'`

The existing variant suffixes are kept, giving per-PKGBUILD values:

```
PKGBUILD      ugli:      'Terminal treasure hunting game'
PKGBUILD-git  ugli-git:  'Terminal treasure hunting game (git version)'
PKGBUILD-dev  ugli-dev:  'Terminal treasure hunting game (local dev build)'
PKGBUILD      uglycraft:     'Retro style treasure hunting game with various puzzles'
PKGBUILD-git  uglycraft-git: 'Retro style treasure hunting game with various puzzles (git version)'
PKGBUILD-dev  uglycraft-dev: 'Retro style treasure hunting game with various puzzles (local dev build)'
```

Notes:

- The namcap rule matches the split package's own `$pkgname` in `pkgdesc`
  (case-insensitively); only the release `ugli` split fires today. All six
  descriptions are reworded anyway so wording stays in sync across variants.
- Neither new base description contains "ugli" or "uglycraft" as a
  substring, so the rule cannot fire on any variant.

### D3 — `.SRCINFO` regeneration

`pkgdesc` is mirrored into `.SRCINFO`, so regenerate both tracked files via
the spec 0084 mechanism (`makepkg --printsrcinfo`, run from `packaging/`)
in the same commit as the PKGBUILD edits. Expected diff: exactly the changed
`pkgdesc` lines for all four splits (`uglycraft`/`ugli` and their `-git`
variants), nothing else. `PKGBUILD-dev` has no `.SRCINFO` by design.

## Verification

No test suite covers packaging; verification is by tool output:

- `namcap packaging/PKGBUILD` and `namcap packaging/PKGBUILD-git` → **zero
  warnings** (these two were the only remaining PKGBUILD-level findings).
- `git diff` of `.SRCINFO`/`.SRCINFO-git` shows only the two `pkgdesc`
  lines changed.

## Done when:

- [x] D1 — all three PKGBUILDs carry the `# Maintainer:` comment on line 1,
      with the repo's commit-author address (`db@edv-bausch.de`). (325c5ad)
- [x] D2 — all six `pkgdesc` values read exactly as specified above and no
      longer contain their own package name. (325c5ad)
- [x] D3 — `.SRCINFO` and `.SRCINFO-git` regenerated in the same commit;
      diff limited to the four `pkgdesc` lines (verified with `git diff`).
      (325c5ad)
- [x] D4 — `namcap` emits zero warnings on `packaging/PKGBUILD` and
      `packaging/PKGBUILD-git` — empty output, exit 0 on both, verified
      independently of the implementing agent (2026-07-19). (325c5ad)

# Spec 0095 — Silence the two remaining namcap PKGBUILD warnings (BL-77)

## Status

- [ ] D1 — `# Maintainer:` comment on line 1 of all three PKGBUILDs
- [ ] D2 — `ugli` split `pkgdesc` reworded without the package name (all three PKGBUILDs)
- [ ] D3 — `.SRCINFO` / `.SRCINFO-git` regenerated (pkgdesc is mirrored metadata)
- [ ] D4 — namcap on `packaging/PKGBUILD` and `packaging/PKGBUILD-git`: zero warnings

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
  rule. **The email address above is a proposal; confirm or substitute the
  address you want public on the AUR.**

### D2 — `ugli` pkgdesc reword

Current descriptions (release / git / dev):

```
'UGLI 2 (1996) — text-mode treasure game (Linux/FPC port)'
'UGLI 2 (1996) — text-mode treasure game (Linux/FPC port) (git version)'
'UGLI 2 (1996) — text-mode treasure game (Linux/FPC port) (local dev build)'
```

New descriptions — same information, name removed:

```
'Text-mode treasure game from 1996 (Linux/FPC port of the DOS original)'
'Text-mode treasure game from 1996 (Linux/FPC port of the DOS original) (git version)'
'Text-mode treasure game from 1996 (Linux/FPC port of the DOS original) (local dev build)'
```

Notes:

- The namcap rule matches the split package's own `$pkgname` in `pkgdesc`
  (case-insensitively), so only the `ugli` split of the release PKGBUILD
  fires today (`ugli-git`/`ugli-dev` don't literally appear in their
  descriptions). All three are reworded anyway so the wording stays in sync
  and cannot regress if a variant is ever renamed.
- The `uglycraft` splits' descriptions ("… inspired by UGLI (1996)") are
  **left unchanged**: "uglycraft" does not appear in them, so the rule does
  not and cannot fire there; mentioning the *other* game's name is
  informative, not redundant.

### D3 — `.SRCINFO` regeneration

`pkgdesc` is mirrored into `.SRCINFO`, so regenerate both tracked files via
the spec 0084 mechanism (`makepkg --printsrcinfo`, run from `packaging/`)
in the same commit as the PKGBUILD edits. Expected diff: exactly the changed
`pkgdesc` lines for the `ugli`/`ugli-git` splits, nothing else.
`PKGBUILD-dev` has no `.SRCINFO` by design.

## Verification

No test suite covers packaging; verification is by tool output:

- `namcap packaging/PKGBUILD` and `namcap packaging/PKGBUILD-git` → **zero
  warnings** (these two were the only remaining PKGBUILD-level findings).
- `git diff` of `.SRCINFO`/`.SRCINFO-git` shows only the two `pkgdesc`
  lines changed.

## Done when:

- [ ] D1 — all three PKGBUILDs carry the `# Maintainer:` comment on line 1,
      with the email address Daniel confirmed for AUR publication.
- [ ] D2 — the three `ugli*` `pkgdesc` values no longer contain the package
      name and read as specified above.
- [ ] D3 — `.SRCINFO` and `.SRCINFO-git` regenerated in the same commit;
      diff limited to the `pkgdesc` lines.
- [ ] D4 — `namcap` emits zero warnings on `packaging/PKGBUILD` and
      `packaging/PKGBUILD-git`.

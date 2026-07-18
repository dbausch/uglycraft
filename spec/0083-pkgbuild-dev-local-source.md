# Spec 0083 — `PKGBUILD-dev`: build from the local working repo, no push required

A third packaging variant, `packaging/PKGBUILD-dev`, that builds the AUR
packages from **this local git checkout's commit history** instead of
GitHub. It exists purely so `makepkg` can be exercised against local,
not-yet-pushed commits — exactly the gap spec 0082 D9 hit: verifying that
`makepkg` still works after the `src/` move required either pushing first or
skipping the check. `PKGBUILD-dev` removes that requirement. It is a **local
dev tool only** — never copied to an AUR sibling repo, never given a
`.SRCINFO`, never wired into `poe deploy*`.

## Status checklist

- [ ] **D1** — `packaging/PKGBUILD-dev` added: mirrors `PKGBUILD-git`
  (`pkgbase=uglycraft-dev`, split packages `uglycraft-dev` + `ugli-dev`), with
  one change — the game-source VCS entry points at a `git+file://` URL built
  from the PKGBUILD's own location (`${BASH_SOURCE[0]}`), not the public
  GitHub URL. No absolute path is hardcoded; it works from any clone/worktree
  location.
- [ ] **D2** — `pkgver()` derives from `git describe --long --tags` against
  the local clone, same as `PKGBUILD-git`, so the built package version shows
  exactly which local commit it came from (e.g. `1.5.r7.g4160602` for commits
  ahead of the `v1.5` tag).
- [ ] **D3** — `.gitignore` gains `packaging/uglycraft-dev/` (the VCS-source
  bootstrap clone directory makepkg creates beside the PKGBUILD), mirroring
  the existing `packaging/uglycraft-git/` entry.
- [ ] **D4** — convenience `poe package-dev` task: `cd packaging && makepkg -p
  PKGBUILD-dev -f`.
- [ ] **D5** — `CLAUDE.md` § *Arch packaging* documents `PKGBUILD-dev`: local
  only, no `.SRCINFO`, never deployed, exists to let `makepkg` be exercised
  against local commits without pushing.
- [ ] **D6** — verified: `poe package-dev` builds successfully from the
  current local repo (including today's spec 0082 commits, not yet pushed to
  GitHub), producing installable `uglycraft-dev` + `ugli-dev` packages; the
  installed `uglycraft-dev` reaches the menu with font + story (closes the
  `makepkg` gap left open in spec 0082 D9).

## Decision — confirmed 2026-07-18

**Source semantics: `git+file://` local clone (not a raw working-tree copy).**
`source=("$pkgbase::git+file://$_repo_root")`, where `_repo_root` is computed
at PKGBUILD-parse time:

```bash
_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
```

This works because makepkg reads a PKGBUILD via a bash `source`, so
`${BASH_SOURCE[0]}` resolves to `packaging/PKGBUILD-dev`'s own path — always
correct relative to wherever the repo happens to be checked out, no
hardcoded absolute path, no assumption about the invoking shell's cwd.

**Consequence:** the build sees **committed local history**, not uncommitted
working-tree edits — same semantics as `PKGBUILD-git` against GitHub, just
pointed at the local `.git` instead. To test an in-progress change, commit it
locally first (cheap, no push needed) and rerun `poe package-dev`. Rejected
alternative: copy the raw working tree via `git ls-files` so uncommitted
edits are included too — this would need new bespoke copy logic instead of
reusing makepkg's existing, already-proven VCS-source handling, for a benefit
(testing uncommitted state) that isn't needed today: the current motivating
case (spec 0082) is already fully committed locally.

## D1 — `packaging/PKGBUILD-dev`

Copy `PKGBUILD-git` and rename the pkgbase/pkgnames:

```bash
pkgbase=uglycraft-dev
pkgname=('uglycraft-dev' 'ugli-dev')
```

Both split packages keep parity with `PKGBUILD-git` (same `provides`,
`conflicts` pattern — `uglycraft-dev` conflicts with `uglycraft` and
`uglycraft-git` and vice versa, so only one variant is installed at a time).
The **only** structural change from `PKGBUILD-git` is the `source` entry for
the game itself:

```bash
_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source=("$pkgbase::git+file://$_repo_root"
        "uos.pas::https://raw.githubusercontent.com/fredvs/uos/main/src/uos.pas"
        "uos_flat.pas::https://raw.githubusercontent.com/fredvs/uos/main/src/uos_flat.pas"
        "uos_portaudio.pas::https://raw.githubusercontent.com/fredvs/uos/main/src/uos_portaudio.pas"
        "ANSI-87.conf::https://raw.githubusercontent.com/kovidgoyal/kitty-themes/master/themes/ANSI-87.conf")
```

UOS and the kitty theme still come from upstream — unrelated to this spec,
matches the existing `PKGBUILD`/`PKGBUILD-git` behaviour. The rest of
`prepare()`/`build()`/`package_*()` is copied unchanged from `PKGBUILD-git`
(including `cp -r src/uglycraft` from spec 0082 D5 — `PKGBUILD-dev` is
created *after* that change, so it never has the stale flat-layout path).

## D2 — `pkgver()`

```bash
pkgver() {
  cd "$pkgbase"
  git describe --long --tags | sed 's/^v//;s/-/.r/;s/-/./'
}
```

Identical to `PKGBUILD-git`'s `pkgver()` — it already operates on whatever
was cloned into `$srcdir/$pkgbase`, so no change needed beyond the `source`
URL update in D1.

## D3 — `.gitignore`

Add one line next to the existing `packaging/uglycraft-git/` entry:

```
packaging/uglycraft-dev/
```

## D4 — `poe package-dev` task

```toml
[tool.poe.tasks.package-dev]
help  = "Build uglycraft-dev/ugli-dev from the local repo's commit history (no push needed)"
shell = "cd packaging && makepkg -p PKGBUILD-dev -f"
```

Not part of `poe deploy` or any AUR flow — purely a local build/test
convenience.

## D5 — `CLAUDE.md` documentation

In § *Arch packaging*, add a short paragraph after the existing two-package
description:

> A third, **local-only** variant, `packaging/PKGBUILD-dev` (`uglycraft-dev` /
> `ugli-dev`), builds from this checkout's own commit history via a
> `git+file://` source instead of GitHub — so `makepkg` can be exercised
> against local, not-yet-pushed commits. It has no `.SRCINFO`, is never copied
> to an AUR sibling repo, and is never touched by any `poe deploy*` task.
> Build it with `poe package-dev`.

## D6 — Verification

1. `poe package-dev` runs `makepkg -p PKGBUILD-dev -f` and exits 0, cloning
   from the local repo (not GitHub) — confirm by checking the reported
   `pkgver` includes a `.rN.gHASH` suffix matching `git describe` run
   directly against this checkout, and that it reflects commits not present
   on the GitHub remote (e.g. today's spec 0082 commits).
2. The built `uglycraft-dev` package installs
   (`pacman -U packaging/uglycraft-dev-*.pkg.tar.zst` or inspect via
   `namcap`/manual extraction) with the same `.../site-packages/uglycraft/`
   layout as the release/`-git` packages (16 modules + `fonts/` +
   `translations/`).
3. Installed `uglycraft-dev` launches and reaches the menu with correct font
   and history/story text (same check as spec 0082 D9's still-open `makepkg`
   item) — self-verifiable without Daniel, since it's a mechanical pass/fail
   (font renders, no crash), not a subjective in-game judgement call.

## Out of scope

- Publishing `PKGBUILD-dev` anywhere (AUR, `.SRCINFO`, `poe deploy*`) — it is
  local-only by design.
- Any change to `PKGBUILD` or `PKGBUILD-git` themselves (already updated by
  spec 0082 D5).
- Supporting uncommitted/dirty working-tree state (see Decision above) — a
  possible future extension, not needed today.

## Done when:

- [ ] **D1** — `packaging/PKGBUILD-dev` exists, mirrors `PKGBUILD-git`, sources
  the game via a `${BASH_SOURCE[0]}`-derived `git+file://` URL.
- [ ] **D2** — `pkgver()` reports the local commit correctly.
- [ ] **D3** — `.gitignore` covers `packaging/uglycraft-dev/`.
- [ ] **D4** — `poe package-dev` task added.
- [ ] **D5** — `CLAUDE.md` documents `PKGBUILD-dev` as local-only.
- [ ] **D6** — `poe package-dev` builds and installs successfully from local
  commits, and the installed `uglycraft-dev` reaches the menu with font +
  story.

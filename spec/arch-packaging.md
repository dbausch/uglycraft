# Split Arch packaging: release + git

## Status

- [ ] `packaging/PKGBUILD` cleaned up for release tags only
- [ ] `packaging/PKGBUILD-git` created for VCS package
- [ ] `deploy-aur` task updated (or split) to handle both repos
- [ ] Dev tag workflow removed from CLAUDE.md
- [ ] Both packages build and install cleanly

## Problem

The current PKGBUILD uses a movable `dev` tag (`_tag=dev`) during
development, requiring `git tag -f dev && git push --tags -f` before
every `makepkg` run.  This is fragile (stale tarball caches, force-push
noise) and conflates two use cases:

1. **Release builds** — pinned to an immutable tag like `v1.4`.
2. **Development builds** — tracking the latest commit on `main`.

## Design

### Two packages, two AUR repos

| | `uglycraft` (release) | `uglycraft-git` (VCS) |
|---|---|---|
| AUR repo | `../uglycraft-aur` | `../uglycraft-git-aur` |
| PKGBUILD | `packaging/PKGBUILD` | `packaging/PKGBUILD-git` |
| Source | GitHub tarball by release tag | `git+https://…` clone |
| `pkgver` | Set manually (`1.4`, `1.5`, …) | `pkgver()` from `git describe` |
| `_tag` | Release tag (e.g. `v1.5`) | Not used |
| Split packages | `uglycraft` + `ugli` | `uglycraft-git` + `ugli-git` |
| Conflicts | `uglycraft-git`, `ugli-git` | `uglycraft`, `ugli` |
| Provides | `uglycraft`, `ugli` | `uglycraft`, `ugli` |

### `packaging/PKGBUILD` (release) changes

- Remove the `_tag=dev` indirection; use the release tag directly in
  `source=()`.  The `_tag` variable stays but is set to the release tag
  (e.g. `_tag=v1.5`) and only changed at release time.
- Add `conflicts=('uglycraft-git')` to `package_uglycraft()` and
  `conflicts=('ugli-git')` to `package_ugli()`.
- Add `provides=('uglycraft')` / `provides=('ugli')` (implicit for
  same-name packages, but explicit is clearer with the `-git` counterpart).
- Replace `sha256sums=('SKIP' ...)` with actual checksums for all
  sources.  At release time, download each source and compute its
  sha256sum, or use `updpkgsums` (from `pacman-contrib`) to fill them
  in automatically.

### `packaging/PKGBUILD-git` (new)

Standard VCS PKGBUILD pattern:

```bash
pkgbase=uglycraft-git
pkgname=('uglycraft-git' 'ugli-git')
pkgver=1.4.r3.gabc1234
pkgrel=1
# ...
makedepends=('fpc' 'git')
source=("$pkgbase::git+https://github.com/dbausch/uglycraft.git"
        "uos.pas::https://..."
        "uos_flat.pas::https://..."
        "uos_portaudio.pas::https://..."
        "ANSI-87.conf::https://...")

pkgver() {
  cd "$pkgbase"
  git describe --long --tags | sed 's/^v//;s/-/.r/;s/-/./'
}

prepare() {
  cd "$pkgbase"
  # copy UOS sources, create uos_define.inc, copy ANSI-87.conf
}

build() {
  cd "$pkgbase/original"
  fpc -Fuuos UGLI_2.pp
}

package_uglycraft-git() {
  pkgdesc='... (git version)'
  depends=(...)
  provides=('uglycraft')
  conflicts=('uglycraft')
  # same install steps as release, but cd "$pkgbase" instead of "$pkgbase-$_tag"
}

package_ugli-git() {
  pkgdesc='... (git version)'
  optdepends=(...)
  provides=('ugli')
  conflicts=('ugli')
  # same install steps
}
```

The `pkgver()` function produces versions like `1.4.r3.gabc1234` (3
commits after tag `v1.4`, at commit `abc1234`).  This requires at least
one annotated or lightweight tag in the repo — release tags satisfy this.

### `deploy-aur` task changes

Split into two tasks:

- **`deploy-aur`** — copies `PKGBUILD` + `.SRCINFO` to `../uglycraft-aur`,
  commits, pushes.  Used at release time.  Same as today but without the
  dev tag dance.
- **`deploy-aur-git`** — copies `PKGBUILD-git` (as `PKGBUILD`) +
  `.SRCINFO-git` (as `.SRCINFO`) to `../uglycraft-git-aur`, commits,
  pushes.

### What to remove

- The `_tag=dev` pattern and the dev tag instructions in `CLAUDE.md`
  ("Arch packaging and tags" section).
- No more `git tag -f dev && git push --tags -f` before builds.

## Verification

Since there is no automated test suite for packaging, verification is
manual:

- `makepkg` with `PKGBUILD` (release) succeeds and installs both
  `uglycraft` and `ugli`
- `makepkg` with `PKGBUILD-git` succeeds and installs both
  `uglycraft-git` and `ugli-git`
- Installing one set conflicts with the other
- `ugli` / `ugli-git` launches the game
- `uglycraft` / `uglycraft-git` launches the game

## Done when

- [ ] `packaging/PKGBUILD` uses release tag, has `conflicts`/`provides`, real sha256sums
- [ ] `packaging/PKGBUILD-git` exists and builds from git HEAD
- [ ] `deploy-aur` and `deploy-aur-git` poe tasks work
- [ ] Dev tag workflow removed from `CLAUDE.md`
- [ ] Both packages build cleanly with `makepkg`

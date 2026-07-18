# Arch / AUR packaging audit

Compliance review of the repo's Arch packaging against the official guidelines,
done ahead of the first **public** AUR release. Records what is wrong, what is
correct, and the operational steps the first push needs.

→ Backlog items spawned from this audit: **BL-61 … BL-70** (`kb/backlog.md`)
→ Packaging process + AUR repo layout: `CLAUDE.md` § *Arch packaging*

## Source guidelines

The three ArchWiki pages this was checked against (fetched as saved HTML; the
live site is behind Anubis anti-bot and cannot be WebFetched):

- Arch package guidelines — <https://wiki.archlinux.org/title/Arch_package_guidelines>
- Free Pascal package guidelines — <https://wiki.archlinux.org/title/Free_Pascal_package_guidelines>
- Python package guidelines — <https://wiki.archlinux.org/title/Python_package_guidelines>

## Package topology

Two `pkgbase`, four split packages, two AUR repos:

| pkgbase | split packages | PKGBUILD | AUR repo (deploy target) |
|---|---|---|---|
| `uglycraft` (release, `_tag=v$pkgver`) | `uglycraft` (Python game), `ugli` (FPC port of the 1996 original) | `packaging/PKGBUILD` | `../uglycraft-aur` via `poe deploy-aur` |
| `uglycraft-git` (VCS) | `uglycraft-git`, `ugli-git` | `packaging/PKGBUILD-git` | `../uglycraft-git-aur` via `poe deploy-aur-git` |

Deploy tasks (`pyproject.toml`) `cp` **only** `PKGBUILD` + `.SRCINFO` into the
sibling AUR clone, commit, and push. All helper files (`*.desktop`, `*.svg`,
`ugli.sh`, `LICENSES/*`, the Pascal sources) reach the build from the release
tarball / git clone, **not** from the AUR repo — so the AUR repos stay minimal
(PKGBUILD + .SRCINFO only). Build artifacts (`packaging/{pkg,src}/`,
`*.pkg.tar.zst`, `*.tar.gz`, fetched `uos*.pas`/`ANSI-87.conf`) are all
gitignored — verified nothing leaks. ✓

## Findings

Severity uses the backlog scheme: **P1** blocks the release (users get a broken
package), **P2** is a guideline violation to fix before publishing, **P3** is
reproducibility / polish.

### P1 — the packaged game is broken (BL-61)

> **RESOLVED — spec 0080 (D7), confirmed 2026-07-18.** The `uglycraft/` package
> restructure shipped; both PKGBUILDs now `cp -r uglycraft` the whole package
> into site-packages, so the install list can no longer go stale. Verified in
> practice: the `uglycraft-git-1.5.r657.g6f4ae40` AUR package installs and
> launches — correct font, history/story screen renders, no
> `ModuleNotFoundError`. **BL-61 closed.** The audit below records the original
> defect. (D9 user acceptance still owes the dev-run and Linux-build legs.)

`packaging/PKGBUILD:47-48` and `PKGBUILD-git:51-52` install a **hardcoded list of
8 modules**:

```
main.py game.py constants.py sprites.py levels.py entities.py hiscore.py sounds.py
```

The game is now **16** modules. The wrapper runs `python
/usr/share/uglycraft/main.py`, which crashes at `game.py:12` (`from hud import …`)
before the window opens. The 7 runtime modules that are **missing** from the
package: `hud`, `world`, `crafting`, `cells`, `rooms`, `levelgraph`,
`levellayout` (import chain: `main`→`game`→`hud`/`world`/`crafting`;
`world`→`rooms`/`cells`/`levels`; `levels`→`levelgraph`/`levellayout`;
`sprites`→`crafting`). `leveldump` (8th absent file) is lazily imported at
`main.py:71` only for `--dump-level`, so also missing but debug-only.

**Root cause:** the module list went stale after the world/hud/crafting split
(specs 0045–0047, 0072). Only the `ugli` (Pascal) half is unaffected.

**Fix (spec 0080):** the durable fix is to make the game a real **package** —
move all 16 modules into `uglycraft/` and install the whole directory as one unit
into site-packages, run as `python -m uglycraft`. The install list then cannot go
stale, because there is no list:

```bash
_site=$(python -c "import site; print(site.getsitepackages()[0])")
install -d "$pkgdir$_site"
cp -r uglycraft "$pkgdir$_site/"
python -m compileall -q "$pkgdir$_site/uglycraft"   # folds in BL-69
```

The wrapper becomes `exec python -m uglycraft "$@"`, and the bundled font +
history text now ride **inside** the package (`uglycraft/fonts`,
`uglycraft/translations`) instead of being installed separately. (An earlier plan
used a flat `install -m644 *.py …` glob; the package restructure was chosen
instead — it fixes the root cause and follows the standard Python layout. See
spec 0080, decision 2026-07-16.)

### P2 — redundant `provides=($pkgname)` (BL-62)

Guideline: *"Do not add `$pkgname` to provides, as it is always implicitly
provided."* Violated in `package_uglycraft` (`provides=('uglycraft')`,
`PKGBUILD:41`) and `package_ugli` (`provides=('ugli')`, `:77`). Remove both.

⚠️ **Keep** the `provides` in the `-git` packages (`PKGBUILD-git:45,81`): there
`$pkgname` is `uglycraft-git`/`ugli-git`, so declaring `provides=('uglycraft')`
/`('ugli')` is correct and required so the VCS package satisfies dependencies on
the non-git name (and pairs with its `conflicts`).

### P2 — `SKIP` checksum on the release tarball (BL-63)

Guideline: integrity variables must contain correct values (`updpkgsums`); the
repo's own `CLAUDE.md` says to run `updpkgsums` at release time — but
`PKGBUILD:15-19` is still all-`SKIP`. At minimum the versioned
`v$pkgver.tar.gz` (index 0) must carry a real sha256. The `git` PKGBUILD
legitimately keeps `SKIP` (VCS clone). See also BL-65 for the branch-tip sources
that currently *force* the other four SKIPs.

### P2 — `uglycraft` ships the OFL font but declares only GPL-3.0-only (BL-64)

`license` is set once at pkgbase level (`GPL-3.0-only`) and never overridden.
But `package_uglycraft` installs `fonts/ShareTechMono-Regular.ttf` and its
`OFL-1.1-ShareTechMono.txt` (`PKGBUILD:50,68`). The `license` field must list
**all** licenses of distributed content, so override per split package:

```bash
license=('GPL-3.0-only' 'OFL-1.1')   # in package_uglycraft (+ package_uglycraft-git)
```

`ugli` ships no font → GPL-only is correct there. `python-pygame`/`python-numpy`
are runtime deps (separate packages), not bundled, so their LGPL/BSD do **not**
belong in this package's `license`.

### P3 — non-reproducible moving-branch sources (BL-65)

`uos.pas`/`uos_flat.pas`/`uos_portaudio.pas` come from `…/uos/main/…` and
`ANSI-87.conf` from `…/kitty-themes/master/…` (`PKGBUILD:11-14`). Unversioned
branch tips: the build is non-reproducible **and** these are the reason four
`sha256sums` are pinned to `SKIP`. Pin each to a commit hash / tag and give it a
real checksum. Reproducibility is an explicit goal of the Arch guidelines.

### P3 — `.SRCINFO` is hand-copied, never regenerated (BL-66)

`deploy-aur`/`deploy-aur-git` `cp` a static `.SRCINFO`/`.SRCINFO-git`
(`pyproject.toml:187-`). It currently matches (`makepkg --printsrcinfo` diff =
MATCH for the release), but any PKGBUILD edit silently drifts it — and
`.SRCINFO-git` already shows a stale `pkgver` (`1.4.r0.gf95b776` vs the
PKGBUILD's `1.4.r20.g21ad119`). Regenerate in the deploy task instead of
copying: `cd packaging && makepkg --printsrcinfo > .SRCINFO`. Any fix to the
`provides`/`license` fields above must be re-flowed into `.SRCINFO`.

### P3 — `arch=('x86_64')` on the pure-Python `uglycraft` (BL-67)

`arch` is overridable per split package. `uglycraft` is architecture-independent
(pure Python) and could set `arch=('any')` so it installs on aarch64 etc.;
`ugli` (compiled FPC binary) correctly stays `x86_64`. The pkgbase-level array
must still include every arch the split members need.

### P3 — compiled binary under `/usr/share` (BL-68)

`UGLI_2` (an ELF executable) is installed to `/usr/share/ugli/UGLI_2`
(`PKGBUILD:82`). `/usr/share` is for architecture-independent data; a private,
wrapper-invoked binary is more idiomatic in `/usr/lib/ugli/`. namcap will warn
("ELF file in /usr/share"). Harmless but non-canonical; the wrapper path in
`ugli.sh` and the PKGBUILD both need updating together.

### P3 — installed modules are not byte-compiled (BL-69)

The loose `.py` files land in root-owned `/usr/share/uglycraft`; at first run
Python tries to write `__pycache__` there, fails silently, and recompiles every
launch. Proper Python packaging precompiles bytecode (`python -m compileall`, or
`--optimize=1` in the setuptools path). Minor; commonly skipped for loose-script
games. **Folded into spec 0080:** the site-packages install byte-compiles the
package with `python -m compileall`, and the package lives in a writable
site-packages dir, so first-launch recompilation no longer applies.

### P3 — stale `pyproject.toml [project]` metadata (BL-70)

Not an AUR file, but packaging metadata: `[project]` says `version = "1.0"` and
`description = "…UGLI (1993)…"` (`pyproject.toml:1-4`), vs the real v1.5 / 1996.
Independent of the AUR fixes.

## Verified correct (checked, no change needed)

- **Naming** — lowercase; app name only (no `python-` prefix, correct for an
  application per the Python guidelines); no upstream-major-version suffix.
- **Free Pascal** — `fpc` in `makedepends`; a standalone executable is built and
  only the binary is installed, so the "put compiled units under
  `/usr/lib/fpc/$ver/units/$arch-linux`" rule does **not** apply (no units shipped).
- **VCS package** — `git+https://` source, `git` in `makedepends`, canonical
  `pkgver()` (`git describe --long --tags | sed …` → `1.4.r20.g21ad119`).
- **Directories** — `/usr/bin` wrapper, `/usr/share` data,
  `/usr/share/licenses/$pkgname`, `/usr/share/applications`, scalable
  `/usr/share/icons/hicolor/scalable/apps`; no forbidden dirs
  (`/usr/local`, `/bin`, `/opt`, …).
- **Hygiene** — `"$pkgdir"`/`"$srcdir"` quoted; custom var `_tag` underscore-prefixed;
  lines < 100 cols; SPDX `GPL-3.0-only`; sources renamed to be unique in
  `srcdir` (`name::url`); HTTPS/git+https throughout.
- **Relations** — release ↔ git mutual `conflicts` correct; `uglycraft` and
  `ugli` are co-installable (distinct binaries/data dirs) as intended.
- **Runtime paths** (once modules are present) — font/translations load relative
  to `__file__` → resolve under `/usr/share/uglycraft`; high scores save to
  `$XDG_DATA_HOME/uglycraft/uglycraft.hsc` (`constants.py:14-24`), a writable
  location, so the wrapper needs no `cd`.

## Operational notes for the first push

- **The AUR repos don't exist yet.** `../uglycraft-aur` and `../uglycraft-git-aur`
  are absent, so `poe deploy-aur` errors immediately. After registering the
  package names, clone them: `git clone ssh://aur@aur.archlinux.org/uglycraft.git`
  and `…/uglycraft-git.git` as the siblings the deploy tasks expect.
- Run `updpkgsums packaging/PKGBUILD` (fills BL-63) and `namcap` on both the
  PKGBUILD and the built `.pkg.tar.zst` before pushing — namcap surfaces BL-68
  and any dependency mistakes.
- After editing any field, regenerate `.SRCINFO` (BL-66) — the AUR reads it for
  all package metadata.

## Priority summary

- **Must fix before release:** ~~BL-61 (broken game)~~ ✓ closed (spec 0080 D7,
  2026-07-18), BL-63 (release checksum).
- **Should fix before release:** BL-62 (redundant provides), BL-64 (OFL license).
- **Reproducibility / polish, can follow:** BL-65, BL-66, BL-67, BL-68, BL-69, BL-70.

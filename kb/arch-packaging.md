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

Deploy tasks (`pyproject.toml`) **regenerate** `.SRCINFO`/`.SRCINFO-git` via
`makepkg --printsrcinfo` immediately before copying (spec 0084/BL-66, commit
c31b855 — this replaced the old hand-copied static file, which could drift
silently), then `cp` **only** `PKGBUILD` + the freshly regenerated `.SRCINFO`
into the sibling AUR clone, commit, and push. Both deploy tasks also carry
`executor = "simple"` (BL-71 Part A's poe-executor rule, applied here so the
project's own `.venv` can never leak into a `makepkg` invocation). All helper
files (`*.desktop`, `*.svg`,
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
>
> **Frozen-build follow-on, fixed by spec 0082.** Verifying 0080 D9's Linux-build
> leg turned up a second, unrelated bug: `poe build-linux`'s `--collect-data
> uglycraft` silently collected **zero** files (`WARNING: collect_data_files -
> skipping data collection for module 'uglycraft' as it is not a package`), and
> the frozen binary crashed with `FileNotFoundError` on the bundled font. Root
> cause: `collect_data_files` calls `importlib.util.find_spec('uglycraft')` in
> the `pyinstaller` process itself, whose `sys.path` is the venv only — and
> `uglycraft` was never an *installed* package, just a directory the repo-root
> cwd happened to make importable. Spec 0082 fixes this at the root: `uglycraft`
> moved to `src/uglycraft/` (PyPA `src/` layout) and `poe install` now does `pip
> install -e ".[dev]"`, so the package sits on the venv's own `sys.path` and
> `find_spec` succeeds unconditionally — no `PYTHONPATH`, no cwd assumption. The
> `src/` layout also removes the old flat-layout shadow trap (the repo-root copy
> was importable even un-installed, which is what hid this for as long as it
> did). PKGBUILD/`PKGBUILD-git` source path updated to `cp -r src/uglycraft`
> (D5); the **installed** site-packages layout is byte-for-byte unchanged.

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
cp -r src/uglycraft "$pkgdir$_site/"   # src/ layout since spec 0082
python -m compileall -q "$pkgdir$_site/uglycraft"   # folds in BL-69
```

The wrapper becomes `exec python -m uglycraft "$@"`, and the bundled font +
history text now ride **inside** the package (`uglycraft/fonts`,
`uglycraft/translations`) instead of being installed separately. (An earlier plan
used a flat `install -m644 *.py …` glob; the package restructure was chosen
instead — it fixes the root cause and follows the standard Python layout. See
spec 0080, decision 2026-07-16.)

### P2 — redundant `provides=($pkgname)` (BL-62)

> **RESOLVED — spec 0085, confirmed 2026-07-18.** Commit 96a60f2 deleted both
> redundant `provides` lines from `packaging/PKGBUILD` (`package_uglycraft`,
> `package_ugli`); `.SRCINFO` regenerated in the same commit (spec 0084
> mechanism) shows exactly those two lines gone, nothing else. `PKGBUILD-git`
> / `PKGBUILD-dev` were left untouched, as intended. namcap (system-installed)
> raises no provides-related warning. **BL-62 closed.**

Guideline: *"Do not add `$pkgname` to provides, as it is always implicitly
provided."* Violated in `package_uglycraft` (`provides=('uglycraft')`,
`PKGBUILD:41`) and `package_ugli` (`provides=('ugli')`, `:77`). Remove both.

⚠️ **Keep** the `provides` in the `-git` packages (`PKGBUILD-git:45,81`): there
`$pkgname` is `uglycraft-git`/`ugli-git`, so declaring `provides=('uglycraft')`
/`('ugli')` is correct and required so the VCS package satisfies dependencies on
the non-git name (and pairs with its `conflicts`).

### P2 — `SKIP` checksum on the release tarball (BL-63)

> **RESOLVED — spec 0090, confirmed 2026-07-18.** Commit 3712eee ran
> `updpkgsums packaging/PKGBUILD`; source index 0 (the `v$pkgver.tar.gz`
> tarball) now carries a real sha256
> (`6fd94d423b5daed0966c63baaab297b103cb326c657712d883d140f8d27bd200`).
> Sequenced after spec 0089 pinned the four external sources (BL-65), so
> those four sums were only re-verified, not rewritten — `git diff` confirmed
> only the index-0 line changed. `makepkg --verifysource -p PKGBUILD` passes
> against the live v1.5 GitHub tag. `PKGBUILD-git`/`PKGBUILD-dev` correctly
> keep `SKIP` for their VCS-clone source only. **BL-63 closed.**

Guideline: integrity variables must contain correct values (`updpkgsums`); the
repo's own `CLAUDE.md` says to run `updpkgsums` at release time — but
`PKGBUILD:15-19` is still all-`SKIP`. At minimum the versioned
`v$pkgver.tar.gz` (index 0) must carry a real sha256. The `git` PKGBUILD
legitimately keeps `SKIP` (VCS clone). See also BL-65 for the branch-tip sources
that currently *force* the other four SKIPs.

### P2 — `uglycraft` ships the OFL font but declares only GPL-3.0-only (BL-64)

> **RESOLVED — spec 0086, confirmed 2026-07-18.** Commit eaf3976 added
> `license=('GPL-3.0-only' 'OFL-1.1')` inside `package_uglycraft()` (and the
> `-git`/`-dev` equivalents); `ugli*` stays GPL-only (ships no font).
> `.SRCINFO`/`.SRCINFO-git` regenerated in the same commit. The built
> `uglycraft-dev` package's `.PKGINFO` carries both `license =` lines, and
> namcap (system-installed) raises no license warning — both SPDX ids
> resolve, with license files present under `/usr/share/licenses/`. **BL-64
> closed.**

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

> **RESOLVED — spec 0089, confirmed 2026-07-18.** Commit a9f6282 pinned all
> four external files to fixed commit hashes —
> `_uos_commit=ffd165382aeae1cc1bf80673d5c02497c06f4efa` and
> `_themes_commit=e144651f75891cf4795ef1e7c24bb3e27c47aa06` (looked up via
> `git ls-remote` at implementation time; these were the branch heads the
> builds already used, so built content is unchanged) — in all three
> PKGBUILDs *and* in the `poe build-original` task, and gave all four files
> real sha256 sums. This unblocked spec 0090/BL-63: the four moving-tip
> sources were the reason the release-tarball `SKIP` couldn't be cleanly
> `updpkgsums`-filled before. `.SRCINFO`/`.SRCINFO-git` regenerated in the
> same commit. **BL-65 closed.**

`uos.pas`/`uos_flat.pas`/`uos_portaudio.pas` come from `…/uos/main/…` and
`ANSI-87.conf` from `…/kitty-themes/master/…` (`PKGBUILD:11-14`). Unversioned
branch tips: the build is non-reproducible **and** these are the reason four
`sha256sums` are pinned to `SKIP`. Pin each to a commit hash / tag and give it a
real checksum. Reproducibility is an explicit goal of the Arch guidelines.

### P3 — `.SRCINFO` is hand-copied, never regenerated (BL-66)

> **RESOLVED — spec 0084, confirmed 2026-07-18.** Commit c31b855 made
> `poe deploy-aur`/`deploy-aur-git` **regenerate** `.SRCINFO`/`.SRCINFO-git`
> via `makepkg --printsrcinfo` immediately before the `cp` step, instead of
> copying a hand-maintained static file — see "Operational notes" below. Both
> tasks also gained `executor = "simple"` (applying BL-71 Part A's rule to
> these two makepkg-invoking tasks, so the project's own `.venv` can never
> leak `_site` detection into a real build). The already-stale
> `.SRCINFO-git` (`1.4.r0.gf95b776` vs the PKGBUILD's `1.4.r20.g21ad119`) was
> regenerated once in the same commit. This is the infrastructure spec every
> other spec in this pass (0085–0090) rides on — from here on, any PKGBUILD
> metadata edit re-flows into `.SRCINFO` automatically at deploy time.
> **BL-66 closed.**

`deploy-aur`/`deploy-aur-git` `cp` a static `.SRCINFO`/`.SRCINFO-git`
(`pyproject.toml:187-`). It currently matches (`makepkg --printsrcinfo` diff =
MATCH for the release), but any PKGBUILD edit silently drifts it — and
`.SRCINFO-git` already shows a stale `pkgver` (`1.4.r0.gf95b776` vs the
PKGBUILD's `1.4.r20.g21ad119`). Regenerate in the deploy task instead of
copying: `cd packaging && makepkg --printsrcinfo > .SRCINFO`. Any fix to the
`provides`/`license` fields above must be re-flowed into `.SRCINFO`.

### P3 — `arch=('x86_64')` on the pure-Python `uglycraft` (BL-67)

> **RESOLVED — spec 0087, confirmed 2026-07-18.** Commit c7b4e7a added
> `arch=('any')` inside `package_uglycraft()` (and the `-git`/`-dev`
> equivalents); the pkgbase-level array and `package_ugli*()` stay `x86_64`
> unchanged. One `poe package-dev` run produces an `…-any.pkg.tar.zst`
> alongside the x86_64 `ugli-dev` package; the extracted `any` package's
> headless `--dump-level` run passed, and namcap's `anyelf` rule (which
> flags ELF files inside an `arch=any` package) found none. **BL-67 closed.**

`arch` is overridable per split package. `uglycraft` is architecture-independent
(pure Python) and could set `arch=('any')` so it installs on aarch64 etc.;
`ugli` (compiled FPC binary) correctly stays `x86_64`. The pkgbase-level array
must still include every arch the split members need.

### P3 — compiled binary under `/usr/share` (BL-68)

> **RESOLVED — spec 0088, confirmed 2026-07-18 — except the real-terminal
> launch check, still open as user acceptance.** Commit b49b587 moved
> `UGLI_2` to `/usr/lib/ugli/UGLI_2` in all three PKGBUILDs and updated
> `packaging/ugli.sh`'s `UGLI=` path to match. **Discovered mechanism** (the
> one open question this spec had to settle): `UGLI_2` resolves both
> `translations/*.mo` and `history_*.txt` relative to its **own executable
> path** (`ParamStr(0)`), not a compiled-in `/usr/share` constant — confirmed
> by reading `original/UGLI_2_Core.inc`'s `LoadTranslation` (lines
> 1978–2007) and `LoadHistoryText` (lines 1524–1568), both of which build
> their path from `ExeDir`. So `translations/` had to **move with the
> binary** to `/usr/lib/ugli/translations/`, while `ANSI-87.conf` — read only
> by the wrapper script via a `-c` kitty flag, never by the Pascal binary
> itself — correctly **stays** under `/usr/share/ugli/` as pure wrapper-only
> data. This was positively verified (not just inferred) by running the
> extracted binary from an unrelated CWD with a forced German locale and
> observing translated `--help` output — no other locale path on the test
> machine could have supplied that translation. `.SRCINFO` regeneration
> showed no diff (function-body-only change). namcap's `elfpaths` rule
> (allows `usr/lib/`, not `usr/share/`) no longer fires; the only remaining
> ELF-related namcap output is the unrelated RELRO/PIE hardening warning
> (filed as a new backlog item, see "Operational notes" below). → see
> spec/0088. **D4's real-terminal-launch leg remains open pending user
> acceptance; everything else about BL-68 is closed.**

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
- `updpkgsums` has already been run (BL-63/spec 0090) and the four external
  sources are pinned (`_uos_commit`/`_themes_commit`, BL-65/spec 0089) — real
  sha256 sums exist throughout except the two VCS-clone `SKIP`s
  (`PKGBUILD-git`/`PKGBUILD-dev` index 0), which are the sanctioned use of
  `SKIP`.
- `poe deploy-aur`/`deploy-aur-git` now **regenerate** `.SRCINFO`/
  `.SRCINFO-git` via `makepkg --printsrcinfo` immediately before copying
  (BL-66/spec 0084, commit c31b855) instead of hand-copying a static file, so
  this can no longer drift silently — no further operational step needed here.
- **namcap has now been run** (system-installed, `namcap 3.6.0-3`) against
  both PKGBUILDs and both built dev packages (`uglycraft-dev`, `ugli-dev`).
  Every finding this audit tracked (BL-62, BL-64, BL-66, BL-67, BL-68) came
  back clean. Three more findings fell outside this audit's original
  scope and were filed as new backlog items (`kb/backlog.md` BL-72–BL-74):
  a `uglycraft-git` split-makedepends note, a missing `hicolor-icon-theme`
  dependency, and RELRO/PIE hardening on the FPC `UGLI_2` binary. **The
  first two are now RESOLVED** — split makedepends by spec 0092
  (commit ed3539f, BL-72) and hicolor-icon-theme by spec 0093 (commits
  c0d7973 + 8f3c117, BL-73); see `kb/backlog.md` for the closure detail.
  Only RELRO/PIE (BL-74) remains open of the three.

**Two durable insights from resolving BL-72/BL-73** (kept here because they
generalize to any future namcap-driven PKGBUILD fix, not just this pass):

1. namcap's split-makedeps rule (`SplitPkgMakedepsRule`) resolves a
   subpackage's dependency coverage against the **local pacman database**,
   not the PKGBUILD in isolation — a clean namcap run on a machine that
   happens to have a related package installed (e.g. `uglycraft-dev`
   providing `uglycraft`) is **not** evidence of correctness. Always judge
   namcap PKGBUILD findings from a clean-DB perspective; the release
   PKGBUILD's apparently-clean run during the original audit was exactly
   this trap. → see spec/0092-split-package-makedepends.md
2. Any `depends` entry added to a split subpackage must also be covered by
   pkgbase-level `makedepends`, or the same split-makedeps rule fires again
   for that new entry — this is how adding `hicolor-icon-theme` to each
   `package_*()`'s `depends` re-triggered the rule spec 0092 had just
   silenced, requiring `hicolor-icon-theme` in pkgbase-level `makedepends`
   too. → see spec/0093-hicolor-icon-theme-dependency.md (D6)

## Priority summary

- **Must fix before release:** ~~BL-61 (broken game)~~ ✓ closed (spec 0080 D7,
  2026-07-18), ~~BL-63 (release checksum)~~ ✓ closed (spec 0090, 2026-07-18).
- **Should fix before release:** ~~BL-62 (redundant provides)~~ ✓ closed
  (spec 0085), ~~BL-64 (OFL license)~~ ✓ closed (spec 0086).
- **Reproducibility / polish:** ~~BL-65~~ ✓ closed (spec 0089), ~~BL-66~~ ✓
  closed (spec 0084), ~~BL-67~~ ✓ closed (spec 0087), ~~BL-68~~ ✓ closed
  (spec 0088 — D4's real-terminal-launch leg remains user-acceptance-pending),
  ~~BL-69~~ ✓ closed (spec 0080), ~~BL-70~~ ✓ closed (spec 0080).
- **Every finding from this audit is now resolved or superseded**, leaving
  only: spec 0088 D4's real-terminal-launch check (user acceptance); BL-71
  Part A (poe-executor fragility — applied to the two deploy-aur tasks by
  spec 0084, but still a standing rule for any *future* poe task that shells
  out to `makepkg`); and, of the three namcap-sourced follow-on items
  (BL-72–BL-74, `kb/backlog.md`), only **BL-74** (RELRO/PIE hardening) still
  open — ~~BL-72~~ ✓ closed (spec 0092) and ~~BL-73~~ ✓ closed (spec 0093).

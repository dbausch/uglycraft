# Spec 0080 — Package the full UGLYCRAFT module set (BL-61)

Backlog: **BL-61 (P1)** — release blocker. Both PKGBUILDs install a **hardcoded
list of 8 Python modules**; the game is now **16** modules, so the packaged
`uglycraft` crashes on launch (`ModuleNotFoundError`) before the window opens.
Replace the stale explicit list with a glob so the package always ships every
module and can never drift again.

→ Audit + full finding: `kb/arch-packaging.md`. → Packaging layout: `CLAUDE.md`
§ *Arch packaging*. No automated packaging test suite exists, so verification is
a headless import smoke test + a manual launch (this section replaces the
"Tests" gate for packaging work, per `CLAUDE.md` step 3).

## Status checklist

- [ ] **I1** — `packaging/PKGBUILD` (`package_uglycraft`): the explicit 8-module
  `install` is replaced by `install -m644 *.py "$pkgdir/usr/share/uglycraft/"`,
  run from the source root that already exists (`cd "$pkgbase-$pkgver"`), after
  the existing `install -d`.
- [ ] **I2** — `packaging/PKGBUILD-git` (`package_uglycraft-git`): the identical
  change (source root is `cd "$pkgbase"`).
- [ ] **I3** — the built package's `usr/share/uglycraft/*.py` set is **exactly**
  the tracked root modules — all 16, including the 7 runtime modules missing
  today (`hud`, `world`, `crafting`, `cells`, `rooms`, `levelgraph`,
  `levellayout`) and `leveldump`.
- [ ] **I4** — headless import smoke: the shipped `main.py --dump-level N` runs
  against **only** the packaged files and exits 0, exercising the whole import
  chain.
- [ ] **I5** — Daniel confirms the installed `uglycraft` launches to the menu
  (and plays) with no `ModuleNotFoundError`.

## Background — confirmed facts

Established by reading the code / packaging (self-contained; do not re-derive):

### What ships today, and why it breaks

`package_uglycraft` (`PKGBUILD:46-48`) does:

```bash
install -d "$pkgdir/usr/share/uglycraft"
install -m644 main.py game.py constants.py sprites.py levels.py \
  entities.py hiscore.py sounds.py "$pkgdir/usr/share/uglycraft/"
```

Eight modules. `PKGBUILD-git:50-52` is byte-identical apart from the source dir.
The wrapper (installed into `/usr/bin/uglycraft`) runs
`python /usr/share/uglycraft/main.py`. Python puts the script's directory on
`sys.path[0]`, so sibling imports resolve **only** against what was installed.
The import chain requires seven modules that are **not** installed:

- `main` → `game` (`main.py:22`); `game` → `hud` (`:12`), `world` (`:17`),
  `crafting` (`:18`)
- `world` → `rooms`, `cells`, `crafting`, `levels`; `rooms` → `cells`,
  `entities`; `levels` → `levelgraph`, `levellayout`, `crafting`;
  `sprites` → `crafting`

So the very first import (`game.py:12`, `from hud import …`) raises
`ModuleNotFoundError` and the game never starts. The `ugli`/`ugli-git` (Pascal)
packages are unaffected — they ship a compiled binary, not these modules.

### The module set is closed and glob-safe

`git ls-files '*.py' | grep -v /` returns **exactly 16** files — the whole game
surface and nothing else:

```
cells constants crafting entities game hiscore hud leveldump
levelgraph levellayout levels main rooms sounds sprites world
```

There is no root `setup.py`, `conftest.py`, or dev script; `tests/` is a
subdirectory. A non-recursive `*.py` glob (run from the source root) matches
precisely these 16 and never descends into `tests/`, `original/`, or `fonts/`.
The GitHub release tarball and a fresh git clone both contain only tracked
files, and nothing in `prepare()`/`build()` writes a root-level `.py`
(`git_sha.inc` and the copied `uos/*.pas` live under `original/`), so the glob
stays clean across rebuilds. `leveldump` is lazily imported at `main.py:71`
(debug-only `--dump-level`); the glob ships it too, at no cost.

### `--dump-level` is a headless-capable smoke path

`leveldump.py` is the pygame-free ASCII exporter (`CLAUDE.md` architecture
table). Running `main.py --dump-level N` goes through the real `start_level`
path and prints a level, then exits — it imports `pygame` transitively (a
declared dependency, importable without a display) but never opens a window. It
therefore exercises the entire previously-broken import graph
(`game`→`hud`/`world`/`crafting`→`rooms`/`cells`/`levels`→`levelgraph`/`levellayout`,
plus `leveldump`) on a machine with no display — the ideal package smoke test.

## I1 / I2 — Replace the explicit list with a glob

In `package_uglycraft` (`PKGBUILD`) and `package_uglycraft-git` (`PKGBUILD-git`),
change the module install to:

```bash
install -d "$pkgdir/usr/share/uglycraft"
# Ship every top-level game module.  The repo root holds exactly the 16 game
# .py files (tests/ is a subdir); a glob keeps the package from going stale as
# modules are split/added — the hardcoded list previously dropped 7 runtime
# modules and broke launch (BL-61).
install -m644 *.py "$pkgdir/usr/share/uglycraft/"
```

Everything else in both package functions is unchanged (fonts, translations,
the wrapper heredoc, desktop entry, icon, licenses). No change to
`package_ugli`/`package_ugli-git`. **No `.SRCINFO` regeneration is needed** — the
`install` body is not part of `.SRCINFO`; no metadata field
(`depends`/`provides`/`license`/…) changes here (field fixes are BL-62/64, and
regeneration is BL-66).

## I3 — Verify the shipped module set

Build the release package and diff the shipped modules against the tracked set:

```bash
cd packaging && makepkg -f            # builds all four split packages (needs fpc)
# expect: identical lists, 16 modules
diff <(tar tf uglycraft-*-x86_64.pkg.tar.zst \
        | sed -n 's#^usr/share/uglycraft/\([^/]*\.py\)$#\1#p' | sort) \
     <(cd .. && git ls-files '*.py' | grep -v / | sort)
```

The diff must be empty and must include the seven modules missing today
(`hud world crafting cells rooms levelgraph levellayout`) plus `leveldump`.

## I4 — Headless import smoke test

Extract the built package to a scratch dir and run the shipped entry point
through the pygame-free dump path — this imports **only** the packaged files:

```bash
tmp=$(mktemp -d)
tar xf packaging/uglycraft-*-x86_64.pkg.tar.zst -C "$tmp"
python "$tmp/usr/share/uglycraft/main.py" --dump-level 3 --seed 1
echo "exit: $?"     # must be 0, and must print an ASCII level (no ModuleNotFoundError)
```

A missing module surfaces here as an `ImportError`/non-zero exit. (Run with the
distro `python` that has `pygame`/`numpy`, matching the package's `depends`.)

## I5 — User acceptance

Daniel installs the package (`sudo pacman -U packaging/uglycraft-*-x86_64.pkg.tar.zst`)
and runs `uglycraft`, confirming it reaches the menu and a level plays with no
`ModuleNotFoundError`. Per `CLAUDE.md` step 5 this item may be ticked **only**
after Daniel says so — a clean build/exit code is not acceptance.

## Out of scope

- The other audit items — redundant `provides` (BL-62), release checksum
  (BL-63), OFL-1.1 license (BL-64), source pinning (BL-65), `.SRCINFO`
  regeneration (BL-66), and the P3 polish (BL-67–70). This spec is *only* the
  broken module set.
- Any change to `ugli`/`ugli-git`, to the wrapper, or to non-`.py` assets.
- Byte-compilation of the shipped modules (BL-69) — orthogonal.
- **Assumption to preserve:** the repo root stays "shippable modules only." If a
  non-shippable top-level `.py` is ever added (a dev/util script), the glob must
  be revisited (exclude it, or move the script into a subdir); I3's set-equality
  check is the guard that would catch it.

## Done when:

- [ ] **I1** — `package_uglycraft` installs `*.py` (all 16 modules), not the
  8-module list.
- [ ] **I2** — `package_uglycraft-git` makes the identical change.
- [ ] **I3** — the built package's `usr/share/uglycraft/*.py` set equals
  `git ls-files '*.py' | grep -v /` (16 modules; empty diff).
- [ ] **I4** — the headless `main.py --dump-level` smoke test against the
  extracted package exits 0 and prints a level.
- [ ] **I5** — Daniel confirms the installed `uglycraft` launches and plays with
  no `ModuleNotFoundError`.

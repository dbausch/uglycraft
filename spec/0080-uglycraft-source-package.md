# Spec 0080 — Move UGLYCRAFT source into a `uglycraft/` package (BL-61)

Backlog: **BL-61 (P1)** — release blocker. The packaged game ships only 8 of its
16 modules and crashes on launch. The **root cause** is a hand-maintained module
list that went stale; the proper fix is to give the game a real **package
directory named after the distribution** (`uglycraft/`), run as
`python -m uglycraft`. Packaging then ships **one directory** and can never drift
again, and the layout follows the standard Python convention.

> **Supersedes** this spec's earlier minimal-glob approach (install `*.py` in the
> flat root — see this file's git history). Daniel chose the full restructure
> (decision 2026-07-16) so the release ships the proper layout. The glob would
> have unblocked BL-61 but left the flat root; the restructure fixes the cause.

This is a **cross-cutting refactor** — imports, entry point, assets, both
PyInstaller builds, both PKGBUILDs, and the test suite all move with it.
→ Audit: `kb/arch-packaging.md`. → Packaging layout: `CLAUDE.md` § *Arch packaging*.

The pytest suite is the red/green safety net for the import rewrite (D2/D6);
packaging/build correctness is verified manually (no packaging test suite),
per `CLAUDE.md` step 3.

## Status checklist

- [x] **D1** — the 16 game modules move from the repo root into a new
  `uglycraft/` package (`uglycraft/__init__.py` added), via `git mv` to preserve
  history.
- [x] **D2** — intra-package imports become absolute (`from uglycraft.constants
  import …`, `from uglycraft import world`) — only the 16 local names, never
  stdlib/`pygame`/`numpy`.
- [x] **D3** — `uglycraft/__main__.py` added (`from uglycraft.main import main;
  main()`) so `python -m uglycraft` runs the game; a thin repo-root launcher
  (`run_game.py`) exists for the PyInstaller entry.
- [x] **D4** — `fonts/` and `translations/` move into `uglycraft/`; the
  `__file__`-relative loader (`game.py:119,1124`) is unchanged and now resolves
  under the package; the `_MEIPASS` branch is unchanged.
- [x] **D5** — `poe run` → `python -m uglycraft`; both PyInstaller builds target
  `run_game.py` with `--add-data` sources repointed to `uglycraft/fonts/…` and
  `uglycraft/translations/…` (dest names `fonts`/`translations` unchanged).
- [x] **D6** — all `tests/` imports rewritten to the `uglycraft.` prefix; the
  full suite is green under `poe test`.
- [ ] **D7** — both PKGBUILDs install the `uglycraft/` package (site-packages,
  DEC-2) and the wrapper runs `python -m uglycraft`; the packaged game ships all
  modules — **closes BL-61**.
- [x] **D8** — living docs updated: `CLAUDE.md` architecture table (paths gain the
  `uglycraft/` prefix), `README.md` run instructions, `kb/arch-packaging.md`
  (package layout), root `CHANGELOG.md` if player-facing.
- [ ] **D9** — Daniel confirms `poe run`, the Linux PyInstaller build, and the
  AUR package all launch and play — font renders, history text loads, no
  `ModuleNotFoundError`.

## Decisions to confirm (forks in this spec)

These change the diff shape; flagged here for the confirmation gate. Recommended
option first.

- **DEC-1 — import style. → CHOSEN: absolute** (`from uglycraft.world import …`).
  *Absolute* intra-package **[chosen 2026-07-18:** gives the whole codebase **one**
  import dialect — package, `tests/`, `__main__.py`, and `run_game.py` all read
  `from uglycraft.x import y`; greppable; PEP 8 mildly prefers it and Google style
  mandates it for application code] vs *relative* (`from .world import …`, the
  spec's original recommendation for relocation-safety — a benefit an application
  that will never be renamed does not need). Since **tests use absolute either
  way**, absolute makes the entire tree uniform; relative would leave two dialects.
- **DEC-2 — install layout.** Install into **site-packages**
  (`$(python -c 'import site;print(site.getsitepackages()[0])')/uglycraft/`) +
  wrapper `python -m uglycraft` + `python -m compileall` **[recommended:**
  idiomatic per the Python guidelines; byte-compiles, folding in **BL-69]** vs
  keep the package under `/usr/share/uglycraft/` and run it via `PYTHONPATH`.
  Full PEP 517 wheel packaging (adding a `[build-system]`, `python-build`/
  `python-installer`, a `console_scripts` entry point) is the eventual "proper"
  end state but is **out of scope here** unless you want it now.
- **DEC-3 — also fix BL-70?** We touch `pyproject.toml [project]` for `run`/build
  anyway; opportunistically correct its stale `version`/year, or leave BL-70
  separate. **[recommended:** fix it here — it is one line and we are already in
  the file.]**

## Background — confirmed facts

Self-contained; established by reading the code (do not re-derive):

### Why a package, and why flat layout (not `src/`)

Three layouts exist; two are standard and **both** put the code in a package
directory:

- **src layout** — `src/uglycraft/…`. PyPA's current default recommendation; its
  main payoff (tests cannot accidentally import the in-repo copy instead of the
  installed one) matters most for *libraries* tested against an install.
- **flat layout** (PyPA's own term) — `uglycraft/…` in the repo root. Also fully
  standard.
- **loose top-level modules** — what UGLYCRAFT has *now*: 16 mutually-importing
  `.py` files in the root, no package at all (setuptools calls these
  `py_modules`). Normal for a single-file script; atypical and fragile for a
  16-module application — and it is the direct cause of BL-61, because a per-file
  install list goes stale.

For a **distributed application** (itch.io + AUR + two PyInstaller builds) a
package directory is the mainstream, correct layout — Django apps, the Flask
tutorial, and anything pip/pipx-installable are all packages; loose modules in the
root are common only for scripts that are *run in place and never installed*,
which UGLYCRAFT stopped being the moment it started shipping. We choose the **flat
layout** (`uglycraft/` in the root, run as `python -m uglycraft`): it is standard,
and `src/`'s isolation benefit is mostly ceremony for a game run from source while
`src/` would add a directory level to every asset path this spec already tracks.
Adopting `src/` — or a full PEP 517 wheel — remains an available later step, out
of scope here.

### Current layout is fully flat

All 16 game modules sit in the repo root and import each other **flat**
(`from constants import …`, `import world`). `git ls-files '*.py' | grep -v /`:

```
cells constants crafting entities game hiscore hud leveldump
levelgraph levellayout levels main rooms sounds sprites world
```

Nothing references a `uglycraft.` package today. `tests/` (a sibling of the
modules) imports the same flat names — ~90 import sites (`levelgraph` ×20,
`levellayout` ×18, `constants` ×15, `levels`, `world`, `crafting`, `game`,
`entities`, …). `fonts/` and `translations/` are also root siblings.

### Why BL-61 happens, and why the package fixes it

The wrapper runs `python /usr/share/uglycraft/main.py`; only the installed
sibling files are importable, and the PKGBUILD installed 8 of 16, so
`game.py:12` (`from hud import …`) raised `ModuleNotFoundError`. With a package
dir, the PKGBUILD installs the **whole** `uglycraft/` directory as one unit —
the list cannot go stale, which is the durable fix for BL-61.

### Entry point

`main.py` already defines `main()` and ends with `if __name__ == '__main__':
main()` (`main.py:66,141`). `--dump-level` (`main.py:70-75`) lazily imports
`leveldump` and is **pygame-free** (no window) — a headless smoke path.

### Assets are `__file__`-relative

`game.py:119-120` and `:1124-1125`:

```python
base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
ttf  = os.path.join(base, 'fonts', 'ShareTechMono-Regular.ttf')
...  os.path.join(base, 'translations', 'history_en.txt')
```

- Non-bundle branch: `dirname(__file__)` becomes `.../uglycraft/`, so the assets
  must live at `uglycraft/fonts/` and `uglycraft/translations/`. **Moving the
  asset dirs into the package keeps this code unchanged.**
- PyInstaller branch: `_MEIPASS` is the bundle root; `--add-data "src:fonts"`
  puts assets at `_MEIPASS/fonts`, and the join uses `'fonts'` — so the **dest**
  stays `fonts`/`translations`; only the **source** path in the build task moves.

### The `__main__` import pitfall

`python -m uglycraft` runs `uglycraft/__main__.py` with the package initialised,
so `from uglycraft.main import main` resolves. But PyInstaller runs its entry
*script* as `__main__` outside package context, where a relative/self import
would fail. Hence a **thin repo-root launcher** `run_game.py`:

```python
from uglycraft.main import main
main()
```

is the PyInstaller entry (root is on `sys.path`, so `uglycraft` imports cleanly).
`__main__.py` uses the same absolute `from uglycraft.main import main`.

## D1 / D2 — Create the package and rewrite intra-package imports

`git mv` each of the 16 modules into `uglycraft/`; add an (essentially empty)
`uglycraft/__init__.py`. Within the package, rewrite **only local** imports to
absolute package form (DEC-1): `from constants import X` → `from
uglycraft.constants import X`; the two lazy bare imports `import levels`
(`leveldump.py:181`) and `import leveldump` (`levellayout.py:2693`) → `from
uglycraft import levels` / `from uglycraft import leveldump` (preserves the
`levels.foo` / `leveldump.foo` call sites); the lazy `from leveldump import
dump_level` (`main.py:71`) → `from uglycraft.leveldump import dump_level`. Leave
every stdlib / `pygame` / `numpy` import untouched. The import **graph** is
unchanged (same edges, new names) so no new cycles are introduced. Script-assisted
(rewrite a line only when its imported name is in the 16-name allow-list) but
**reviewed per file**.

## D3 — `python -m uglycraft` + PyInstaller launcher

Add `uglycraft/__main__.py`:

```python
from uglycraft.main import main
main()
```

Keep `main.py`'s own `if __name__ == '__main__'` guard — harmless, but note it no
longer makes `python uglycraft/main.py` work: run by path, `main.py`'s top-level
`from uglycraft.… import` fails because the repo root is not on `sys.path` (and a
relative-style `from .` would fail even earlier with "attempted relative import
with no known parent package"). The supported entry is `python -m uglycraft`. Add
repo-root `run_game.py` (the launcher above) as the PyInstaller entry.

## D4 — Move the asset directories

`git mv fonts uglycraft/fonts` and `git mv translations/history_en.txt
uglycraft/translations/history_en.txt` (create `uglycraft/translations/`). The
game's asset code is **unchanged** (D-background). Note: `original/translations`
and `original/`’s own assets are **separate** and untouched.

## D5 — Task + build updates

- `poe run` (`pyproject.toml:24`): `.venv/bin/python -m uglycraft`.
- `build-linux` (`:72-75`): entry `run_game.py`; `--add-data
  "uglycraft/fonts/ShareTechMono-Regular.ttf:fonts"` and
  `"uglycraft/translations/history_en.txt:translations"`.
- `build-windows` (`:95-97`): same, with the Windows `;` separator.
- `--name uglycraft` and the onefile/noconsole flags are unchanged.

## D6 — Test import rewrite

Rewrite `tests/` local imports to the package: `from world import X` →
`from uglycraft.world import X`; `import levels` → `from uglycraft import levels`
(preserves `levels.foo` call sites). Same 16-name allow-list. `poe test` must be
**green** afterwards — this is the red→green net proving D2/D6 correct. `poe
test -- -n0` for a clean serial run if xdist noise obscures a failure.

## D7 — PKGBUILD install (both release and git)

Per DEC-2 (site-packages). In `package_uglycraft` / `package_uglycraft-git`,
replace the loose-module install with:

```bash
_site=$(python -c "import site; print(site.getsitepackages()[0])")
install -d "$pkgdir$_site"
cp -r uglycraft "$pkgdir$_site/"
python -m compileall "$pkgdir$_site/uglycraft"     # BL-69 falls out here
```

and change the wrapper body to `exec python -m uglycraft "$@"`. The separate
`fonts/` and `translations/` install lines are **removed** — those assets now
ride inside the copied package (`uglycraft/fonts`, `uglycraft/translations`).
Licenses, desktop entry, and icon installs are unchanged. `package_ugli` /
`ugli-git` (the Pascal port) are **untouched**. `arch` stays as-is here (any
`arch=('any')` refinement is BL-67, separate). No `.SRCINFO` field changes → no
regeneration needed for this spec (that concern is BL-66).

## D8 — Living docs

`CLAUDE.md` architecture table: prefix the 16 file paths with `uglycraft/` and
note `run_game.py` + `__main__.py`. `README.md`: run instructions become
`python -m uglycraft` / `poe run`. `kb/arch-packaging.md`: update BL-61's entry
and the install-path notes to the package layout. Root `CHANGELOG.md`: only if
there is a player-facing effect (there is not, beyond "packaged build now runs").

## D9 — Verification

1. **Suite** — `poe test` green (D2/D6 net).
2. **Headless import** — `python -m uglycraft --dump-level 3 --seed 1` prints a
   level and exits 0 (drives the whole import graph, pygame-free).
3. **Dev run** — `poe run` launches to the menu; font + history screen render.
4. **Linux build** — `poe build-linux`; the onefile binary in `dist/linux-64/`
   launches and plays (assets bundled). (`build-windows` likewise if Wine is set
   up — at minimum confirm it builds.)
5. **Package** — `cd packaging && makepkg -f`; the built `uglycraft` package
   contains `…/site-packages/uglycraft/` with all 16 modules + assets; install
   and run `uglycraft` — reaches the menu, no `ModuleNotFoundError` (**BL-61
   closed**).
6. **User acceptance (D9)** — Daniel confirms 3–5 work in-game. Ticked only after
   he says so (a clean exit code is not acceptance, `CLAUDE.md` step 5).

## Out of scope

- The other audit items — redundant `provides` (BL-62), release checksum
  (BL-63), OFL-1.1 license (BL-64), source pinning (BL-65), `.SRCINFO`
  regeneration (BL-66), `arch=any` (BL-67), binary location (BL-68). BL-69
  (byte-compile) and BL-70 (pyproject metadata) fold in *only* via DEC-2/DEC-3 if
  chosen.
- Full PEP 517 wheel packaging with a `console_scripts` entry point (a later,
  optional step — see DEC-2).
- Any gameplay, generator, or asset-content change; the Pascal `ugli` port.

## Done when:

- [x] **D1** — the 16 modules live under `uglycraft/` with `__init__.py`
  (history-preserving `git mv`). — `5a99c71`
- [x] **D2** — intra-package imports are absolute and correct (suite green). —
  `5a99c71`
- [x] **D3** — `python -m uglycraft` runs the game; `run_game.py` launcher exists.
  — `5a99c71` (both entry points verified headless via `--dump-level`, identical
  output; in-game menu is part of D9)
- [x] **D4** — assets moved into the package; loader code unchanged. — `5a99c71`
  (font present + loadable — `test_overlay_box` passes)
- [x] **D5** — `poe run` and both PyInstaller builds target the package/launcher
  with repointed `--add-data`. — `5a99c71` (Linux onefile builds and runs headless;
  Windows targets verified by inspection, Wine build is D9)
- [x] **D6** — `tests/` imports use the `uglycraft.` prefix; `poe test` green. —
  `5a99c71` (895 passed, 0 failed)
- [ ] **D7** — both PKGBUILDs install the package (+ wrapper `python -m
  uglycraft`); packaged game ships every module — BL-61 closed. *(PKGBUILD edits
  in `8c70f7b`; install simulation ships all 18 `.py` + assets + bytecode. Awaits
  `makepkg` + install + in-game run — folded into D9.)*
- [x] **D8** — `CLAUDE.md`, `README.md`, `kb/arch-packaging.md` reflect the layout.
  — `a9892ac`
- [ ] **D9** — Daniel confirms dev run, Linux build, and AUR package all launch
  and play with assets and no `ModuleNotFoundError`.

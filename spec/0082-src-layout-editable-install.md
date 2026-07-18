# Spec 0082 — `src/` layout + editable install for the `uglycraft` package

Adopt the standard PyPA **`src/` layout** and make `uglycraft` a **properly
installed package** (`pip install -e .` into `.venv`, backed by a real
`[build-system]`). This is the durable fix for the frozen-build asset breakage
found while verifying spec 0080 D9 (the `--collect-data uglycraft` "not a
package" bug — see **Background**), and the natural next step after spec 0080
turned the loose modules into a package.

Spec 0080 deliberately chose the **flat layout** and a **cp-into-site-packages**
install, explicitly naming `src/` + full build-system packaging as an available
*later step, out of scope there*. This is that step. → 0080 §*Why a package, and
why flat layout*, DEC-1, DEC-2.

**Relationship to spec 0080.** 0082 **supersedes 0080 DEC-1** (flat layout) and
**extends 0080 DEC-2** (adds a dev-time editable install; the AUR install method
is revisited in DEC-4 below). Once 0082 lands, **0080 D9's Linux-build leg and
D10's frozen-font re-verification can close** — they are blocked today purely by
this bug. 0080 D7 / BL-61 (the AUR package) are **unaffected** and stay closed:
that path is a filesystem `cp -r`, not an import.

→ Packaging audit: `kb/arch-packaging.md`. → Packaging process: `CLAUDE.md`
§*Arch packaging*.

## Status checklist

- [x] **D1** — the `uglycraft/` package moves to `src/uglycraft/` via history-
  preserving `git mv` (all 16 modules + `__init__.py` + `__main__.py` +
  `fonts/` + `translations/`); `run_game.py` stays at the repo root. —
  e3e0c6a, fab3cd5
- [x] **D2** — `pyproject.toml` gains a real `[build-system]` (setuptools) and
  `src/` packaging config (`package-dir`, `packages.find where=["src"]`,
  package-data for `fonts`/`translations`); `[project]` deps are split into
  runtime vs. a `dev`/build extra. — 6686493
- [x] **D3** — `poe install` creates the venv and runs `pip install -e ".[dev]"`,
  so `uglycraft` is importable in **every** interpreter (dev shell, pytest,
  PyInstaller's build process). This is the load-bearing change. — 6686493
- [x] **D4** — `poe run` / `poe test` / `build-linux` / `build-windows` work with
  **no `PYTHONPATH`** and **no source-dir path juggling**; `--collect-data
  uglycraft` now resolves and bundles the assets (the D9/D10 fix). — verified
  (no task references `PYTHONPATH`; `poe build-linux` runs warning-free, see D9)
- [x] **D5** — both PKGBUILDs change their source path `cp -r uglycraft` →
  `cp -r src/uglycraft`; the installed site-packages layout, wrapper, compileall,
  and bundled assets are **unchanged**. — d24eb4d
- [x] **D6** — the `game.py` `__file__`-only asset loader is unchanged and still
  resolves from `src/uglycraft/…` (source) and `_MEIPASS/uglycraft/…` (frozen).
  — verified (no diff to `game.py`; frozen-binary asset check under D9 confirms
  both paths resolve)
- [x] **D7** — the full pytest suite is green under `poe test` after the move +
  install (import statements stay `uglycraft.*`; `conftest.py` unchanged). —
  4160602 (fixed one stale repo-root-relative path in `test_overlay_box.py`);
  895 passed on rerun
- [x] **D8** — living docs updated: `CLAUDE.md` architecture table (paths gain
  `src/`), `README.md` (install via `poe install` / `pip install -e .`),
  `kb/arch-packaging.md` (record the root cause + the install-based layout),
  `kb/architecture.md` if it names the layout. — 5ea44b0 (`kb/architecture.md`
  doesn't name the layout, so it needed no change)
- [x] **D9** — Daniel confirms: suite green, `poe run` renders font + history, and
  the **Linux binary** builds with **no `--collect-data` warning** and runs with
  font + story (closing 0080 D9 Linux leg + re-validating D10); `makepkg` install
  still works from the `src/` source path. — **dev run and Linux binary
  confirmed by Daniel, 2026-07-18**. `makepkg` resolved via `packaging/
  PKGBUILD-dev` (spec 0083): rebuilt fresh against HEAD `9a5f8aa` (pushed to
  gitolite same day) — `poe package-dev` succeeds, `pkgver` reports
  `1.5.r673.g9a5f8aa` matching `git describe` exactly, the package layout
  (`cp -r src/uglycraft` → `usr/lib/python3.14/site-packages/uglycraft/` with
  all 16 modules + `fonts/` + `translations/`) is correct, and an
  extracted-tree headless run confirms the font and history text both load.
  This exercises the exact same `package_uglycraft()` logic as `PKGBUILD`/
  `PKGBUILD-git` — the actual AUR-facing PKGBUILDs still haven't been
  build-tested themselves, since both hardcode `url='https://github.com/
  dbausch/uglycraft'` and a gitolite-only push doesn't change that; a real
  check of those two needs an actual GitHub push (still on hold) or a new
  release tag.

## Decisions (forks) — all confirmed 2026-07-18

Recommended option first; each now marked **CHOSEN**.

- **DEC-1 — build backend. → CHOSEN: setuptools** (`setuptools.build_meta`), the current default backend.
  **[recommended:** already the de-facto stdlib backend, needs no new tooling,
  and supports the `src/` + `package-dir` config out of the box] vs. hatchling /
  flit (nicer TOML but a new dependency for zero functional gain here).
- **DEC-2 — console entry point. → CHOSEN: add it.** Add `[project.scripts] uglycraft =
  "uglycraft.main:main"` **[recommended:** costs one line; a real installed
  `uglycraft` command falls out for the editable install, and it is the hook a
  future *wheel-based* AUR install (DEC-4) would use to drop `/usr/bin/uglycraft`
  automatically]. The AUR package **keeps its shell wrapper** (`exec python -m
  uglycraft`) for now regardless — switching it is DEC-4. `main.main` already
  exists and is the correct target (`main.py:66,141`).
- **DEC-3 — `requirements.txt` fate. → CHOSEN: fold into pyproject, delete it.** Fold it into `pyproject.toml`
  (`[project].dependencies` = runtime: `pygame`, `numpy`;
  `[project.optional-dependencies].dev` = `pyinstaller`, `pytest`,
  `pytest-xdist`, `hypothesis`) and delete `requirements.txt`, updating
  `poe install` **[recommended:** single source of truth; `pyinstaller`/`pytest`
  are build/test tools, not runtime deps of the game — today they are wrongly in
  `[project].dependencies`]. `requirements-docs.txt` (MkDocs, spec 0081) is
  **separate and untouched**. Alternative: keep a one-line `requirements.txt`
  (`-e .[dev]`) as a compat shim.
- **DEC-4 — AUR install method. → CHOSEN: keep `cp -r src/uglycraft` (wheel install = later spec).** **Keep `cp -r src/uglycraft` into
  site-packages** (+ `compileall`, as spec 0080 D7) **[recommended for 0082:**
  minimal, does not destabilize the just-fixed AUR packaging, installed layout
  identical]. The "proper" alternative — build a wheel (`python -m build`) and
  install it (`python -m installer`), giving real dist metadata + the DEC-2
  console script — is the eventual end state but is its **own later spec** (it
  also touches `.SRCINFO`/BL-66 and the `depends` set).

## Background — confirmed facts

Self-contained; do not re-derive.

### The bug this fixes: `--collect-data uglycraft` silently bundles nothing

Discovered verifying 0080 D9. `poe build-linux` prints:

```
WARNING: collect_data_files - skipping data collection for module 'uglycraft'
as it is not a package.
```

and the resulting binary crashes at launch:

```
FileNotFoundError: '/tmp/_MEIs366wb/uglycraft/fonts/ShareTechMono-Regular.ttf'
  run_game.py:11 → uglycraft/main.py:101 → game.py:120
  self.font_big = pygame.font.Font(ttf, 36)
```

**Root cause** (traced through PyInstaller 6.20 source, reproduced both ways).
`--collect-data uglycraft` calls `collect_data_files('uglycraft')`, which first
calls `is_package('uglycraft')`. For a **top-level** name that check runs **in
the pyinstaller process itself** (`utils/hooks/__init__.py`: `is_package` →
`_is_package` → `importlib.util.find_spec('uglycraft')`; the isolated-subprocess
path is only taken for dotted names). The `pyinstaller` console-script's
`sys.path` is the venv only — it does **not** include the repo root or the cwd —
and `uglycraft` is **not installed in the venv** (`pip show uglycraft` → not
found). So `find_spec` returns `None`, `is_package` returns `False`, the warning
fires, and **zero** data files are collected → the font/translations never enter
the bundle.

Empirically confirmed with the project venv (PyInstaller 6.20.0, Python 3.14):

| condition | `is_package('uglycraft')` | `collect_data_files` |
|---|---|---|
| repo root **not** on the process path (the real build) | `False` | `[]` + warning |
| repo root on `PYTHONPATH` **or** package installed | `True` | both asset dirs |

(An earlier `python -c` reproduction *looked* fine only because `python -c`
prepends the cwd to `sys.path`; the real `pyinstaller` executable does not. This
is why 0080 D10's `--collect-data` "verified" once and fails now — it is
inherently environment-dependent for a **run-from-source, never-installed**
package.)

**Why installing the package is the fix — not `PYTHONPATH`.** Making `uglycraft`
a real (editable) install puts it on the venv's own `sys.path`, so `find_spec`
succeeds in the pyinstaller process (and every other process) with **no** env
juggling, cwd assumption, or Wine-side `PYTHONPATH` special-casing. `--collect-
data` then becomes *correct* rather than *coincidental* — D10's instinct was
right; it was only missing the install step that makes a package importable.

### Why `src/` (and not just "install the flat package")

An editable install alone fixes the build. `src/` adds **enforcement**: in a
flat layout the repo-root copy is still importable directly (cwd shadows the
install), which is exactly the ambiguity that hid "this package isn't really
installed." Under `src/uglycraft/`, the in-repo copy is **not** importable unless
installed, so the only `uglycraft` that ever loads is the installed one —
removing the shadow trap structurally. This is the PyPA-recommended layout; 0080
weighed and deferred it, and the D9 bug is the concrete cost of having deferred
it. `src/` also gives the future `src/ugli` sibling a natural home (see
*Out of scope*).

### What does **not** change

- **Runtime import paths** — the installed package is still `uglycraft` at the
  top level (`package-dir = {"" = "src"}` maps `src/uglycraft` → import name
  `uglycraft`). `python -m uglycraft`, `from uglycraft.x import y`, and all ~90
  test import sites are **unchanged**.
- **Installed/AUR layout** — still `site-packages/uglycraft/` with assets inside;
  the wrapper still runs `python -m uglycraft`. Only the PKGBUILD's **source**
  path (`src/uglycraft`) changes (D5).
- **The asset loader** — `game.py`'s `__file__`-only base
  (`os.path.dirname(os.path.abspath(__file__))`, 0080 D10) resolves to
  `…/src/uglycraft` from source and `_MEIPASS/uglycraft` when frozen; both hold
  the assets. No code change (D6).
- **`.gitignore`** — already ignores `*.egg-info/` (matches the new
  `src/uglycraft.egg-info/`), `.venv/`, `build/`, `dist/`, `*.spec`. No change
  expected.

## D1 — Move to `src/`

`git mv uglycraft src/uglycraft` (single move preserves history for the whole
subtree: 16 modules, `__init__.py`, `__main__.py`, `fonts/`,
`translations/history_en.txt`). `run_game.py` **stays at the repo root** — it is
the PyInstaller entry and imports the installed `uglycraft` (its docstring's
"repo root is on sys.path" rationale becomes "the package is installed"; update
the comment). No import statements change.

## D2 — `pyproject.toml`: build-system + `src/` packaging

Add:

```toml
[build-system]
requires      = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
uglycraft = ["fonts/*.ttf", "translations/*.txt"]
```

Restructure `[project]` (DEC-3): `dependencies = ["pygame>=2.0", "numpy"]`;
`[project.optional-dependencies] dev = ["pyinstaller", "pytest", "pytest-xdist",
"hypothesis"]`. Optionally (DEC-2) `[project.scripts] uglycraft =
"uglycraft.main:main"`. `version`/`description` already corrected (BL-70,
`4968c08`).

`package-data` is for a built **wheel** (future AUR / DEC-4); the **editable**
dev install reads assets straight from `src/uglycraft/…`, and PyInstaller uses
`--collect-data` (D4) — so nothing at dev/runtime depends on `package-data`, but
it keeps a wheel correct and is cheap to include.

## D3 — Editable install workflow

`poe install` becomes:

```
virtualenv .venv && .venv/bin/pip install -e ".[dev]"
```

This installs the runtime deps, the dev/build tools, **and** the project itself
in editable mode — the step that makes `uglycraft` importable everywhere. Delete
`requirements.txt` (DEC-3) or reduce it to `-e .[dev]`. `docs-install` /
`requirements-docs.txt` are untouched.

**Note for the working `.venv`:** existing checkouts must re-run `poe install`
(or `.venv/bin/pip install -e ".[dev]"`) once so the current venv gains the
editable install — otherwise the build still sees no `uglycraft`. Call this out
in D9 verification and the README.

## D4 — Tasks need no `PYTHONPATH`

With the editable install, `run` (`python -m uglycraft`), `test` (`pytest
tests/`), `build-linux`, and `build-windows` (`pyinstaller … --collect-data
uglycraft run_game.py`) all resolve `uglycraft` from the venv. Concretely:
`--collect-data uglycraft` now finds the package → `is_package` True → both asset
dirs collected → bundle gets `uglycraft/fonts/…` + `uglycraft/translations/…`.
No task text needs `PYTHONPATH`; confirm none references a flat-root path.

## D5 — PKGBUILDs: source path only

In `package_uglycraft` **and** `package_uglycraft-git`, change the one line
`cp -r uglycraft "$pkgdir$_site/"` → `cp -r src/uglycraft "$pkgdir$_site/"`.
Everything else is unchanged: `_site` discovery, `compileall`, the
`exec python -m uglycraft` wrapper, and the assets riding inside the copied
package. The **installed** tree is byte-for-byte the same, so no `.SRCINFO`
metadata change and no wrapper/runtime-path change. `package_ugli` / `ugli-git`
are untouched (their `src/ugli` move is a later spec).

## D6 — Loader unchanged

Confirm (no edit): from source, `game.py:119`'s base resolves to
`…/src/uglycraft`; frozen, to `_MEIPASS/uglycraft`. Assets sit at
`fonts/`/`translations/` under each. The 0080 D10 `__file__`-only loader already
handles both; the `src/` move only lengthens the source path.

## D7 — Suite green (red/green net)

The move is behaviour-preserving; the existing **895-test** suite is the safety
net. After D1–D3, `poe test` must be green with **no import changes**
(`uglycraft.*` throughout; `conftest.py` uses plain package imports, no
`sys.path` hacks — verified). `poe test -- -n0` for a clean serial run if xdist
noise obscures a failure. `test_overlay_box` loads the real font from
`src/uglycraft/fonts`, exercising the asset path from source.

## D8 — Living docs

`CLAUDE.md` architecture table: prefix package paths with `src/`. `README.md`:
setup is `poe install` (now an editable install) and note `pip install -e .` for
manual setups; run stays `poe run` / `python -m uglycraft`.
`kb/arch-packaging.md`: record the `collect_data_files`/`is_package` root cause
(above) and update BL-61/D7 notes to the `src/` install-based layout.
`kb/architecture.md`: update if it names the top-level layout. Root
`CHANGELOG.md`: only if player-facing (it is not — packaged runtime is
unchanged).

## D9 — Verification

1. **Fresh install** — `poe install` (or re-`pip install -e ".[dev]"` in the
   existing venv) succeeds; `.venv/bin/python -c "import uglycraft; print('ok')"`
   works from an arbitrary cwd. — ✓ self-verified 2026-07-18 (import from `/tmp`
   resolved to `src/uglycraft/__init__.py`).
2. **Suite** — `poe test` green. — ✓ self-verified 2026-07-18 (895 passed after
   the `test_overlay_box.py` fix, 4160602).
3. **Headless import** — `python -m uglycraft --dump-level 3 --seed 1` exits 0
   (drives the import graph, pygame-free). — ✓ self-verified 2026-07-18 (exit 0
   from an unrelated cwd, both the dev interpreter and the frozen binary).
4. **Dev run** — `poe run` renders font + history. — ✓ **confirmed by Daniel**,
   2026-07-18.
5. **Linux build** — `poe build-linux`: **no `collect_data_files` warning**; the
   onefile binary in `dist/linux-64/` launches and plays with font + story
   (this is the 0080 D9/D10 fix — verify the assets are actually in the bundle,
   e.g. a onedir probe or kept-tmp extraction shows `uglycraft/fonts/…` +
   `uglycraft/translations/…`). `build-windows` at least builds (Wine),
   likewise warning-free. — ✓ **confirmed by Daniel** (`poe build-linux && dist/
   linux-64/uglycraft`), 2026-07-18; warning-free build and bundled-asset check
   (`pyi-archive_viewer`) also self-verified same day. `build-windows` (Wine)
   not yet re-checked.
6. **Package** — `cd packaging && makepkg -f`: builds from the `src/` source,
   installs `…/site-packages/uglycraft/` with all modules + assets; the installed
   `uglycraft` reaches the menu (BL-61 stays closed). — **not yet run**: both
   PKGBUILDs source from the pushed GitHub tag/repo, so a real `makepkg -f`
   needs these commits pushed first. Structurally simulated locally instead
   (see D5 note above) — still open for a real AUR-side check.
7. **User acceptance (D9)** — Daniel confirms 4–5 in-game. Ticked only after he
   says so. — ✓ **confirmed by Daniel**, 2026-07-18 (items 4 and 5 above).

## Out of scope

- **`original/` → `src/ugli`** — Daniel's stated **later** want, and its own
  spec. It is large and unrelated to the Python package: it touches ~10 poe
  tasks (`run-original`, `build-original`, `test-original`, `build-replay`,
  `bench-original`, `make-pot`, `deploy-original-linux`/`-dos`, `clean`), the FPC
  `-Fuuos` unit search path and `original/uos/`, `original/translations/`, the
  `package_ugli` / `ugli-git` PKGBUILDs and `ugli.sh`, and many kb/spec path
  references. The `src/` layout established here is **designed to host
  `src/ugli` as a sibling**, so this spec unblocks that move without doing it.
- **Wheel-based AUR install** / full PEP 517 packaging with `console_scripts`
  install (folds in only if DEC-4's alternative is chosen — otherwise a later
  spec).
- Any gameplay, generator, or asset-content change; the Pascal `ugli` port
  itself.

## Done when:

- [x] **D1** — `src/uglycraft/` holds the package (history-preserving move);
  `run_game.py` at repo root. — e3e0c6a, fab3cd5
- [x] **D2** — `pyproject.toml` has `[build-system]` + `src/` packaging config +
  split runtime/dev deps. — 6686493
- [x] **D3** — `poe install` does `pip install -e ".[dev]"`; the package is
  importable from any cwd in the venv. — 6686493 (verified: `import uglycraft`
  from `/tmp` resolves to `.../src/uglycraft/__init__.py`)
- [x] **D4** — all tasks run with no `PYTHONPATH`; `--collect-data uglycraft`
  collects the assets (warning gone). — verified: `poe build-linux` prints no
  `collect_data_files`/"not a package" warning; `pyi-archive_viewer` shows
  `uglycraft/fonts/ShareTechMono-Regular.ttf` and
  `uglycraft/translations/history_en.txt` in the bundle
- [x] **D5** — both PKGBUILDs `cp -r src/uglycraft`; installed layout unchanged.
  — d24eb4d; structurally simulated locally (cp + compileall + import from an
  unrelated cwd all succeed) since a real `makepkg -f` needs the commits pushed
  to the GitHub tag/repo the PKGBUILDs source from
- [x] **D6** — asset loader unchanged and resolving from source + frozen. —
  no diff to `game.py`; confirmed resolving in both the dev venv and the frozen
  binary
- [x] **D7** — `poe test` green after the move. — 4160602; 895 passed on rerun
  (one unrelated Hypothesis deadline flake on the first run reproduced green in
  isolation)
- [x] **D8** — `CLAUDE.md`, `README.md`, `kb/arch-packaging.md`
  (+ `kb/architecture.md` if needed) reflect the `src/` install-based layout. —
  5ea44b0
- [x] **D9** — Daniel confirms suite + dev run + a warning-free Linux binary that
  renders font + story, and a working `makepkg` install (closes 0080 D9/D10). —
  dev run + Linux binary confirmed 2026-07-18; `makepkg` verified the same day
  via `PKGBUILD-dev` (spec 0083) against gitolite-pushed HEAD `9a5f8aa` — same
  install logic as the real AUR PKGBUILDs, which still need an actual GitHub
  push/release tag for their own direct check.

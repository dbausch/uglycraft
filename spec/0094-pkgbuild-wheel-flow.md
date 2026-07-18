# Spec 0094 — PEP 517 wheel flow for the `uglycraft` split package (BL-71 root fix)

## Status

- [ ] D1 — `build()` builds a wheel: `python -m build --wheel --no-isolation` (all three PKGBUILDs)
- [ ] D2 — `package_uglycraft*()` installs via `python -m installer --destdir="$pkgdir"` — `_site` detection, `cp -r`, and `compileall` removed (all three PKGBUILDs)
- [ ] D3 — hand-written `/usr/bin/uglycraft` bash wrapper replaced by the `[project.scripts]` entry point the installer generates
- [ ] D4 — `makedepends` extended with `python-build`, `python-installer`, `python-setuptools`
- [ ] D5 — `.SRCINFO` / `.SRCINFO-git` regenerated from the changed PKGBUILDs
- [ ] D6 — verified via `poe package-dev`: package builds, installs, game runs, no new namcap/makepkg warnings
- [ ] D7 — living documents updated (`kb/arch-packaging.md`, BL-71 closure note in `kb/backlog.md`, root `CHANGELOG.md`)

## Motivation

BL-71 Part A flagged the `_site=$(python -c "import site;
print(site.getsitepackages()[0])")` detection in all three
`package_uglycraft*()` functions as fragile: any invoker that puts a venv
`python` first on `PATH` (poethepoet's `"auto"` executor does exactly that)
silently redirects the whole install into venv-relative paths. The standing
guard is `executor = "simple"` on every poe task that runs `makepkg`.

The Arch Wiki's *Python package guidelines* (§ Installation methods) prescribe
a different install mechanism altogether — the PEP 517 flow: build a wheel
with `python-build`, install it with `python-installer`. Adopting it removes
the fragile machinery at the root instead of guarding it:

- **`_site` disappears entirely** — `installer` derives site-packages itself
  (BL-71 Part A becomes structurally impossible in the PKGBUILDs; the
  `executor = "simple"` rule stays as defence-in-depth for the invoker side).
- **`compileall` disappears** — `installer` byte-compiles by default and
  embeds correct runtime paths, obsoleting the `-d "$_site/uglycraft"`
  workaround from BL-71 Part B.
- **The hand-written `/usr/bin/uglycraft` heredoc wrapper disappears** —
  `pyproject.toml` already declares `[project.scripts] uglycraft =
  "uglycraft.main:main"`, the same function `python -m uglycraft` reaches;
  `installer` generates the entry-point script from it.
- The package gains proper `.dist-info` metadata (visible to
  `importlib.metadata` and pip, tracked by pacman).

The project is already PEP 517-ready: `build-backend =
"setuptools.build_meta"` (requires setuptools ≥ 61), `src/` layout declared
via `[tool.setuptools] package-dir`, and package data declared as
`[tool.setuptools.package-data] uglycraft = ["fonts/*.ttf",
"translations/*.txt"]` — which covers exactly the assets shipped today
(`fonts/ShareTechMono-Regular.ttf`, `translations/history_en.txt`).

## Changes

Applies identically to `packaging/PKGBUILD`, `packaging/PKGBUILD-git`, and
`packaging/PKGBUILD-dev` (function bodies are shared verbatim across the
three; only surrounding version/source plumbing differs).

### `build()`

Add the wheel build alongside the existing FPC build:

```bash
build() {
  cd "$pkgbase-$pkgver"          # or the -git/-dev source dir
  rm -rf dist
  python -m build --wheel --no-isolation
  cd original
  echo "const GitVersion = '$pkgver';" > git_sha.inc
  fpc -Fuuos UGLI_2.pp
}
```

`rm -rf dist` guards against stale wheels being matched by the `dist/*.whl`
glob in `package_uglycraft*()`. The wiki's tip for VCS packages is `git clean
-dfx` in `prepare()`; the narrower `rm -rf dist` is used uniformly in all
three PKGBUILDs instead, since the release variant builds from a tarball
(no git metadata) and only `dist/` matters here.

### `package_uglycraft*()`

Replace the manual install block:

```bash
  # BEFORE
  _site=$(python -c "import site; print(site.getsitepackages()[0])")
  install -d "$pkgdir$_site"
  cp -r src/uglycraft "$pkgdir$_site/"
  python -m compileall -q -d "$_site/uglycraft" "$pkgdir$_site/uglycraft"

  install -Dm755 /dev/stdin "$pkgdir/usr/bin/uglycraft" <<'WRAPPER'
#!/bin/bash
exec python -m uglycraft "$@"
WRAPPER

  # AFTER
  python -m installer --destdir="$pkgdir" dist/*.whl
```

The desktop file, icon, and license installs are unchanged. `package_ugli*()`
is untouched.

### `makedepends`

Add `python-build`, `python-installer`, `python-setuptools` (the build
backend; not currently in the repo's makedepends because nothing imported
setuptools at build time before).

### Metadata re-flow

`makedepends` is build metadata → `.SRCINFO` and `.SRCINFO-git` must be
regenerated (`makepkg --printsrcinfo`) in the implementing commit. The
deploy-time regeneration from spec 0084 provides a second net.

## Accepted deviations / notes

- **Wheel version stays `1.5` in `-git`/`-dev` builds.** `pyproject.toml`
  pins `version = "1.5"` statically; VCS pkgvers like `1.5.r20.g21ad119` are
  not valid PEP 440 and cannot be injected. Consequence: `.dist-info` claims
  1.5 regardless of pkgver. Cosmetic only — pacman's own version is the
  pkgver; accepted.
- **Asset staleness guard shifts.** Today `cp -r` ships whatever is in
  `src/uglycraft/` (BL-61's fix); after this change the
  `[tool.setuptools.package-data]` globs are the single source of truth, so a
  *new asset extension* (e.g. `.png`, `.mo`) would need a glob update or it
  silently vanishes from the wheel — same class of risk PyInstaller's
  `--collect-data uglycraft` already carries. Mitigated by the file-list
  comparison in the verification steps; noted in `kb/arch-packaging.md`.
- **The entry-point script's shebang** points at the interpreter that ran
  `installer` — the system `/usr/bin/python` under makepkg with a clean
  `PATH`. This is exactly why the `executor = "simple"` rule (BL-71 Part A)
  remains in force for `poe package-dev` and any future makepkg-running task.

## Non-goals

- No change to `package_ugli*()`, the PyInstaller/itch.io distributables, or
  the deploy tasks.
- No dynamic versioning (setuptools-scm etc.) — out of scope, see accepted
  deviations.

## Verification (manual — no automated suite covers packaging)

Vehicle: `poe package-dev` (spec 0083's local variant exists precisely to
exercise makepkg against local commits).

1. `poe package-dev` completes; makepkg's packaging-issue check reports zero
   `$pkgdir` references and no new warnings.
2. File-list diff old vs new package (`pacman -Qlp` on both): identical
   modulo the expected delta — `.dist-info/` added, wrapper script replaced
   by the generated entry point, `__pycache__` layout as produced by
   `installer`. Both assets (`ShareTechMono-Regular.ttf`,
   `history_en.txt`) present in the new package.
3. `namcap` on the built package: no new warnings vs the pre-change build.
4. Install the package; `/usr/bin/uglycraft` launches the game; font renders
   (Share Tech Mono, not a fallback), history text loads, hiscore
   persistence works.
5. `strings` on an installed `.pyc` shows only runtime paths (no fakeroot
   `$pkgdir` prefix).

## Done when:

- [ ] D1 — all three `build()` functions produce `dist/uglycraft-1.5-py3-none-any.whl` via `python -m build --wheel --no-isolation` after `rm -rf dist`. *(commit: )*
- [ ] D2 — all three `package_uglycraft*()` functions install solely via `python -m installer --destdir="$pkgdir" dist/*.whl`; no `_site`, `cp -r src/uglycraft`, or `compileall` remains in any PKGBUILD. *(commit: )*
- [ ] D3 — `/usr/bin/uglycraft` in the built package is the installer-generated entry-point script and launches the game (user-confirmed). *(commit: )*
- [ ] D4 — `makedepends` lists `python-build`, `python-installer`, `python-setuptools` in all three PKGBUILDs. *(commit: )*
- [ ] D5 — `.SRCINFO` and `.SRCINFO-git` match `makepkg --printsrcinfo` output for their PKGBUILDs. *(commit: )*
- [ ] D6 — verification steps 1–5 above pass; step 4 is user acceptance and requires an explicit confirmation message. *(commit: )*
- [ ] D7 — `kb/arch-packaging.md` records the new install flow and the package-data staleness note; BL-71 closed in `kb/backlog.md`; root `CHANGELOG.md` gets an `[Unreleased]` entry. *(commit: )*

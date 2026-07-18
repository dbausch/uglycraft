# Spec 0089 — Pin the external sources to fixed commits (BL-65)

The UOS units and the kitty ANSI-87 theme are fetched from **moving branch
tips** (`uos/main`, `kitty-themes/master`) in all three PKGBUILDs and in the
`poe build-original` task. Unversioned tips make builds non-reproducible and
force `SKIP` checksums. Pin every external URL to a fixed commit hash and give
the four files real sha256 sums.

→ Audit: `kb/arch-packaging.md` (P3 section). → Backlog: BL-65.
→ Enables spec 0090 (release-tarball checksum via plain `updpkgsums`).
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [x] **D1** — all three PKGBUILDs (`packaging/PKGBUILD`, `PKGBUILD-git`,
  `PKGBUILD-dev`) fetch `uos.pas`, `uos_flat.pas`, `uos_portaudio.pas` from
  `https://raw.githubusercontent.com/fredvs/uos/<COMMIT>/src/…` and
  `ANSI-87.conf` from
  `https://raw.githubusercontent.com/kovidgoyal/kitty-themes/<COMMIT>/themes/…`,
  where `<COMMIT>` are full commit hashes looked up at implementation time
  (the branch heads the current builds already use, so the built content is
  unchanged). Record both hashes as `_uos_commit=` / `_themes_commit=`
  variables so a future bump is a one-line edit per PKGBUILD. — a9f6282
- [x] **D2** — the four pinned files get real `sha256sums` entries in all
  three PKGBUILDs (only the release tarball / VCS-clone source at index 0
  keeps its spec-0090 / `SKIP` treatment respectively). — a9f6282
- [x] **D3** — `poe build-original` (`pyproject.toml`) fetches the same four
  files from the **same pinned commits**, so dev builds and packaged builds
  compile identical UOS sources (today it also fetches branch tips). — a9f6282
- [x] **D4** — `.SRCINFO` and `.SRCINFO-git` regenerated (spec 0084) in the
  same commit (source URLs + checksums are metadata). — a9f6282
- [x] **D5** — verified: `poe package-dev` passes source validation (real
  checksums verified by makepkg, no longer `Skipped`) and builds; after
  `poe clean`-style removal of `original/uos/*.pas`, `poe build-original`
  re-fetches from the pinned URLs and compiles.

## Background — confirmed facts

- Current moving-tip URLs: `PKGBUILD:11-14`-ish (`uos/main/src/*.pas`,
  `kitty-themes/master/themes/ANSI-87.conf`), mirrored in `PKGBUILD-git`,
  `PKGBUILD-dev`, and the `build-original` task in `pyproject.toml` (which
  fetches into `original/uos/` / `original/` only when absent).
- All four downloads currently carry `sha256sums=('SKIP')` **because** the
  tips move — pinning is the precondition for real checksums.
- raw.githubusercontent.com serves any commit hash in the ref position, so
  pinning is a URL-only change; no download tooling changes.
- UOS is a mature, slow-moving library — the pin freezing us on today's head
  is the *point* (reproducibility); bumps become deliberate one-line edits.
- `updpkgsums` fills checksum arrays in place (uses the first PKGBUILD in
  cwd; use `updpkgsums PKGBUILD-git` etc. per file, or fill the four sums
  manually via `sha256sum` on the downloaded files — same result).

## Out of scope

- The release tarball checksum at source index 0 of `PKGBUILD` — that is
  spec 0090, run after this spec lands.
- Bumping UOS/theme to newer upstream content — pin the currently-used heads.

## Done when:

- [x] **D1** — pinned-commit URLs (via `_uos_commit`/`_themes_commit`) in all
  three PKGBUILDs. — a9f6282; UOS pinned to `ffd165382aeae1cc1bf80673d5c02497c06f4efa`
  (`uos/main` tip), kitty-themes pinned to
  `e144651f75891cf4795ef1e7c24bb3e27c47aa06` (`kitty-themes/master` tip), both
  looked up via `git ls-remote` at implementation time.
- [x] **D2** — four real sha256 sums in each; only index 0 remains
  SKIP/spec-0090. — a9f6282; sums verified byte-identical across all three
  PKGBUILDs:
  `uos.pas=22f3e9215611d9877d21f7c835085baf9a393eac1a9e9047f195559ca1e949e4`,
  `uos_flat.pas=2ceb6afccad36f520fb57123dd7b38b59f36dedcc0bd3e099657086d7bd352b7`,
  `uos_portaudio.pas=bea6c3c79b42fdf67f8b5d3ba7895dae341a9ed72d53d0f0526a736dda3f8489`,
  `ANSI-87.conf=f3de3caf475fedeb5b0498520bb82b7d511d07d1072cd604387177f238cde9b9`.
- [x] **D3** — `poe build-original` fetches the same pinned commits. — a9f6282
- [x] **D4** — both `.SRCINFO` files regenerated in the same commit. — a9f6282;
  `makepkg --printsrcinfo` diffs show only the new pinned URLs + real
  checksums, source-array metadata otherwise unchanged.
- [x] **D5** — makepkg validates the checksums (dev build) and
  `poe build-original` still builds after a clean re-fetch. — verified this
  session: `poe package-dev` (after clearing stale cached downloads in
  `packaging/`, which were left over from before the pin and predictably
  failed the new checksum) showed `uos.pas … Passed`, `uos_flat.pas … Passed`,
  `uos_portaudio.pas … Passed`, `ANSI-87.conf … Passed` in the
  "Validating source files with sha256sums" step, and the build completed
  (FPC compiled `UGLI_2`, both sub-packages created). `PKGBUILD-dev`'s
  auto-bumped `pkgver` line was reverted per the known side effect. Separately,
  removed the gitignored `original/uos/*.pas` and `original/ANSI-87.conf`
  fetched copies and reran `poe build-original`: it re-downloaded from the
  pinned URLs and FPC compiled `UGLI_2` with exit 0; the re-fetched files'
  sha256 sums matched the four sums above exactly.

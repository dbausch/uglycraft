# Release process — order of operations and pitfalls

Operational record of how a release actually goes, distilled from the v1.6
release (2026-07-19, the first release with checksummed sources and AUR
deployment). The poe task inventory is in `CLAUDE.md`; AUR specifics are in
→ `kb/arch-packaging.md`. This article is the cross-cutting sequence and the
traps that are not obvious from the tasks themselves.

## The working order (v1.6 as template)

1. **Docs first**: verify README/CHANGELOG are current, then close
   `[Unreleased]` in `CHANGELOG.md` (game version, e.g. 1.6) **and**
   `original/CHANGELOG.md` (port version, e.g. 2.7 — its own numbering).
2. **Port version constant** — see pitfall below: bump `Version = '…'` in
   `original/UGLI_2.pp` *and* the test program's own copy in
   `UGLI_2_Test.pp` to match the new port version. Rebuild + rerun
   `poe test-original`.
3. **Version metadata**: `pyproject.toml` `[project] version` and
   CLAUDE.md's *Current version* marker.
4. **Tag** (lightweight, `vX.Y`) and **push the tag to GitHub** — the next
   step needs the tag live.
5. **Release PKGBUILD bump**: `pkgver=X.Y`, then `updpkgsums` (only source
   index 0 changes; the four pinned external sums are re-verified in
   place), regenerate `.SRCINFO`, `makepkg --verifysource`, `namcap`.
   This *must* come after the GitHub tag push — the tarball checksum is of
   the published tag (spec 0090). Consequence: the PKGBUILD bump commit is
   always *after* the tag, unlike in the pre-checksum era (v1.5's tag
   pointed at its PKGBUILD bump; that ordering is no longer possible).
6. **Builds**: `poe build-linux`, `poe build-windows`, `poe build-original`
   — build and deploy are separate; deploy tasks never build.
7. **Verify the artifacts before deploying** (see pitfalls): sizes vs the
   documented expectations, a `--help` run of the Linux binary, and for the
   Windows exe an archive listing.
8. **Deploy**: `poe deploy` (itch linux-64 + windows-64 + original-linux +
   AUR release), then `poe deploy-aur-git`. Verify with
   `butler status dbausch/uglycraft` (all channels show the new versions)
   and the AUR web page.

## Pitfalls (each one bit during v1.6)

### Windows exe builds "successfully" while bundling nothing

The Wine Python must have an **editable install of `uglycraft`** (the
Windows leg of the spec 0082 src-layout trap): without it,
PyInstaller-in-Wine cannot resolve `run_game.py`'s import, silently bundles
neither the game package nor pygame/numpy (they are only imported *by* the
game), and still exits 0. The analysis warnings go to the gitignored
`build/uglycraft/warn-uglycraft.txt`, not stdout. `poe setup-windows` now
performs the editable install; a fresh Wine setup is covered.

**The tell**: exe size. A correct `uglycraft.exe` is ~25 MB; the broken one
was 7 MB. **The proof**: list the onefile archive with
`.venv/bin/pyi-archive_viewer --list dist/windows-64/uglycraft.exe` — it
must contain `pygame\…`, `numpy\…`, `uglycraft\fonts\…`,
`uglycraft\translations\…` (note *backslashes* in the listing — grep
patterns with `/` match nothing). This works cross-platform from the Linux
venv's PyInstaller.

### The port's `Version` constant is not derived from anything

`original/UGLI_2.pp` has a hand-maintained `Version = '2.x'` constant
(shown in the intro/log), and `deploy-original-linux` greps it for the itch
`--userversion`. `UGLI_2_Test.pp` carries its **own copy** of the constant
(the test program cannot include the game's program header). Closing
`original/CHANGELOG.md` into a new port version without bumping both
constants ships a binary that reports the old version — at v1.6 time the
game said 2.6 (changelog: 2.7) and the test copy was stuck at 2.3.

Residual quirk: the AUR `ugli` package builds from the *game* release tag,
so its baked-in `GitVersion` is the game version (`1.6`) while `Version` is
the port version — the in-game log shows `2.7/1.6`. Intentional.

### Deploy-time gotchas

- `poe deploy` aborts at the first failing subtask, but piping it through
  `tail` (or anything) masks the nonzero exit — check the real exit code
  and read the full log, not a tail.
- `deploy-aur*` only `git push`es when it just created a commit; after a
  commit-succeeded-push-failed run, a rerun silently skips the push
  (BL-78, open).
- First-time AUR pushes: account email must be verified; the AUR accepts
  only branch `master` (fresh clones default to the user's
  `init.defaultBranch` and must be renamed) — details in
  → `kb/arch-packaging.md` § First push.

### After deploying

`butler status dbausch/uglycraft` is the ground truth that all channels
processed the new builds. The `original-dos` channel must remain untouched
(frozen forever, see CLAUDE.md).

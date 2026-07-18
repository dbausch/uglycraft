# Spec 0090 — Real sha256 for the release tarball (BL-63)

The release PKGBUILD's source array is still all-`SKIP`, including the
versioned `v$pkgver.tar.gz` GitHub tarball — an Arch guideline violation
(integrity variables must hold correct values) and a gap in our own release
procedure (CLAUDE.md § *Arch packaging* already mandates `updpkgsums` at
release time; it was never run for v1.5). Fill in the real checksum.

**Depends on spec 0089**: once the four external sources are pinned and
checksummed there, this spec is a plain `updpkgsums` run that fixes the one
remaining entry (index 0). Implement after 0089.

→ Audit: `kb/arch-packaging.md` (P2 section). → Backlog: BL-63.
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [x] **D1** — `updpkgsums packaging/PKGBUILD` run; source index 0
  (`uglycraft-1.5.tar.gz :: …/archive/v1.5.tar.gz`) carries a real sha256.
  (With spec 0089 landed this cannot disturb the other four entries — they
  already hold real sums that updpkgsums re-verifies.) — 3712eee;
  `6fd94d423b5daed0966c63baaab297b103cb326c657712d883d140f8d27bd200`; `git
  diff` confirmed only the index-0 line changed, the other four sums are
  byte-identical to before.
- [x] **D2** — `PKGBUILD-git` and `PKGBUILD-dev` keep `SKIP` for their VCS
  clone source **only** (a git clone has no meaningful tarball checksum; this
  is the sanctioned use of SKIP). — verified this session: both files were
  already in this state pre-0090 (their four external sums real from spec
  0089) and were not touched.
- [x] **D3** — `packaging/.SRCINFO` regenerated (spec 0084) in the same
  commit. — 3712eee; `makepkg --printsrcinfo` diff shows only the index-0
  `sha256sums` line changing from `SKIP` to the real sum.
  `.SRCINFO-git` was also regenerated to confirm: byte-for-byte identical, no
  diff.
- [x] **D4** — verified: `makepkg --verifysource -p PKGBUILD` (or a full
  `makepkg -f` when a GitHub-reachable state permits) downloads the v1.5
  tarball and passes validation. Since the v1.5 tag is already published on
  GitHub, `--verifysource` works today regardless of the unpushed commits. —
  verified this session: `makepkg --verifysource -f -p PKGBUILD` (the `-f`
  needed only because a prior `uglycraft-1.5-1-x86_64.pkg.tar.zst` already
  existed in `packaging/`, not because anything was rebuilt) printed
  `uglycraft-1.5.tar.gz … Passed`, `uos.pas … Passed`, `uos_flat.pas …
  Passed`, `uos_portaudio.pas … Passed`, `ANSI-87.conf … Passed` — all five
  sources validated.
- [x] **D5** — release procedure note: CLAUDE.md § *Arch packaging* already
  says "run `updpkgsums`" at release time — confirm the wording still matches
  the post-0089 reality (only index 0 changes per release; the pinned
  externals' sums change only on a deliberate pin bump) and adjust if needed.
  — 3712eee; the old wording ("run `updpkgsums` to fill in real sha256
  checksums") read as if multiple entries get filled in each release, which
  no longer matches reality post-0089. Reworded to name index 0 as the only
  `SKIP` entry and note the four externals are re-verified, not rewritten,
  changing only on a deliberate `_uos_commit`/`_themes_commit` bump.

## Background — confirmed facts

- `PKGBUILD` `sha256sums` is five × `SKIP` today; the release tarball URL is
  `$url/archive/v$pkgver.tar.gz` with `_tag=v$pkgver`, `pkgver=1.5`.
- The `v1.5` tag and its tarball are live on GitHub (the v1.5 release was
  deployed from it), so the checksum can be computed right now — no push of
  the current working state is needed for this spec.
- GitHub's `/archive/` tarballs for a **tag** are generated deterministically
  enough in practice for AUR use (same tag → same bytes has held for years;
  the residual risk of GitHub changing its tar/gzip stack is the accepted
  Arch-wide norm — every GitHub-sourced AUR package shares it).
- `updpkgsums` (pacman-contrib) downloads all sources into `$SRCDEST`
  (`packaging/`, gitignored) and rewrites the array in place.

## Done when:

- [x] **D1** — index-0 sha256 real in `PKGBUILD`. — 3712eee
- [x] **D2** — VCS sources in `-git`/`-dev` remain SKIP, nothing else does.
  — already true pre-0090; confirmed unchanged this session.
- [x] **D3** — `.SRCINFO` regenerated in the same commit. — 3712eee
- [x] **D4** — `makepkg --verifysource` passes against the live v1.5
  tarball. — verified this session; all five sources `Passed`.
- [x] **D5** — CLAUDE.md release-time wording checked/adjusted. — 3712eee

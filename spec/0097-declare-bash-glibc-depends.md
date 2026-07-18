# Spec 0097 — declare `bash` + `glibc` depends for the ugli split packages

The last two namcap implicit-dependency notes on the built `ugli` packages:

```
ugli-dev W: Dependency bash detected and implicitly satisfied but optional
  (programs ['bash'] needed in scripts ['usr/bin/ugli'])
ugli-dev W: Dependency glibc detected and implicitly satisfied but optional
  (libraries ['usr/lib/libc.so.6'] needed in files ['usr/lib/ugli/UGLI_2'])
```

Both needs are real: the wrapper `packaging/ugli.sh` is a genuine bash
script (it uses arrays — `args=()` / `args+=(…)` / `"${args[@]}"` — to
filter `-f`/`--fs` out of the pass-through arguments; everything else in it
is POSIX), and the `UGLI_2` ELF binary dynamically links `libc.so.6`.
Declare both explicitly. After this, the only namcap output on the built
packages is the accepted `lacks PIE` warning (spec 0095).

→ Audit: `kb/arch-packaging.md`. → Wrapper analysis: this session,
2026-07-19. → `.SRCINFO` regeneration mechanism: spec 0084.
→ Split-makedeps rule interaction precedent: spec 0093 (D6).

## Status checklist

- [ ] **D1** — `depends=('hicolor-icon-theme')` becomes
  `depends=('bash' 'glibc' 'hicolor-icon-theme')` in `package_ugli()`
  (`packaging/PKGBUILD:79`), `package_ugli-git()` (`PKGBUILD-git:84`), and
  `package_ugli-dev()` (`PKGBUILD-dev:91`).
- [ ] **D2** — the `uglycraft*` split packages are untouched: their wrapper
  needs are covered transitively via `python` (namcap is already silent on
  the built `uglycraft-dev` package).
- [ ] **D3** — split-makedeps interaction checked (the spec 0093 D6 lesson:
  a subpackage `depends` entry must be reachable from the pkgbase
  `makedepends` closure or namcap's `SplitPkgMakedepsRule` fires). Run
  `namcap` on all PKGBUILDs after the D1 edit; **if** it demands `bash`/
  `glibc` in `makedepends`, add exactly the demanded names to the
  pkgbase-level `makedepends` of all three PKGBUILDs (same pattern as
  commit 8f3c117); if it stays silent (both are plausibly covered through
  the existing makedepends' own dependency trees), no makedepends change —
  record which way it went here.
- [ ] **D4** — `.SRCINFO`/`.SRCINFO-git` regenerated in the same commit,
  showing the new `depends = bash` / `depends = glibc` lines under the
  `ugli`/`ugli-git` sections.
- [ ] **D5** — verified: `namcap` on both PKGBUILDs stays clean (no new
  finding); `poe package-dev` builds; `namcap` on the fresh `ugli-dev`
  package shows **only** the accepted `lacks PIE` line (both
  implicit-dependency notes gone); the fresh `uglycraft-dev` package stays
  namcap-silent.

## Background — confirmed facts

- Current `depends` of all three `package_ugli*()`:
  `('hicolor-icon-theme')` only (`PKGBUILD:79`, `PKGBUILD-git:84`,
  `PKGBUILD-dev:91`).
- The bash requirement is genuine, not shebang pedantry: rewriting the
  wrapper to POSIX sh was considered and rejected — on Arch `/bin/sh` is
  owned by the `bash` package anyway, so the dependency (and namcap's note)
  would persist; the rewrite would buy portability to non-Arch systems that
  are not a target for this wrapper.
- `glibc` as an explicit depends for ELF-shipping packages matches common
  current Arch practice; namcap's note is the same class.
- Both packages are effectively unremovable on any working Arch system, so
  this is a guideline/metadata fix with zero installation-footprint impact.
- namcap on the built `uglycraft-dev` package is currently completely
  silent — its interpreter/library needs resolve through its `python`
  dependency chain, so extending its `depends` too would be redundant.

## Done when:

- [ ] **D1** — three `depends` arrays extended with `bash` and `glibc`.
- [ ] **D2** — `uglycraft*` packages untouched.
- [ ] **D3** — split-makedeps interaction checked; outcome recorded (and
  pkgbase `makedepends` extended only if namcap demanded it).
- [ ] **D4** — both `.SRCINFO` files regenerated in the same commit.
- [ ] **D5** — namcap: PKGBUILDs clean; fresh `ugli-dev` package shows only
  the accepted PIE line; fresh `uglycraft-dev` stays silent.

# Spec 0095 — FULL RELRO for the FPC binaries; PIE declared out of reach (BL-74)

namcap warns on the built `ugli`/`ugli-git`/`ugli-dev` packages that the
`UGLI_2` ELF binary "lacks FULL RELRO" and "lacks PIE". This spec fixes the
RELRO half by passing the standard hardening options to the linker through
FPC, uniformly across every `fpc` invocation in the project, and documents —
with reproducible evidence — why the PIE half is not achievable with the
stock Arch FPC toolchain and is accepted as a known leftover.

→ Audit: `kb/arch-packaging.md` (namcap follow-ups). → Backlog: BL-74.
→ `.SRCINFO` regeneration mechanism: spec 0084 (no metadata change expected —
the flags live in `build()` function bodies; regenerate-and-diff to confirm).

## Status checklist

- [x] **D1** — `-k-z -krelro -k-z -know` added to the `fpc -Fuuos UGLI_2.pp`
  invocation in `build()` of all three PKGBUILDs (`packaging/PKGBUILD:46`,
  `PKGBUILD-git:50`, `PKGBUILD-dev:57`). (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D2** — the same flags added to the four `fpc` invocations in
  `pyproject.toml` (`build-original`:146, `test-original`:153,
  `build-replay`-style task:158, bench task:163), so dev, test, and packaged
  builds all link identically. (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D3** — verified on the built binary: `readelf -lW` shows a
  `GNU_RELRO` segment **and** `readelf -dW` shows `BIND_NOW` / `FLAGS_1: NOW`
  (= FULL RELRO); `poe test-original` still passes (exit 0, all tests) with
  the hardened link; the packaged binary still prints its `--help` from an
  extracted `ugli-dev` package. (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D4** — namcap on the built `ugli-dev` package no longer emits the
  `lacks FULL RELRO` warning; the `lacks PIE` warning **remains and is
  accepted** (see Background — not fixable with the system FPC).
  (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D5** — `.SRCINFO`/`.SRCINFO-git` regenerated and diffed: no change
  (function-body-only edit). (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D6** — launch check: the game starts and plays normally with the
  hardened binary (user acceptance) — user installed the hardened
  `ugli-dev-1.5.r738.g0a88210` package and confirmed the game runs fine
  (2026-07-19).

## Background — confirmed facts

### What the two warnings mean

- **RELRO** (RELocation Read-Only): the dynamic linker maps the relocation
  tables (GOT etc.) read-only after startup so a write primitive cannot
  overwrite function pointers there. "Partial" RELRO protects only part of
  the tables; "FULL" additionally requires `BIND_NOW` (all symbols resolved
  eagerly at startup, then the whole GOT sealed).
- **PIE** (Position-Independent Executable): the program is linked as
  `ET_DYN` so ASLR can randomize its load address.

### Current state of the shipped binary

Verified on the built `ugli-dev` package's `UGLI_2` (2026-07-18):
`ET_EXEC` (no PIE), `GNU_RELRO` segment present, **no** `BIND_NOW` dynamic
flag — i.e. partial RELRO. Exactly namcap's two warnings.

### FULL RELRO: one flag pair, verified

FPC's `-k<option>` passes options through to the external linker. Passing
`-k-z -krelro -k-z -know` (→ `ld -z relro -z now`) was verified this session
(FPC 3.2.2, Arch) on a dynamically-linked test program: the result carries
`GNU_RELRO` + `FLAGS: BIND_NOW` + `FLAGS_1: NOW` and runs normally. The
explicit `-z relro` is belt-and-braces (Arch's ld already defaults to
partial RELRO; the default is not guaranteed by FPC). Cost: eager symbol
binding at process start — negligible for a game that links only libc
dynamically.

### PIE: blocked by the stock FPC RTL — accepted as won't-fix

Attempting a PIE link (`fpc -Cg -k-pie`) against a libc-linked program fails
hard on Arch's FPC 3.2.2:

```
/usr/bin/ld: /usr/lib/fpc/3.2.2/units/x86_64-linux/rtl/si_c.o:
  relocation R_X86_64_PC32 against symbol `__libc_start_main@@GLIBC_2.34'
  can not be used when making a PIE object; recompile with -fPIE
```

The precompiled RTL startup object shipped by the distro is not
PIC-compiled. `UGLI_2` dynamically links libc (the PortAudio/UOS path), so
this startup object is exactly what its link uses. Producing a PIE would
require rebuilding the FPC RTL with PIC codegen (or a patched/newer FPC) —
grossly out of proportion for a P3 polish item, and non-PIE is the norm for
FPC-built packages on Arch for this exact reason. (A `-k-pie` link *without*
libc "succeeds" but yields a binary that does not execute — broken either
way.) The namcap `lacks PIE` warning is therefore accepted and documented,
not fixed.

### Where the flags go — every fpc invocation

Uniformity across all seven sites keeps dev/test/packaged links identical
(same principle as the spec 0089 source pinning) and means the test suite
exercises a full-RELRO link on every run:

- `packaging/PKGBUILD:46`, `PKGBUILD-git:50`, `PKGBUILD-dev:57` —
  `fpc -Fuuos UGLI_2.pp` in `build()`.
- `pyproject.toml:146` (`build-original`), `:153` (`test-original`), `:158`
  (replay tool), `:163` (bench tool).

## The concrete change

In each of the seven invocations, insert the flags after `-Fuuos`:

```
fpc -Fuuos -k-z -krelro -k-z -know …
```

Nothing else changes — no source edits, no new tasks.

## Verification

- **D3**: after `poe build-original`, `readelf -lW original/UGLI_2 | grep
  GNU_RELRO` (present) and `readelf -dW original/UGLI_2 | grep -E
  'BIND_NOW|FLAGS_1'` (both present). `poe test-original` exits 0 with all
  tests passing. After `poe package-dev`, extract `usr/lib/ugli/UGLI_2` from
  the `ugli-dev` package, repeat the two readelf checks, and run it with
  `--help` from an unrelated CWD (it must print the help text).
- **D4**: `namcap` on the built `ugli-dev` package: the FULL-RELRO warning is
  gone; the PIE warning remains (expected, accepted).
- **D5**: `cd packaging && makepkg --printsrcinfo | diff - .SRCINFO` (and the
  `-p PKGBUILD-git` equivalent) — empty diffs.
- **D6**: user launches the game (`ugli` wrapper or `poe run-original`-style
  invocation) and confirms it plays normally — eager binding changes process
  startup, so a real launch is the final gate.

## Out of scope

- PIE (see Background — accepted won't-fix until FPC ships a PIC RTL).
- Any other hardening (stack protector, FORTIFY) — FPC does not consume C
  compiler hardening flags; nothing further namcap asks for.
- BL-77 (Maintainer tag / pkgdesc wording) — separate item.

## Done when:

- [x] **D1** — flags present in all three PKGBUILDs' `build()`.
  (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D2** — flags present in the four `pyproject.toml` fpc invocations.
  (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D3** — readelf shows FULL RELRO on both the dev-built and packaged
  binary; tests pass (159/159); extracted packaged binary prints `--help`.
  (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D4** — namcap: FULL-RELRO warning gone, PIE warning documented as
  accepted. (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D5** — `.SRCINFO` regeneration shows no diff.
  (`0a882109b52a1f3792aac3fbf15814c3b1b6f270`)
- [x] **D6** — launch check confirmed by the user: hardened
  `ugli-dev-1.5.r738.g0a88210` package installed and tested, game runs fine
  (2026-07-19).

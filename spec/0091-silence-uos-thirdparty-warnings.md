# Spec 0091 — Scoped suppression of FPC warnings/notes from fetched UOS sources (BL-75)

`poe build-original`, and the `build()` step of all three PKGBUILDs
(`packaging/PKGBUILD`, `PKGBUILD-git`, `PKGBUILD-dev`), compile the fetched
third-party UOS units (`uos.pas`, `uos_flat.pas`, `uos_portaudio.pas`) as
part of building `UGLI_2.pp`. Against those units FPC 3.2.2 emits **5
warnings + 18 notes on every build**. They are third-party code we do not
own, and they drown out any warning/note FPC might emit for the project's own
Pascal sources in the same log. This spec silences the third-party clutter
**strictly within the UOS units**, so project code (`UGLI_2.pp`,
`UOSSound.pp`, includes, tests) keeps full, unfiltered warnings.

→ Backlog: BL-75.  → External-source pinning: spec 0089
(`_uos_commit=ffd165382aeae1cc1bf80673d5c02497c06f4efa`).
→ Existing in-source precedent for exactly this technique: spec/
`original/UGLI_2_Core.inc:1` (`{$WARN 6058 OFF}`).

## Status checklist

- [ ] **D1** — A fixed FPC message-directive block
  (`{$WARN 4105 OFF} {$WARN 5025 OFF} {$WARN 5027 OFF} {$WARN 5089 OFF}
  {$WARN 5093 OFF} {$WARN 6058 OFF}` + a `UGLYCRAFT-WARN-SUPPRESS` sentinel
  comment) is prepended to each of the three fetched UOS units after they are
  fetched/copied, in `pyproject.toml`'s `build-original` task.
- [ ] **D2** — The same prepend step is added to the `prepare()` (or start of
  `build()`) of all three PKGBUILDs, right after the `cp …/uos*.pas
  original/uos/` step.
- [ ] **D3** — The prepend is idempotent: guarded by the sentinel so a repeat
  build over an already-patched working tree (the poe task fetches only when
  the file is absent) does not stack duplicate directive blocks.
- [ ] **D4** — Clean build demonstrated: `poe build-original` shows **0**
  UOS-originated warnings/notes (was 5 + 18). `poe test-original` and
  `poe package-dev` likewise show no UOS clutter.
- [ ] **D5** — Scoping proven: a deliberately introduced warning in
  project-own code (e.g. an unused local in `UGLI_2.pp`) still appears in the
  build log while the UOS suppression is active.

## Background — confirmed facts

### The messages and their FPC numbers

Compiling the already-fetched tree with message numbers shown
(`fpc -Fuuos -vq uos/uos.pas`, FPC 3.2.2) yields **5 warnings + 18 notes**,
falling into exactly six distinct message numbers — all in `uos.pas` only
(`uos_flat.pas`/`uos_portaudio.pas` emit none today):

| Num  | Kind    | Text |
|------|---------|------|
| 4105 | Warning | Implicit string type conversion with potential data loss from "UnicodeString" to "UTF8String" |
| 5089 | Warning | Local variable "…" of a managed type does not seem to be initialized |
| 5093 | Warning | function result variable of a managed type does not seem to be initialized |
| 5025 | Note    | Local variable "…" not used |
| 5027 | Note    | Local variable "…" is assigned but never used |
| 6058 | Note    | Call to subroutine "…" marked as inline is not inlined |

Line references (representative): `uos.pas` 2239 (5093), 10640 (5089),
11754/12148/12149 (4105), 4505/7811-7814/8530-8532/10256 (5025), 10594
(5027), 6174/6176/6257/6259 (6058).

### The existing in-source precedent (the mechanism we reuse)

The project already silences one of these exact categories for its **own**
RTL calls: `original/UGLI_2_Core.inc:1` begins with
`{$WARN 6058 OFF} { "marked as inline is not inlined" — FPC's BaseUnix calls }`.
That is a per-source-location FPC message directive. This spec reuses the
identical mechanism (`{$WARN <num> OFF}`), applied to the fetched UOS units
instead of a project include.

### Why the directive must live *inside* the UOS units, not in our wrapper

FPC message directives (`{$WARN n OFF}`) are **local switches scoped to the
compilation of the unit they appear in**. They do **not** cross the `uses`
boundary in either direction. Verified two ways this session:

1. Minimal test — a used unit `usedu.pas` with `{$WARN 5025 OFF}` on line 1
   and an unused local, used by `mainp.pas` which also has an unused local.
   `fpc mainp.pas` suppressed the note in `usedu` but still reported
   `mainp.pas(3,5) Note: Local variable "unusedInMain" not used`. So a
   directive in the **used** unit stays contained to that unit, and does
   **not** leak forward into the **using** unit compiled afterwards.
2. The status quo is the mirror image: the `{$WARN 6058 OFF}` in
   `UGLI_2_Core.inc` (compiled as part of `UGLI_2.pp`) does **not** suppress
   the 6058 notes emitted while compiling `uos.pas` — proving a directive in
   the **using** unit cannot reach the **used** unit either.

Consequence: suppression **must** be inserted into the UOS unit sources
themselves. A `{$push}{$warnings off}` block wrapped around our own `uses`
clause (candidate (b) in the backlog hint) is therefore ineffective for
messages emitted while compiling the used units — rejected.

Placement note: the directive works when prepended on line 1, **before** the
`unit` keyword (confirmed in the minimal test, and matching how
`UGLI_2_Core.inc` puts it on its first line).

### Why not the global command-line flags

`-vm<numbers>` (mask messages) and `-vw-`/`-v0` apply **globally to the whole
compilation invocation**. Because `fpc -Fuuos UGLI_2.pp` compiles the UOS
units and the project's own units in **one** invocation, any global flag
would silence the same categories in `UGLI_2.pp`/`UOSSound.pp` too —
violating the strict-scoping requirement. Rejected. (A separate invocation
that pre-compiles only `uos*.pas` with relaxed `-v` into `.ppu`/`.o` for the
main build to link — candidate (c) — would scope correctly but adds a second
compile step and `.ppu` staleness/recompile fragility to the poe task and all
three PKGBUILDs; the in-source directive is simpler and needs no ordering
guarantees.)

### End-to-end verification already run this session

With the directive block prepended to all three fetched UOS units and a full
`fpc -Fuuos UGLI_2.pp`:

- Build log dropped from **5 warnings + 18 notes** to a **single** remaining
  note, `UOSSound.pp(57,3) Note: (6058) … FpWrite … marked as inline is not
  inlined` — which is **project-own** code, not UOS (see *Out of scope*).
  All 23 UOS messages were gone; the `UGLI_2` binary built normally.
- With an additional deliberately-inserted unused local in `UGLI_2.pp`, the
  log showed `UGLI_2.pp(70,4) Note: Local variable "…" not used` **plus** the
  UOSSound note — i.e. project-code diagnostics survive untouched while UOS is
  silenced. (Both temporary edits were reverted; `original/` left clean.)

### Where the change must be applied — independent compiles

The suppression must be added in **every** place that compiles the UOS chain,
because they compile independently:

- `pyproject.toml` → `build-original`: fetches into `original/uos/` (only when
  a file is absent: `[ -f original/uos/$f ] || curl …`), then
  `cd original && fpc -Fuuos UGLI_2.pp`. Add the prepend step after the fetch
  `for` loop, before the `fpc` line.
- `packaging/PKGBUILD`, `PKGBUILD-git`, `PKGBUILD-dev`: each `prepare()` does
  `cp "$srcdir"/{uos.pas,uos_flat.pas,uos_portaudio.pas} original/uos/`; each
  `build()` runs `fpc -Fuuos UGLI_2.pp`. Add the prepend step in `prepare()`
  immediately after that `cp` (or at the top of `build()`), in all three.

`test-original` (`fpc -Fuuos -oUGLI_2_Test UGLI_2_Test.pp`) and the
`package-dev` build both compile the same UOS chain (`UGLI_2_Test.pp` uses
`UOSSound`, which uses `uos_flat`, which uses `uos`). `test-original` has **no
fetch/copy step of its own** — it reuses the `original/uos/` files that
`build-original` fetched. Since `build-original` now prepends the directives
into those persistent working-tree files, `test-original` inherits the
patched sources automatically; **no change to the `test-original` task is
needed**. `package-dev` is covered by the PKGBUILD-dev change (D2).

## The concrete change

Reproducible because the UOS sources are pinned (spec 0089). The directive
block (single line, order-independent):

```
{$WARN 4105 OFF} {$WARN 5025 OFF} {$WARN 5027 OFF} {$WARN 5089 OFF} {$WARN 5093 OFF} {$WARN 6058 OFF} { UGLYCRAFT-WARN-SUPPRESS BL-75: fetched third-party UOS unit — see spec 0091 }
```

Idempotent prepend applied to each fetched unit, e.g.:

```sh
for f in uos.pas uos_flat.pas uos_portaudio.pas; do
  grep -q 'UGLYCRAFT-WARN-SUPPRESS' "original/uos/$f" \
    || sed -i "1i $BLOCK" "original/uos/$f"
done
```

- **poe `build-original`**: insert this loop between the existing fetch `for`
  loop and the `cd original && fpc …` line (path prefix `original/uos/…` as
  above).
- **All three PKGBUILDs**: insert the same loop in `prepare()` right after the
  `cp …/uos*.pas original/uos/` line (path prefix `original/uos/…` relative to
  the already-`cd`-ed package dir).

Apply the block to **all three** units (not just `uos.pas`) for uniformity and
to future-proof `uos_flat`/`uos_portaudio` against a later pin bump; applying
`{$WARN … OFF}` to a unit that currently emits nothing is harmless. If a
future pin bump introduces a *new* message number, that new message still
surfaces (graceful degradation to today's behavior), signalling the block may
need an added number — it never breaks the build.

The six numbers are deliberately enumerated rather than using a blanket
`{$WARNINGS OFF}{$NOTES OFF}`: enumerating keeps *unexpected* new UOS
diagnostics visible after a pin bump, and documents precisely what is being
tolerated.

## Verification

- **D4 build-original**: run `poe build-original`; confirm the log contains no
  `uos.pas(`/`uos_flat.pas(`/`uos_portaudio.pas(` warning or note lines and no
  `N warning(s)/note(s) issued` count attributable to UOS. (A single
  `UOSSound.pp(57,…)` 6058 note remains — project code, out of scope below.)
- **D4 test-original**: run `poe test-original`; confirm the same absence of
  UOS lines and that the suite still exits 0.
- **D4 package-dev**: run `poe package-dev`; confirm the `build()` log shows no
  UOS warnings/notes.
- **D3 idempotency**: run `poe build-original` twice; confirm each patched
  `original/uos/*.pas` contains exactly **one** `UGLYCRAFT-WARN-SUPPRESS` line.
- **D5 scoping**: temporarily add an unused local variable to `UGLI_2.pp`,
  rebuild, and confirm the corresponding `UGLI_2.pp(…) Note: Local variable …
  not used` **still** appears despite UOS suppression; then revert. (Already
  demonstrated once this session — see Background.)

## Out of scope

- **The `UOSSound.pp(57,3)` 6058 note** (`FpWrite … marked as inline is not
  inlined`). This is **project-own** code, not a UOS unit, so BL-75's
  strict-scoping rule ("do not blanket-silence the project's own Pascal code")
  and this spec deliberately leave it untouched. It is the same *category*
  already silenced for `UGLI_2.pp` via `UGLI_2_Core.inc`'s `{$WARN 6058 OFF}`;
  extending that targeted directive to `UOSSound.pp` is a separate project-code
  decision and should be handled as its own change/backlog item, not folded in
  here.
- **BL-74** (FULL RELRO / PIE hardening of the `UGLI_2` binary) — unrelated
  FPC linker-flag work.
- Changing the UOS pin or upstreaming fixes to `fredvs/uos`.

## Done when:

- [ ] **D1** — `pyproject.toml` `build-original` prepends the six-number
  directive block (with sentinel) to all three fetched UOS units after fetch,
  before the `fpc` line.
- [ ] **D2** — All three PKGBUILDs (`PKGBUILD`, `PKGBUILD-git`,
  `PKGBUILD-dev`) prepend the same block in `prepare()` after the
  `cp …/uos*.pas` step.
- [ ] **D3** — The prepend is sentinel-guarded and idempotent (no duplicate
  blocks across repeated builds).
- [ ] **D4** — `poe build-original`, `poe test-original`, and
  `poe package-dev` all produce a build log free of UOS-originated
  warnings/notes (down from 5 warnings + 18 notes); `test-original` still
  exits 0.
- [ ] **D5** — A deliberately introduced warning in project-own code still
  appears in the build log while UOS suppression is active (scoping proven).

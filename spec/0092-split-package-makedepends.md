# Spec 0092 — makedepends for the uglycraft split packages (BL-72)

namcap's split-package makedeps rule flags `packaging/PKGBUILD-git`:
`E: Split PKGBUILD needs additional makedepends ['python', 'python-numpy',
'python-pygame'] to work properly` for the `uglycraft-git` split package. This
spec investigates why the structurally-identical release `PKGBUILD` does
**not** get the same warning in the same namcap run, and specifies the fix —
which must land in all three PKGBUILDs (release, `-git`, `-dev`) for
consistency, once the investigation shows the release PKGBUILD's silence is
not evidence of correctness.

→ Audit: `kb/arch-packaging.md` ("Operational notes for the first push",
BL-72–BL-74). → Backlog: BL-72.
→ `.SRCINFO` regeneration mechanism: spec 0084.

## Status checklist

- [ ] **D1** — `makedepends` at **pkgbase level** in `packaging/PKGBUILD` gains
  `python`, `python-numpy`, `python-pygame` (alongside the existing `fpc`).
- [ ] **D2** — same three packages added to pkgbase-level `makedepends` in
  `packaging/PKGBUILD-git` (alongside `fpc`, `git`).
- [ ] **D3** — same three packages added to pkgbase-level `makedepends` in
  `packaging/PKGBUILD-dev` (alongside `fpc`, `git`), for consistency — this
  file is never deployed but should not drift from the other two.
- [ ] **D4** — `.SRCINFO` and `.SRCINFO-git` regenerated (spec 0084 mechanism)
  to reflect the new `makedepends` lines.
- [ ] **D5** — verified: `namcap packaging/PKGBUILD` and `namcap
  packaging/PKGBUILD-git` both run clean of the `missing-makedeps` /
  "Split PKGBUILD needs additional makedepends" finding after the edit; `poe
  package-dev` still builds both `uglycraft-dev` and `ugli-dev` successfully
  with the extra makedepends present.

## Background — confirmed facts

### The namcap finding

Running `namcap packaging/PKGBUILD-git` (namcap 3.6.0-3, system-installed)
produces:

```
PKGBUILD (uglycraft-git) E: Split PKGBUILD needs additional makedepends ['python', 'python-numpy', 'python-pygame'] to work properly
```

Running `namcap packaging/PKGBUILD` in the same environment produces **no**
such line — only an unrelated `Missing Maintainer tag` warning. `PKGBUILD:44`
and `PKGBUILD-git:48` declare the identical
`depends=('python' 'python-pygame' 'python-numpy')` inside
`package_uglycraft()`/`package_uglycraft-git()` respectively, and neither
top-level `PKGBUILD` (`makedepends=('fpc')`, `PKGBUILD:8`) nor `PKGBUILD-git`
(`makedepends=('fpc' 'git')`, `PKGBUILD-git:8`) declares `python`/
`python-pygame`/`python-numpy` at pkgbase level. Structurally the two files
are the same shape.

### Why the release PKGBUILD doesn't flag: it's local-machine state, not correctness

The rule is `Namcap.rules.splitpkgbuild.SplitPkgMakedepsRule`
(`/usr/lib/python3.*/site-packages/Namcap/rules/splitpkgbuild.py:29-62`,
rule name `splitpkgmakedeps`). It builds `global_deps` from the pkgbase's
own `names` + `depends` + `makedepends`, then expands it with
`Namcap.depends.getcovered(global_deps)` — the **transitive dependency
closure of each name, looked up in the local pacman database**
(`Namcap/depends.py:15-27`: `single_covered()` calls
`package.load_from_db(i)` for every name in the set, including the pkgbase's
own package **names**, not just its `makedepends`). It then checks that each
subpackage's own `depends`/`makedepends` (`local_deps`) is a subset of
`global_deps`.

`package.load_from_db()` (`Namcap/package.py:257-269`) queries
`pyalpm_handle.get_localdb()` — the **installed-package** database on the
machine running namcap — and falls back to `lookup_provider()` (i.e. resolves
virtual/`provides` names) if no exact match exists.

On the machine this audit ran on, `uglycraft-dev`/`ugli-dev` are installed
(built and installed during the spec 0086/0087 verification passes) and
`package_uglycraft-dev()` declares `provides=('uglycraft')`
(`PKGBUILD-dev:56`). Querying namcap's own dependency loader directly
confirms the mechanism:

```
>>> Namcap.package.load_from_db('uglycraft')
PacmanPackage({'name': 'uglycraft-dev', ...,
                'depends': ['python', 'python-pygame', 'python-numpy'], ...})
>>> Namcap.package.load_from_db('uglycraft-git')
None
```

Because the release pkgbase's own package name `uglycraft` is one of the
`names` fed into `getcovered()`, and the installed `uglycraft-dev` package
*provides* `uglycraft`, `load_from_db('uglycraft')` resolves through
`lookup_provider()` to the installed `uglycraft-dev` package — whose real
`depends` array (`python`, `python-pygame`, `python-numpy`) is then pulled
into `global_deps`, silencing the rule for the release PKGBUILD purely by
accident. No installed package provides the name `uglycraft-git`, so the
same accidental coverage never happens for the `-git` PKGBUILD, and the rule
fires there.

**Conclusion: the release PKGBUILD's clean namcap run is not evidence that
it is actually correct** — it is an artifact of what happens to be installed
on the machine running namcap at audit time (a prior `poe package-dev`
build/install), not a property of the PKGBUILD itself. A namcap run on a
clean chroot/CI box with nothing named `uglycraft*` pre-installed would flag
the release `PKGBUILD` exactly as it flags `-git` today. The backlog's own
hedge ("this namcap pass only observed the warning on `-git`, it was not
confirmed absent on the release one") is correct, and the fix must apply to
all three PKGBUILDs identically.

### The fix, verified empirically

The backlog's fix hint speculated `makedepends=('python')` alone (i.e. just
the interpreter, not pygame/numpy) "may already satisfy namcap," reasoning
that only `python` is genuinely needed at build time (`package()` in all
three PKGBUILDs runs `python -c "import site; ..."` for `_site` detection
and `python -m compileall`, both build-time-only uses of the bare
interpreter — `python-pygame`/`python-numpy` are only *imported* at runtime,
never touched during `package()`).

This was tested locally on `packaging/PKGBUILD-git` (edited, namcap re-run,
then reverted with `git checkout --`, per the coordinator's instruction —
no PKGBUILD changes ship with this spec):

- `makedepends=('fpc' 'git' 'python')` → namcap **still** flags:
  `E: ... needs additional makedepends ['python-numpy', 'python-pygame']` —
  the `python` entry alone silences only itself; `python-pygame`/
  `python-numpy` remain missing from the rule's point of view, because the
  rule (`splitpkgbuild.py:60-62`) does a literal subset check of
  **subpackage `depends`** against `global_deps` — it does not know that
  `python-pygame`/`python-numpy` are only needed at import time, only that
  the subpackage declares them as `depends` and they are absent from
  `global_deps`.
- `makedepends=('fpc' 'git' 'python' 'python-numpy' 'python-pygame')` →
  namcap is clean of this finding (only the unrelated `Missing Maintainer
  tag` warning remains).

So the backlog's speculation was **wrong on the technical merits, right on
the intuition**: `python` is the only one *actually* needed to run
`package()`, but namcap's heuristic cannot distinguish "needed to build" from
"needed so the subset check passes," and mechanically requires the full
triple to be silenced. The correct, verified fix is to add all three —
`python`, `python-numpy`, `python-pygame` — to pkgbase-level `makedepends` in
all three PKGBUILDs. This is a documentation/hygiene fix (namcap compliance,
matching the guideline that a split package's `makedepends` must cover
everything any subpackage needs, whether at true build time or only to
satisfy the heuristic), not a change to the actual build behavior — none of
the three packages are freshly compiled or imported during `package()` in a
way that changes.

### Scope: pkgbase level, not per-subpackage

The rule (`splitpkgbuild.py:39-48`) only reads `makedepends`/`depends` from
the **pkgbase-level** `pkginfo`, and separately reads each subpackage's own
`depends`/`makedepends` (`local_deps`) — a `makedepends` line placed *inside*
a `package_uglycraft()` function body would be added to `local_deps`, not
`global_deps`, and would not satisfy the check. The fix must go on the
top-level `makedepends=(...)` array shared by both split packages in each
PKGBUILD, not inside a `package_*()` function.

## Done when:

- [ ] **D1–D3** — pkgbase-level `makedepends` in all three PKGBUILDs
  (`PKGBUILD`, `PKGBUILD-git`, `PKGBUILD-dev`) includes `python`,
  `python-numpy`, `python-pygame` in addition to the existing entries
  (`fpc`, plus `git` in `-git`/`-dev`).
- [ ] **D4** — `.SRCINFO`/`.SRCINFO-git` regenerated in the same commit,
  showing the three new `makedepends =` lines.
- [ ] **D5** — `namcap packaging/PKGBUILD` and `namcap packaging/PKGBUILD-git`
  both run clean of the split-makedeps finding; `poe package-dev` still
  builds `uglycraft-dev`/`ugli-dev` successfully.

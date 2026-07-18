# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Building and publishing distributables

Tasks are managed with **poethepoet** (`pyproject.toml`). `poe` is installed globally via pipx.

| Task | Action |
|---|---|
| `poe install` | Create venv and install all dependencies |
| `poe run` | Run the game (e.g. `poe run --level 5`) |
| `poe docs-install` | One-time: create `.venv-docs` and install MkDocs Material (local docs dev aid) |
| `poe docs` | Serve the local docs site (specs + kb) on localhost **and LAN** at `http://<host>:4001`. Local dev aid — **never published** (see below) |
| `poe build-linux` | Build `dist/linux-64/uglycraft` + license notices (~41 MB) |
| `poe setup-windows` | One-time: install Python 3.13 + deps into Wine |
| `poe build-windows` | Build `dist/windows-64/uglycraft.exe` + license notices (~25 MB) via Wine |
| `poe build-original` | Generate `git_sha.inc`, fetch UOS source (curl), and build `original/UGLI_2` with FPC |
| `poe clean` | Remove all build artifacts (`dist/`, `build/`, compiled Pascal output) |
| `poe deploy` | Push the three **live** itch.io channels (UGLYCRAFT Linux + Windows, original Linux) and the AUR release, with current git tag as version. Excludes `original-dos` — see note below |
| `poe deploy-uglycraft` | Push the UGLYCRAFT Linux and Windows channels only |
| `poe deploy-original-linux` | Push `dist/original-linux` to itch.io |
| `poe deploy-original-dos` | Push `dist/original-dos` to itch.io (manual only; see note) |
| `poe deploy-aur` | Copy release PKGBUILD + .SRCINFO to `../uglycraft-aur`, commit and push |
| `poe deploy-aur-git` | Copy git PKGBUILD + .SRCINFO to `../uglycraft-git-aur`, commit and push |
| `poe package-dev` | Build `uglycraft-dev`/`ugli-dev` from the local repo's own commit history — no push needed (local dev tool only, never deployed) |

Build and deploy are separate steps — deploy tasks only call butler, never build.
Windows build requires Wine installed via the system package manager; `poe setup-windows` handles the rest.
Version is read from the latest git tag automatically.

The **`original-dos` channel is frozen forever** — the original DOS executable
can never be rebuilt, so it is deliberately left out of the `poe deploy` bundle
and will not be redeployed. The `poe deploy-original-dos` task still exists for
the record, but there is no reason to run it again.

### Local documentation site (dev aid)

`poe docs` serves the `spec/` history and `kb/` articles as a browsable,
searchable MkDocs Material site (spec 0081). It is a **purely local development
aid** — served with `mkdocs serve`, reachable on localhost and the LAN
(`dev_addr: 0.0.0.0:4001`). The landing page teases the 5 most recent specs via a
native hook (`docs/hooks/recent_specs.py`, no plugin dependency; recency comes
from the zero-padded spec numbers, so no per-spec metadata is needed). `docs/` is
a symlink farm (`docs/spec → ../spec`, `docs/kb → ../kb`) so `spec/`/`kb/` stay in
place and their relative cross-links resolve. Docs deps live in a **separate**
`.venv-docs` (`requirements-docs.txt`) and never touch the game's `.venv` or the
PyInstaller build.

**This site is never published.** It must never become a GitHub Page: do not
enable Pages, do not add a `*pages*` workflow, do not create a `gh-pages` branch,
and **never run `mkdocs gh-deploy`** (the only command that would). A root
`.nojekyll` guards against accidental Jekyll rendering if Pages is ever switched
on. LAN reach is a local `mkdocs serve` process on the home network — not
internet publication.

The server listens on **port 4001**. A user-local systemd service —
`contrib/uglycraft-docs.service`, a `Type=simple` unit template — runs it
persistently. After `poe docs-install`, install it, set its path, and enable it:

```
cp contrib/uglycraft-docs.service ~/.config/systemd/user/
$EDITOR ~/.config/systemd/user/uglycraft-docs.service   # replace /path/to/uglycraft
systemctl --user daemon-reload
systemctl --user enable --now uglycraft-docs.service
```

Point the unit's `WorkingDirectory` at a durable checkout, never a
transient/throwaway working copy. Open port 4001 permanently in your firewall
since the service is durable (firewall-specific — e.g. firewalld:
`firewall-cmd --permanent --add-port=4001/tcp && firewall-cmd --reload`).

### Arch packaging

Two AUR packages, each with its own repo:

- **`uglycraft` / `ugli`** (release) — `packaging/PKGBUILD`, pinned to a
  release tag (`_tag=v1.5`).  Deployed with `poe deploy-aur` to
  `../uglycraft-aur`.  At release time, update `pkgver`, `_tag`, and run
  `updpkgsums` to fill in the real sha256 for the release tarball (source
  index 0, the only entry still `SKIP`); the four pinned external sums are
  re-verified in place and change only on a deliberate `_uos_commit`/
  `_themes_commit` bump.
- **`uglycraft-git` / `ugli-git`** (VCS) — `packaging/PKGBUILD-git`, clones
  the repo and derives `pkgver` from `git describe`.  Deployed with
  `poe deploy-aur-git` to `../uglycraft-git-aur`.  No tags to manage.

Each set `provides` and `conflicts` with the other so only one can be
installed at a time.

A third, **local-only** variant, `packaging/PKGBUILD-dev` (`uglycraft-dev` /
`ugli-dev`), builds from this checkout's own commit history via a
`git+file://` source instead of GitHub — so `makepkg` can be exercised
against local, not-yet-pushed commits (spec 0083). It has no `.SRCINFO`, is
never copied to an AUR sibling repo, and is never touched by any `poe
deploy*` task. Build it with `poe package-dev`.

## Session discipline

### One topic per session

Each session tackles exactly one topic. If a second topic surfaces mid-session
— a bug noticed in passing, a new idea, a tangential requirement — file it to
the backlog immediately via a spawned background agent and do not pursue it
further in the current session.

### Geometry rule

Before changing any geometric algorithm, produce a labeled ASCII diagram of the
before/after layout with explicit column/row numbers. Get explicit confirmation
that the diagram is correct **before writing any code**. Never reason about 2D
tile geometry purely from algebra.

### Backlog agent rule

New backlog items are added by spawning a background agent. The agent must also
**commit its own changes to `kb/backlog.md`** (one commit per invocation) so the
backlog is never left uncommitted — the main session does not commit on its
behalf:

```python
Agent(description="Add backlog item", run_in_background=True,
      prompt="Append to kb/backlog.md with the next BL-NN ID and priority P2: "
             "[description + fix hint]. Then `git add kb/backlog.md` and commit "
             "with a 'docs: add BL-NN ...' message (use the standard commit "
             "trailers). Committing the backlog requires no user confirmation.")
```

The main session never edits `kb/backlog.md` directly mid-task.
Project backlog is `kb/backlog.md`. Items use IDs BL-NN with priority P1/P2/P3.

### "What's next?" rule

When the user asks "what's next?", always spawn an agent to answer:

```python
Agent(description="What's next?",
      prompt="Read kb/backlog.md and summarise the open backlog items by priority. List P1 first, then P2, then P3. For each item show its ID, priority, one-line description, and the fix hint. Working directory: the repository root")
```

Never answer "what's next?" inline without spawning the agent.

### Level generator sessions

Load `kb/requirements.md` and `kb/architecture.md` at the start of every session
that touches `levelgraph.py` or `levellayout.py`.

## Knowledge base discipline

### Read first

Before reading any source file, read the relevant `kb/` articles. The KB is
compressed understanding of the codebase; reading code without it means
re-deriving facts that are already known.

### Write insights

Every non-trivial insight obtained during a session — a discovered invariant, a
confirmed assumption, a clarified mechanism, a "this is already done / not done"
finding — goes into the relevant KB article before the session ends. Do not leave
it only in the conversation.

### Link heavily

KB articles cross-reference each other with explicit `→ see kb/filename.md`
pointers when one article's content depends on or extends another.

### Review for staleness

At the start of any session touching a KB-covered topic, skim the relevant
articles for stale facts before trusting them.

---

## Development workflow

Every non-trivial change follows this sequence. Skipping a step requires an
explicit justification in the commit message.

### No machine-specific details in tracked docs

This repo is public. **Never write system/machine-specific details into a spec,
`kb/` article, this file, a tracked service unit, or any other committed
document.** That includes absolute home paths (`/home/<user>/…`), usernames,
personal host/service names (e.g. someone's private preview service), LAN IPs,
and other local-environment specifics. Use placeholders (`/path/to/uglycraft`),
repo-relative references ("the repository root"), or portable specifiers
(systemd `%h`) instead. Machine-specific values belong only in untracked local
files (e.g. an installed `~/.config/systemd/user/*.service`), never in the repo.

### 1 — Plan

Clarify scope and approach before touching any file. For architectural
decisions use plan mode; for smaller changes a short conversation is enough.
The plan's output is a committed spec file — not uncommitted notes.

### 2 — Spec

Write a spec file (`original/spec/<topic>.md` for Pascal work; an inline
comment block for Python work where a separate file would be disproportionate).
Every spec must contain:
- A **status checklist** at the top — one line per deliverable, using GFM
  syntax: `- [ ]` (not yet done) / `- [x]` (confirmed working).
- A **"Done when:"** section at the bottom listing the acceptance criteria.

Commit the spec alone, before any implementation code.

**After committing the spec, stop and wait for the user to confirm it before
proceeding to tests or implementation.** Never move from step 2 to step 3
without an explicit confirmation message. The user may want to adjust scope,
wording, or approach before any code is written.

### 3 — Tests (`original/` Pascal work only)

Add tests to `UGLI_2_Test.pp` that cover the required behaviour.
Run `poe test-original` and confirm the new tests are **red**.
Implement until the suite is **green** (`poe test-original` exits 0).
A task is not complete while a test it introduced is still failing.

For Python/UGLYCRAFT work there is no automated suite; describe the manual
verification steps in the spec instead.

### 4 — Implement

Write the code. Keep commits on topic — one logical concern per commit
(see global CLAUDE.md commit-discipline rules).

### 5 — Gates (Pascal / `original/` work)

Both must pass before the work is called done:

```
poe build-original   # zero compiler errors
poe test-original    # all tests pass, exit 0
```

Spec items labelled "manual check" or "user acceptance" may only be marked ✓
after the user has **explicitly stated in a message** that the behaviour works
correctly. An exit code of 0 or a process completing without error is not
confirmation. Never infer acceptance from tooling output alone.

### 6 — Maintain living documents

After every substantive commit to `original/` (Pascal work):

| Document | What to update |
|---|---|
| `original/CHANGELOG.md` | Add entries to `[Unreleased]`; merge into existing category headings |
| `original/CLAUDE.md` | Update if data structures, procedures, file layout, or `uses` clause changed |
| Spec checklist | Mark items `- [x]` only after the user confirms the behaviour works |

After every substantive commit to UGLYCRAFT (Python work):

| Document | What to update |
|---|---|
| `CHANGELOG.md` (root) | Add player-facing entries to `[Unreleased]` — the UGLYCRAFT changelog, written for a general audience (not the Pascal port's `original/CHANGELOG.md`) |
| `CLAUDE.md` (this file) | Update the **Architecture** table (file count + roles) if a Python module was added/removed/repurposed, and the **Knowledge base** table if a `kb/` file was added/removed |
| `kb/feature-inventory.md` | Record new/changed features and their spec links |
| Spec checklist | Mark items `- [x]` only after the user confirms the behaviour works |

After a release (new git tag + `poe deploy`):

| Document | What to update |
|---|---|
| `CLAUDE.md` (this file) | Bump **Current version** |
| `CHANGELOG.md` (root) | Close `[Unreleased]` into a versioned section |
| `original/CHANGELOG.md` | Close `[Unreleased]` into a versioned section |

## Licensing

UGLYCRAFT is GPLv3. Distributables also bundle pygame (LGPL 2.1) and numpy (BSD 3-Clause).
License texts live in `LICENSES/` and are copied into each build by the poe tasks.
`LICENSES/NOTICE.txt` summarises what is bundled and under what terms.

## Current version

**v1.5** — bump this whenever a new git tag is created.

## What this is

This repo contains two things:

1. **The original game** — UGLI (version 2, 1996), a DOS text-mode game written in Turbo Pascal 7 by Daniel Bausch. Source files: `UGLI_2.pp`, plus `UOSSound.pp` (FPC/Linux sound via UOS + PortAudio). See [`original/CLAUDE.md`](original/CLAUDE.md) for a full analysis of the original code, data structures, and mechanics.

2. **UGLYCRAFT** — a new Python/pygame spiritual remake of UGLI, written from scratch. This is the active project.

## Knowledge base

`kb/` contains reference files loaded on demand — not always in context.
Use them when working on a topic that needs deeper background.

| File | Contents |
|---|---|
| `kb/feature-inventory.md` | Hierarchical map of all implemented aspects with spec links and test-coverage status |
| `kb/world-model-review.md` | SE review of the runtime world model: pain points + staged refactoring plan (World extraction, tile map, dispatch) |
| `kb/uglycraft-mechanics.md` | Scoring, lives, shield, speed formula, state machine, boss behaviour |
| `kb/uglycraft-levels.md` | Wall layouts and enemy start positions for the 10 hand-authored Act 1 levels |
| `kb/uglycraft-layouts.md` | Act 2 layout-strategy reference: grid/diagram notation, the corridor/zone strategies, worked examples |
| `kb/uglycraft-display.md` | Integer scaling, HUD layout, sprite construction notes |
| `kb/uglycraft-sound.md` | Sound generation, music keys, trigger map, fallback behaviour |
| `kb/findings.md` | Bugs, quirks, and key differences between Pascal original and Python remake |
| `kb/requirements.md` | Formal numbered invariants for the level generator (load for any levelgraph/levellayout session) |
| `kb/architecture.md` | Level generator pipeline, data structures, layout strategies, target architecture |
| `kb/backlog.md` | Prioritised bug and improvement backlog (IDs BL-01…) |
| `kb/arch-packaging.md` | Arch/AUR packaging compliance audit: findings vs the guidelines, verified-correct list, first-push operational steps |

`original/kb/` covers the Pascal source — see `original/CLAUDE.md`.

## System prerequisites

| Tool | Required for |
|---|---|
| `fpc` (Free Pascal) | `poe build-original`, `poe test-original` |
| `curl` | `poe build-original` (fetches UOS source + `ANSI-87.conf` on first run) |
| `libportaudio.so.2` | `poe run-original` (runtime sound; fails silently if absent) |
| `wine` | `poe setup-windows`, `poe build-windows` |
| `butler` (itch.io) | all `poe deploy*` tasks |

## Running UGLYCRAFT

```bash
pipx install poethepoet   # one-time; virtualenv via package manager
poe install               # creates .venv and does an editable install (pip install -e ".[dev]")
poe run
```

Or directly: `.venv/bin/python -m uglycraft --level N --easy/--hard`

In debug mode (`--level`) the high-score entry screen is suppressed.

## Architecture (`src/uglycraft/` package — 16 modules)

The game is a package under `src/uglycraft/`, installed editable (`pip install
-e ".[dev]"`, via `poe install`) and run with `python -m uglycraft` (spec 0080;
`src/` layout + editable install: spec 0082). The repo root holds only
`run_game.py`, the PyInstaller launcher; assets live inside the package at
`src/uglycraft/fonts/` and `src/uglycraft/translations/`.

| File | Role |
|---|---|
| `src/uglycraft/__main__.py` | `python -m uglycraft` entry point — imports and calls `main()` |
| `src/uglycraft/constants.py` | Logical resolution, tile size, colours, timing, wall types |
| `src/uglycraft/hud.py` | HUD layout primitives: `HudElement`/`LabelValue`/`IconStrip` + an `HBox` that distributes slack across the `n-1` gaps and draws subtle gap separators (spec 0072) |
| `src/uglycraft/sprites.py` | All sprites drawn procedurally via `pygame.draw` — no image files |
| `src/uglycraft/levels.py` | Act 1 levels (hand-authored) + Act 2 levels (graph-generated lazily per level on demand, spec 0028) |
| `src/uglycraft/entities.py` | `Player`, `Enemy`, `PatrolEnemy`, `ForgeOgre` (breaks placed walls) — tile-grid movement, BFS pathfinding, room confinement |
| `src/uglycraft/hiscore.py` | Top-10 score persistence to `uglycraft.hsc` |
| `src/uglycraft/sounds.py` | `SoundManager` — 14 procedural SFX + 12 music tracks |
| `src/uglycraft/cells.py` | Layered cell model: terrain (floor/water) + Barrier/Bridge fixtures per cell, one parser from room data (spec 0047) |
| `src/uglycraft/world.py` | **Pygame-free** gameplay rules: all world state, movement/push/bump, rooms, hazards, pickups; passability as a query over cells; emits a typed event stream (specs 0045–0047) |
| `src/uglycraft/game.py` | Presentation: menu state machine, input translation, rendering, inventory/crafting UI; maps world events → sounds/music/flash |
| `src/uglycraft/main.py` | Window creation, integer scaling, top-level event loop |
| `src/uglycraft/crafting.py` | Materials, tools, keys, recipes, `Inventory` class |
| `src/uglycraft/rooms.py` | Live `Room` objects (persist by identity, spec 0051), exit detection |
| `src/uglycraft/levelgraph.py` | Graph model (`Node`, `Edge`, `LevelGraph`), generation, playability validation |
| `src/uglycraft/levellayout.py` | Layout algorithm: graph → one or more 30×16 grids, wall derivation, Sokoban solver |
| `src/uglycraft/leveldump.py` | Pygame-free ASCII export of a loaded level (`--dump-level`) via the real `start_level` path; single- and multi-grid canvases (specs 0064/0065) |
| `run_game.py` | Repo-root PyInstaller entry: `from uglycraft.main import main; main()` (runs as `__main__` outside package context; imports the installed `uglycraft`, not a relative path) |

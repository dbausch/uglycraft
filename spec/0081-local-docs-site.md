# Spec 0081 — Local MkDocs dev-aid site (serve-only, never published)

A **local** documentation aid: browse and full-text-search the 80 `spec/`
files and the 12 `kb/` articles in a rendered, navigable web view via
`mkdocs serve`, reachable on `localhost` **and across the LAN** (the dev server
binds `0.0.0.0` so a phone or another dev machine on the network can read it).
The landing page **lists the 5 most recent specs with their
checklist progress**. It is a development convenience only — LAN reach is *not* internet publication: it must **never**
become a GitHub Page, and the setup deliberately makes accidental publication
impossible. (LAN serving is a local process on the home network; it is orthogonal
to the never-a-Page guarantee below.)

Chosen over Jekyll (decision 2026-07-17): MkDocs Material is Python (matches the
`poe`/`pipx`/`.venv` toolchain), auto-rewrites relative `.md` links so navigation
works, keeps `spec/` and `kb/` exactly where they are (the spec-numbering
workflow and the `kb/ → ../spec/NNNN.md` cross-links depend on it), and — unlike
Jekyll — leaves **no root `_config.yml`**, the exact artifact GitHub Pages
auto-detects. → Background discussion & tiering: this session's conversation.

**Scope.** Minimal serve-only browse + search, plus a lightweight "recent specs"
list (with per-spec checklist progress) on the landing page. The full
reverse-chronological **blog/feed** view (which would need per-spec `date`
frontmatter on all 80 files and the blog plugin) is **explicitly out of scope** —
considered and rejected as too much machinery for a local dev aid; the
recent-specs list (D3) covers the "what's new" need with none of it. See
*Deferred*.

## Status checklist

- [x] **D1** — `mkdocs.yml` at repo root: Material theme, `docs_dir: docs`,
  `site_dir: site`, built-in search enabled, `use_directory_urls: true`,
  `dev_addr: 0.0.0.0:4001` (serve on localhost **and LAN**), auto-generated nav
  (no hand-maintained `nav:`), non-strict link validation set to **warn** (so a
  stray link never breaks `poe docs`), and a `hooks:` entry registering the
  recent-specs hook (D3).
- [x] **D2** — `docs/` symlink farm preserving the real tree so relative links
  resolve identically to GitHub: `docs/spec → ../spec`, `docs/kb → ../kb`, plus a
  hand-written `docs/index.md` landing page containing a `<!-- RECENT_SPECS -->`
  placeholder. `spec/` and `kb/` files are **not moved** — only symlinked.
- [x] **D3** — recent-specs list: a **native MkDocs hook**
  (`docs/hooks/recent_specs.py`, referenced from `mkdocs.yml` `hooks:` — a
  built-in feature, **not** a plugin dependency) that, on `on_page_markdown` for
  `index.md`, replaces `<!-- RECENT_SPECS -->` with the **5 highest-numbered
  specs**, newest first — each an ordinary relative link titled from the spec's
  `#` H1, followed by a **progress bar** (`done/total`) computed from that spec's
  status checklist. No per-spec frontmatter; no blog plugin; specs stay ordinary
  pages.
- [x] **D4** — docs dependencies isolated from the game: `requirements-docs.txt`
  (just `mkdocs-material`); `poe docs-install` builds a **separate** `.venv-docs`;
  `poe docs` runs `.venv-docs/bin/mkdocs serve`. The game's `.venv`,
  `requirements.txt`, and `[project].dependencies` are left untouched (mkdocs must
  never enter the PyInstaller build).
- [x] **D5** — `.gitignore` gains `site/` and `.venv-docs/` (build output +
  docs venv never committed).
- [x] **D6** — "never a Page" guardrails in place and documented: an empty root
  `.nojekyll` (disables Jekyll processing *if* Pages is ever switched on); no
  `.github/workflows/*pages*`, no `gh-pages` branch, no `/docs`-as-Pages-source;
  and a written note that `mkdocs gh-deploy` (the only command that publishes)
  must never be run.
- [x] **D7** — `CLAUDE.md` updated: `poe docs` / `poe docs-install` rows added to
  the task table with a one-line "local docs dev aid — never published" note.
- [x] **D8** — verification pass (per *Verification* below): the landing
  page lists the 5 newest specs correctly, all 80 specs + 12 kb pages render, GFM
  checklists render as checkboxes, search works, and every `kb/ → ../spec/` link
  navigates without a 404.
- [x] **D9** — the docs server runs on **port 4001** (not the busy 8000), and a
  **user-local systemd service** manages it — a tracked unit *template*
  (`contrib/uglycraft-docs.service`): a standard `Type=simple` service
  (`WorkingDirectory` at the checkout, `--dev-addr 0.0.0.0:4001`,
  `Restart=on-failure`, `WantedBy=default.target`), installed to
  `~/.config/systemd/user/`. The tracked template carries **no machine-specific
  paths** — it uses a `/path/to/uglycraft` placeholder the installer fills in. It
  becomes active once the branch is on the checkout's default branch and
  `poe docs-install` has been run there (point the unit at a durable checkout,
  never a transient/throwaway copy).

## Design

### Recent-specs list (no blog, no frontmatter)

Recency is already encoded in the filenames: spec IDs are **monotonic and
zero-padded**, so the 5 most recent specs are simply the 5 highest-numbered files
(`ls spec/ | tail -5`) — no dates, no metadata. The list is rendered by a
**native MkDocs hook** (`hooks:` is a documented MkDocs feature — a Python module
wired to build events, requiring no dependency beyond mkdocs itself):

- `docs/hooks/recent_specs.py` implements `on_page_markdown(markdown, page, …)`;
- for `index.md` only, it lists the last 5 specs (by number, descending) and
  substitutes them for the `<!-- RECENT_SPECS -->` placeholder;
- each entry is an **ordinary relative link** `[<id> — <H1 title>](spec/<file>)`,
  the title lifted from the spec's `#` heading, followed by a **progress bar**
  (`` `▰▰▰▱▱▱▱▱▱▱` done/total ``) computed from the spec's status checklist:
  `- [x]` (done) vs `- [ ]` (open) items counted **only in the top `## Status`
  section** — the scan stops at the next `##`, so the duplicate `## Done when:`
  list is never double-counted. Progress therefore tracks confirmed acceptance
  (items go `- [x]` only after the user confirms), so a built-but-unaccepted spec
  reads low on purpose.

Because the specs remain ordinary pages, their links are ordinary and nothing is
relocated — the blog plugin's URL-rewriting risk simply doesn't exist here.
**Ordering = spec number** (newest = highest), which matches "newest specs" and
needs no git calls; switching to "recently *edited*" (git commit date) would be a
one-line change in the hook.

*(Alternative considered: the `mkdocs-gen-files` plugin does index generation
idiomatically but adds a dependency; the native hook is lighter and self-contained,
so it is preferred.)*

### Why not `docs_dir: .`

MkDocs forbids `docs_dir` being the project root, because the default
`site_dir: site/` would then nest inside `docs_dir` (hard error). So the content
cannot be served in place from the root. The cross-links are the
`kb/architecture.md → ](../spec/0007-….md)` form — relative to each file — so
whatever is served must keep `spec/` and `kb/` as **siblings** under one served
root. The symlink farm (D2) gives exactly that: `docs/spec` and `docs/kb` sit
side by side under `docs/`, so `../spec/…` resolves the same as on GitHub, while
`site/` stays outside `docs/`. MkDocs follows symlinks, and `mkdocs serve`'s
watcher fires live-reload when a real `spec/`/`kb/` file is edited through the
link.

### Navigation & titles

No hand-maintained `nav:` — MkDocs auto-builds the sidebar from the file tree.
The zero-padded IDs (`0001`…`0081`) mean **alphabetical order == numeric order**,
so specs list chronologically for free. Auto-nav labels come from the filenames
(`0001-shield-rework.md → "0001 Shield Rework"`) — numbered and titled, good
enough for a dev aid. `docs/index.md` is the landing page.

### Link validation

`strict` stays **off** so `poe docs` is always resilient, but
`validation.links.*` is set to `warn`. The warning log doubles as a free
link-checker for the `kb/ → ../spec/` references (D8 uses it as the signal).

### Dependency isolation

```
requirements-docs.txt         # mkdocs-material  (pulls mkdocs + deps)
poe docs-install → virtualenv .venv-docs && .venv-docs/bin/pip install -r requirements-docs.txt
poe docs         → .venv-docs/bin/mkdocs serve   # binds 0.0.0.0:4001 (dev_addr), live-reload
```

A dedicated `.venv-docs` keeps mkdocs out of the game's runtime `.venv` (which
PyInstaller bundles) — the two never mix. The LAN bind (`dev_addr: 0.0.0.0:4001`
in `mkdocs.yml`) lets other devices on the home network reach the site at
`http://<host-LAN-IP>:4001`; it is still just a local `mkdocs serve` process,
never a published site.

### Port & systemd service (D9)

The server listens on **port 4001** (8000 is heavily used by other dev tools).
`dev_addr: 0.0.0.0:4001` in `mkdocs.yml` sets this for `poe docs`; the systemd
unit passes `--dev-addr 0.0.0.0:4001` explicitly as well.

A **user-local systemd service** runs it persistently — a standard
`~/.config/systemd/user/` unit (`Type=simple`, `--dev-addr 0.0.0.0:4001`,
`Restart=on-failure`, `WantedBy=default.target`). The tracked unit
`contrib/uglycraft-docs.service` is a **template with a placeholder path** (no
machine-specific paths in the repo):

```ini
[Service]
Type=simple
WorkingDirectory=/path/to/uglycraft
ExecStart=/path/to/uglycraft/.venv-docs/bin/mkdocs serve --dev-addr 0.0.0.0:4001
Restart=on-failure
RestartSec=3
```

At install time, replace `/path/to/uglycraft` with the absolute path to the
checkout (or a `%h/…` specifier). **Crucial:** point `WorkingDirectory` at a
**durable checkout**, never a transient/throwaway working copy — so the service
only functions once the branch is on that checkout's default branch and
`poe docs-install` has created `.venv-docs` there. Until then the unit is left
un-enabled; enable it with:

```
systemctl --user enable --now uglycraft-docs.service
```

The firewall rule for 4001 should be **permanent** (the service is durable),
unlike the temporary 8000 rule used during development. Opening a port is
firewall-specific (e.g. firewalld: `firewall-cmd --permanent --add-port=4001/tcp
&& firewall-cmd --reload`).

### Why this cannot accidentally publish

GitHub never auto-renders markdown. Pages goes live only via one of four
deliberate actions, none of which this setup performs or leaves lying around:
enabling Pages in repo Settings; a `*pages*` deploy workflow (none added);
selecting `/docs` as a Pages source (that's a *Settings* choice — the folder
existing does nothing); or a `gh-pages` branch (never created — only
`mkdocs gh-deploy` makes one, and it is forbidden). The root `.nojekyll` is
belt-and-suspenders: if Pages is *ever* enabled by mistake, it disables Jekyll
processing rather than rendering the repo. `mkdocs.yml` itself is inert to
GitHub.

## Deferred (explicitly out of scope for this spec)

- **Blog / reverse-chron spec feed** with per-spec `date` + `status` frontmatter
  (backfill across all 80 files) and Material's blog plugin — rejected as too
  much machinery for a local dev aid. The recent-specs list (D3) covers the
  "what's new" need without it. Revisit only if a full paginated feed is wanted.
- **Surfacing root docs** (`README.md`, `CHANGELOG.md`) — their root-relative
  asset/link paths need handling; left out to keep the first cut tight.

## Verification (manual — no automated suite for docs tooling)

Per `CLAUDE.md` step 3, UGLYCRAFT infra work states its manual checks in the
spec rather than adding pytest coverage:

1. `poe docs-install` creates `.venv-docs` with mkdocs-material; game `.venv`
   and `poe build-linux` output are unaffected.
2. `poe docs` serves at `http://127.0.0.1:4001` **and** is reachable from another
   LAN device at `http://<host-LAN-IP>:4001`; the landing page loads and its
   **"Recent specs"** section lists the 5 highest-numbered specs newest-first,
   each linking to the right spec page (title from that spec's H1) with a
   progress bar whose `done/total` matches that spec's `## Status` checklist.
3. All 80 specs appear under a `spec` nav section in numeric order; opening a few
   shows H1 titles and GFM `- [x]`/`- [ ]` checklists rendered as checkboxes.
4. All 12 kb pages render; clicking a `kb/ → ../spec/…` link lands on the right
   spec (rewritten URL, no 404). The `mkdocs serve` log shows no link warnings
   for `kb → spec` references.
5. The search box finds a term spanning both `spec/` and `kb/`.
6. Publication is impossible: `git status` shows no `*pages*` workflow and no
   `gh-pages` branch; `.nojekyll` exists at root; `site/` and `.venv-docs/` are
   gitignored; `poe docs` pushes nothing.
7. **Port & service:** the server binds `0.0.0.0:4001` (not 8000). After the
   branch is merged to main and `poe docs-install` is run there,
   `systemctl --user enable --now uglycraft-docs.service` starts it, and
   `systemctl --user status uglycraft-docs.service` shows *active (running)*
   serving on 4001 across the LAN; it comes back up after `systemctl --user
   restart` and on next login.

## Done when:

- [x] **D1** `mkdocs.yml` present and valid, hook registered (`mkdocs build`
  exits 0, no warnings) — commits `9b83022`, `e5cb787` (verified 2026-07-18).
- [x] **D2** `docs/` symlink farm + `docs/index.md` (with placeholder) present;
  `spec/`/`kb/` files unmoved (tracked as symlinks); relative `kb → ../spec`
  links resolve with no build warnings — commit `9b83022` (index trimmed
  `b1441d3`, `2af1e4a`; verified 2026-07-18).
- [x] **D3** recent-specs hook renders the 5 newest specs from filenames alone
  (no frontmatter), each with a checklist progress bar whose `done/total` matches
  a ground-truth recount — commits `9b83022`, `a484a47` (verified 2026-07-18).
- [x] **D4** `requirements-docs.txt`, `poe docs-install`, `poe docs` added;
  `.venv-docs` separate; game `requirements.txt` has no mkdocs — commit `9b83022`
  (verified 2026-07-18).
- [x] **D5** `.gitignore` ignores `site/` and `.venv-docs/` (`git check-ignore`
  confirms) — commit `9b83022` (verified 2026-07-18).
- [x] **D6** root `.nojekyll` added; no `*pages*` workflow, no `gh-pages` branch —
  commit `9b83022` (verified 2026-07-18).
- [x] **D7** `CLAUDE.md` task table documents `poe docs` / `poe docs-install` as
  a local, never-published dev aid — commits `2be01e1`, `e5cb787`, `63046a2`
  (verified 2026-07-18).
- [x] **D8** verified: 81 spec + 12 kb pages render, GFM checklists render as
  checkboxes, search index built, every `kb → ../spec` link resolves, nothing
  publishes; mobile layout user-confirmed — verified 2026-07-18.
- [x] **D9** port 4001 + unit template `contrib/uglycraft-docs.service` tracked
  and installed to `~/.config/systemd/user/`; squash-merged to `main` (`1075e4c`),
  `poe docs-install` run in the main checkout, and `systemctl --user enable --now
  uglycraft-docs.service` now runs it **active (running)** from the main checkout —
  serving `0.0.0.0:4001` on the LAN and recovering on `systemctl --user restart` —
  commits `e5cb787`, `a6b193a`, `63046a2` (verified 2026-07-18).

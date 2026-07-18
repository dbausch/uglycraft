"""MkDocs hook: render the 5 most recent specs on the landing page.

Recency is taken straight from the zero-padded spec IDs (highest number = newest),
so **no per-spec metadata is required** — no ``date:`` frontmatter, no blog
plugin. On ``index.md`` the ``<!-- RECENT_SPECS -->`` marker is replaced with a
bulleted list of the newest specs, each an ordinary relative link titled from the
spec's ``#`` H1, followed by a **progress bar** computed from that spec's status
checklist (``- [x]`` done vs ``- [ ]`` open, counted in the top ``## Status``
section only — never the duplicate ``## Done when:`` list).

Registered from ``mkdocs.yml`` via ``hooks:`` — a built-in MkDocs feature, not a
plugin dependency.  See ``spec/0081-local-docs-site.md``.
"""

from __future__ import annotations

import os
import re
from glob import glob

MARKER = "<!-- RECENT_SPECS -->"
RECENT_COUNT = 5
BAR_CELLS = 10

# NNNN-topic.md
_SPEC_NAME = re.compile(r"^\d{4}-.*\.md$")
# Strip a redundant "Spec NNNN — " prefix already present in many H1s.
_H1_PREFIX = re.compile(r"^Spec\s+\d+\s*[—:-]\s*", re.IGNORECASE)
# The top overview checklist: "## Status" / "## Status checklist".
_STATUS_HEADING = re.compile(r"^##+\s*Status\b", re.IGNORECASE)
_H2 = re.compile(r"^##\s")
_DONE = re.compile(r"^- \[[xX]\]")
_TODO = re.compile(r"^- \[ \]")


def _title(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("# "):
            return _H1_PREFIX.sub("", line[2:].strip())
    return ""


def _progress(lines: list[str]) -> tuple[int, int]:
    """(done, total) from the first `## Status` checklist; (0, 0) if none.

    Counts only top-level `- [ ]` / `- [x]` items in that section, stopping at
    the next `##` heading so the bottom `## Done when:` duplicate is excluded.
    """
    in_section = False
    done = total = 0
    for line in lines:
        if not in_section:
            if _STATUS_HEADING.match(line):
                in_section = True
            continue
        if _H2.match(line):
            break
        if _DONE.match(line):
            done += 1
            total += 1
        elif _TODO.match(line):
            total += 1
    return done, total


def _bar(done: int, total: int) -> str:
    """A BAR_CELLS-wide filled/empty block bar; never misleadingly full/empty."""
    if done >= total:
        filled = BAR_CELLS
    else:
        filled = round(done / total * BAR_CELLS)
        filled = min(BAR_CELLS - 1, max(1 if done else 0, filled))
    return "▰" * filled + "▱" * (BAR_CELLS - filled)


def _recent_block(spec_dir: str) -> str:
    files = sorted(
        (
            p
            for p in glob(os.path.join(spec_dir, "*.md"))
            if _SPEC_NAME.match(os.path.basename(p))
        ),
        reverse=True,
    )[:RECENT_COUNT]

    if not files:
        return "_No specs found._"

    items = []
    for path in files:
        name = os.path.basename(path)
        ident = name.split("-", 1)[0]
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        title = _title(lines) or name
        done, total = _progress(lines)
        line = f"- [**{ident}** — {title}](spec/{name})"
        if total:
            # Two trailing spaces = hard line break, so the bar sits under the
            # link within the same list item.
            line += f"  \n  `{_bar(done, total)}` {done}/{total}"
        items.append(line)

    return "\n".join(items)


def on_page_markdown(markdown, *, page, config, files, **kwargs):
    if page.file.src_uri != "index.md" or MARKER not in markdown:
        return markdown
    spec_dir = os.path.join(config["docs_dir"], "spec")
    return markdown.replace(MARKER, _recent_block(spec_dir))

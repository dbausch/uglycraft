# FPC build environment quirks

System-level issues that affect `poe build-original` / `poe test-original`
(anything compiled with FPC) but live outside this repository.

## Missing `crtbeginS.o` / `crtendS.o` → stale gcclib path in `/etc/fpc.cfg`

**Symptom:** at link time FPC warns that `crtbeginS.o` and `crtendS.o` cannot
be found (e.g. `Warning: "crtbeginS.o" not found, this will probably cause a
linking failure`). The build may still succeed, but the warning must not be
ignored — report it whenever it appears.

**Cause:** `/etc/fpc.cfg` hardcodes the gcclib search path (`-Fl` lines under
the `# path to the gcclib` comment) to a specific GCC major version, e.g.
`-Fl/usr/lib/gcc/x86_64-pc-linux-gnu/16`. When the system GCC gets a major
upgrade, the old versioned directory disappears and the path goes stale —
the `crt*S.o` startup files live inside that versioned directory.

**Fix:** update the `-Fl` gcclib lines in `/etc/fpc.cfg` to the currently
installed GCC version directory (check with
`ls /usr/lib/gcc/x86_64-pc-linux-gnu/`), or regenerate the whole file with
`fpcmkcfg -d basepath=/usr/lib/fpc/$fpcversion -o /etc/fpc.cfg`. Verify with
a rebuild: the warning must be gone.

**History:** happened at least twice (last recurrence and manual fix:
2026-07-18, after a GCC major bump on Arch). If it reappears during a
session, tell the user immediately instead of letting the build's exit code 0
mask it.

→ see `original/kb/sound-system.md` for the other external build input
(fetched UOS sources; pinned to a fixed commit since spec 0089).

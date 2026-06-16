# CLI help screen — --help / -h

## Status

- [x] `resourcestring` entries for help text added to `UGLI_2_Core.inc`
- [x] `CLIHelpText: string` function added to `UGLI_2_Core.inc`
- [x] `ShowCLIHelp` procedure added to `UGLI_2_Core.inc`
- [x] `TCliHelpTests` added to `UGLI_2_Test.pp`
- [x] CLI parsing refactored to `ParseCLI` (getopts); `--help`/`-h` handled there
- [x] `translations/de.po` updated with German strings; `de.mo` recompiled
- [x] `poe build-original` passes
- [x] `poe test-original` passes
- [x] `./UGLI_2 --help` and `-h` print correctly in English (confirmed by user)
- [x] `LC_ALL=de_DE.UTF-8 ./UGLI_2 --help` prints correctly in German (confirmed by user)
- [x] `poe run-original --help` prints in the calling terminal, no kitty window (confirmed by user)

---

## Done when

- [x] `poe build-original` exits 0 (b0c3f0c)
- [x] `poe test-original` exits 0 (b0c3f0c)
- [x] `./UGLI_2 --help` and `-h` both print help in English and exit 0 (confirmed by user)
- [x] `LC_ALL=de_DE.UTF-8 ./UGLI_2 --help` prints German text (confirmed by user)
- [x] `poe run-original --help` prints in calling terminal (0658f89; confirmed by user)

Key commits: b0c3f0c (initial implementation), b970db0 (red tests),
83e6beb (getopts/ParseCLI refactor), 80e11c5 (unknown/missing-arg → help),
0658f89 (--help skips kitty), d85a25b (--level help text fix).

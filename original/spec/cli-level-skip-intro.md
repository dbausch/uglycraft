# CLI options: --skip-intro and --level N

## Status

- [x] `SkipIntro: Boolean = false` and `StartAtLevel: Integer = 0` added to `UGLI_2_Core.inc`
- [x] `Init` checks `SkipIntro` before `Intro`; checks `StartAtLevel = 0` before `ShowItemDescriptions`
- [x] CLI parsing refactored to `ParseCLI` (getopts) in `UGLI_2_Core.inc`; `NewGame:` uses `StartAtLevel`
- [x] `CLIHelpText` updated with two new options; resourcestrings + de.po translations added
- [x] `poe run-original` forwarding fixed: `$POE_EXTRA_ARGS`; `--help` skips kitty
- [x] `TCliHelpTests` extended with two new assertions
- [x] `poe build-original` passes
- [x] `poe test-original` passes (130 tests)
- [x] `poe run-original --level 5` starts at level 5 without intro (confirmed by user)
- [x] `poe run-original --skip-intro` skips animated intro, still shows item-descriptions (confirmed by user)

---

## Behaviour

| Invocation | Effect |
|---|---|
| `./UGLI_2` | Normal startup: animated intro + item-descriptions screen, then level 1 |
| `./UGLI_2 --skip-intro` | Skip animated intro; item-descriptions screen still shown; start at level 1 |
| `./UGLI_2 --level 5` | Skip both intro and item-descriptions; start at level 5 |
| `./UGLI_2 --skip-intro --level 3` | Same as `--level 3` |
| `poe run-original --level 5` | As above, via poe |

Level is clamped to `[1..9]`. F4 (restart) returns to `StartAtLevel`, not always 1.
`StartAtLevel = 0` (default) means "not set via --level"; game starts at level 1 and
shows item-descriptions. Any explicit `--level N` sets `StartAtLevel` to a non-zero
value, which also gates the item-descriptions skip.

---

## Done when

- [x] `poe build-original` exits 0 (a31e1cd)
- [x] `poe test-original` exits 0, 130 tests pass (a31e1cd)
- [x] `poe run-original --level 5` opens at level 5 with no intro (confirmed by user)
- [x] `poe run-original --skip-intro` skips animated intro, shows item-descriptions, starts at level 1 (confirmed by user)
- [x] `poe run-original --help` prints help in calling terminal, no kitty window (0658f89)

Key commits: a31e1cd (initial), e247c68 (loop bound fix), b4ff4ef ($POE_EXTRA_ARGS),
1d09626 (--skip-intro/--level split), a3f7793 (StartAtLevel=0 sentinel),
83e6beb (getopts/ParseCLI), 0658f89 (--help to calling terminal).

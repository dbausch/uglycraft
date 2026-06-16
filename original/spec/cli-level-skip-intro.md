# CLI options: --skip-intro and --level N

## Status

- [ ] `SkipIntro: Boolean = false` and `StartAtLevel: Integer = 1` added to `UGLI_2_Core.inc`
- [ ] `Init` checks `SkipIntro` before calling `Intro` / `ShowItemDescriptions`
- [ ] `UGLI_2.pp` main block parses `--skip-intro` and `--level N`; `--level N > 1` implies skip-intro
- [ ] `NewGame:` label uses `StartAtLevel` instead of hard-coded `1`
- [ ] `CLIHelpText` updated with two new options; resourcestrings + de.po translations added
- [ ] `poe run-original` shell updated to append `"$@"` so args are forwarded to the binary
- [ ] `TCliHelpTests` extended with two new assertions (red before implementation)
- [ ] `poe build-original` passes
- [ ] `poe test-original` passes (130 tests)
- [ ] `poe run-original -- --level 5` starts at level 5 without intro (confirmed by user)
- [ ] `poe run-original -- --skip-intro` skips intro but starts at level 1 (confirmed by user)

---

## Behaviour

| Invocation | Effect |
|---|---|
| `./UGLI_2` | Normal startup: intro + item descriptions, then level 1 |
| `./UGLI_2 --skip-intro` | Skip intro and item descriptions; start at level 1 |
| `./UGLI_2 --level 5` | Skip intro; start at level 5 (implies --skip-intro) |
| `./UGLI_2 --skip-intro --level 3` | Same as `--level 3` |
| `poe run-original -- --level 5` | As above, via poe |

Level is clamped to `[1..9]`. F4 (restart) returns to `StartAtLevel`, not always 1.

---

## What changes

### `UGLI_2_Core.inc` — new variables

In the second `var` block (near `WBuf`, `DumpFd`):

```pascal
SkipIntro   : Boolean = false;
StartAtLevel: Integer = 1;
```

### `UGLI_2_Core.inc` — `Init`

```pascal
{ OLD }
Intro(...);
ShowItemDescriptions;
FillScreen(FieldBg);

{ NEW }
if not SkipIntro then
  begin
    Intro(...);
    ShowItemDescriptions;
  end;
FillScreen(FieldBg);
```

### `UGLI_2_Core.inc` — `CLIHelpText` + new resourcestrings

New resourcestrings:
```pascal
sCliSkipIntro = 'Skip the intro and item-descriptions screen.';
sCliLevel1    = 'Start at level N (1–9; default: 1). Implies --skip-intro.';
```

Updated `CLIHelpText` adds:
```
  --skip-intro
      <sCliSkipIntro>
  --level <N>
      <sCliLevel1>
```

### `UGLI_2.pp` — CLI parsing and `NewGame:` label

```pascal
{ after --help check, before InitStderrSink }
for I := 1 to ParamCount - 1 do
  begin
    if ParamStr(I) = '--skip-intro' then
      SkipIntro := true;
    if ParamStr(I) = '--level' then
      begin
        StartAtLevel := StrToIntDef(ParamStr(I + 1), 1);
        if StartAtLevel < 1 then StartAtLevel := 1;
        if StartAtLevel > 9 then StartAtLevel := 9;
        SkipIntro := true;
      end;
  end;

{ NewGame: }
NewGame:
  Level := StartAtLevel;   { was: Level := 1 }
```

### `pyproject.toml` — `poe run-original`

Add `"$@"` after the binary name in both branches:

```toml
${TERMINAL} original/UGLI_2 "$@"
kitty ... original/UGLI_2 "$@"
```

Help text updated to mention `-- <options>` pass-through.

### `translations/de.po`

| English | German |
|---|---|
| `Skip the intro and item-descriptions screen.` | `Intro und Gegenstandsliste überspringen.` |
| `Start at level N (1–9; default: 1). Implies --skip-intro.` | `Spiel bei Level N starten (1–9; Standard: 1). Impliziert --skip-intro.` |

### `UGLI_2_Test.pp` — extended `TCliHelpTests`

Add:
- `TestHelpText_ContainsSkipIntro`: `Pos('--skip-intro', CLIHelpText) > 0`
- `TestHelpText_ContainsLevel`: `Pos('--level', CLIHelpText) > 0`

---

## Done when

- [ ] `poe build-original` exits 0
- [ ] `poe test-original` exits 0, 130 tests pass
- [ ] `poe run-original -- --level 5` opens at level 5 with no intro (confirmed by user)
- [ ] `poe run-original -- --skip-intro` skips intro, starts at level 1 (confirmed by user)
- [ ] `poe run-original -- --help` prints the updated help with both new options (confirmed by user)

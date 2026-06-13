# UGLI 2 Pascal House Style

Rules applied by `reformat.py` to `UGLI_2.PAS` and `DANISOFT.PAS`.

## Status

| Rule | Status |
|---|---|
| Keywords lowercase | ✓ |
| Built-in types PascalCase | ✓ |
| RTL routines PascalCase | ✓ |
| User identifiers PascalCase | ✓ |
| Two-letter abbreviations ALL CAPS | ✓ |
| `TTY` ALL CAPS (standalone and in compounds) | ✓ |
| Compound identifiers: abbreviation suffix uppercased | ✓ |
| Brand/product names ALL CAPS | ✓ |
| 2-space indentation | ✓ |
| `begin`/`end` on own lines | ✓ |
| `begin` after `then`/`do`/`else` indented one extra level | ✓ |
| Short single-statement `if` on one line | ✓ |
| Goto labels at column 0 | ✓ |
| End-comments: identifiers cased, no inner spaces | ✓ |
| One space after comma | ✓ |
| Wrapped argument list continuation: 2 spaces (not paren-aligned) | ✓ |
| No blank line after `begin` or goto label | ✓ |
| No blank line before `end`/`until` | ✓ |
| Blank line between top-level procedure/function definitions | ✓ |
| Compiles with `fpc -Mtp` | ✓ |

---

## Casing rules

### Keywords → lowercase

All reserved words: `program`, `uses`, `label`, `const`, `var`, `begin`, `end`,
`if`, `then`, `else`, `for`, `to`, `do`, `while`, `procedure`, `function`,
`repeat`, `until`, `case`, `of`, `not`, `and`, `or`, `div`, `mod`, `type`,
`record`, `array`, `true`, `false`, `unit`, `interface`, `implementation`,
`with`, `downto`, `in`, `nil`, `set`, `file`, `goto`, `break`, `exit`.

### Built-in types → PascalCase

Treated as identifiers, not keywords: `String`, `Integer`, `LongInt`, `Boolean`,
`Char`, `Byte`, `Word`, `Real`, `Text`, `ShortInt`, `LongWord`, `Cardinal`.

### RTL routines → PascalCase

`WriteLn`, `Write`, `ReadLn`, `Read`, `ReadKey`, `GotoXY`, `ClrScr`, `ClrEol`,
`TextColor`, `TextBackground`, `TextAttr`, `KeyPressed`, `GetKey`, `Window`,
`Delay`, `Assign`, `ReWrite`, `Reset`, `Flush`, `Close`, `Append`, `Eof`,
`EoLn`, `Inc`, `Dec`, `Chr`, `Ord`, `Length`, `Str`, `Val`, `Copy`, `Pos`,
`Concat`, `Delete`, `Insert`, `UpCase`, `Abs`, `Sqr`, `Sqrt`, `Random`,
`Randomize`, `Halt`, `IOResult`, `ParamCount`, `ParamStr`, `Hi`, `Lo`.

CRT color constants: `Black`, `Blue`, `Green`, `Cyan`, `Red`, `Magenta`, `Brown`,
`LightGray`, `DarkGray`, `LightBlue`, `LightGreen`, `LightCyan`, `LightRed`,
`LightMagenta`, `Yellow`, `White`, `Blink`.

Sound routines: `Ton`, `Sound`, `NoSound`, `SoundBrumm`, `SoundPickup`,
`SoundCaught`, `SoundGameOver`, `SoundGewonnen`.

Splash screen: `Erkennung`, `Erkennung2`, `UTF8Cols`, `Zentriert`, `WLn`.

### User-defined identifiers → English, PascalCase

All user-defined identifiers must be English.
First letter uppercase, rest unchanged: `BlocksRemaining`, `Score`, `EscState`,
`EnemyTick`, `Shield`, `Level`, `Lives`, `DrawFrame`, `HighScoreEntry`, etc.

**Exception — two-letter abbreviations → ALL CAPS:**
`VX`, `VY`, `SX`, `SY`, `DX`, `DY`, `XX`, `YY`, `TI`, `OP`, `IZ`, `TTY`.

**Exception — x/y suffix form:** `LocX`, `LocY`.

**Exception — brand/product names → ALL CAPS:**
`DANISOFT`, `UGLI`, `UGLI_2`, `UGLI2`.

**Compound identifiers:** when a user-defined identifier ends with a known
coordinate abbreviation or `TTY`, that suffix is uppercased even inside a
longer name. Requires the prefix to be ≥ 2 characters.

| Abbreviations used as suffixes | Example |
|---|---|
| `XX`, `YY` (coordinate pairs) | `Oldxx` → `OldXX`, `Oldyy` → `OldYY` |
| `X`, `Y` (single-letter coordinate) | `Tryx` → `TryX`, `Oldx` → `OldX`, `Oldy` → `OldY` |
| `TTY` | `SomeTty` → `SomeTTY` |

Two-letter direction abbreviations (`VX`, `VY`, `SX`, `SY`, `DX`, `DY`) are
NOT applied as compound suffixes because they appear as false matches inside
unrelated words (e.g. `Oldy` ends in `dy`).

### Unit names → specific casing

`CThreads`, `Crt`, `Dos`, `UOSSound`.

### Game procedures with non-obvious casing

`WriteXY`, `DrawHLine`, `DrawVLine`, `MyCursorOn`, `MyCursorOff`,
`WriteLevel`, `ReStone`, `PunkteZaehlen`, `ZahlenSetzung`, `ZufalsPos`,
`SteineSetzen`, `SteineNehmen`, `PausenZeigen`, `LevelNeu`.

---

## Indentation

- 2 spaces per level.
- `begin` and `end` are always on their own lines.
- After `then`, `do`, or `else` (alone on a line): the body is indented one
  extra level. If `begin` follows, it sits at `depth + 1`; the body inside at
  `depth + 2`.
- Short single-statement `if` stays on one line — no forced `begin`/`end`:
  ```pascal
  if Zahl = 2 then Punkte := Punkte + 100;
  ```
- Chained single-statement control lines (`then`/`do` without `begin`) accumulate
  indentation: each ctrl line adds one extra level so the terminal statement ends up
  correctly nested:
  ```pascal
  for J := 9 to 11 do
    for I := 2 to 79 do
      Sper[I, J] := false;
  ```
- Numeric goto labels (`100:`, `300:`, etc.) are always emitted at column 0.
  Numeric case-arm labels (`1:`, `2:`, etc.) are indented normally because the
  reformatter tracks which blocks are `case...of` blocks.
- `var`/`const`/`type`/`label` section: the keyword is at current depth;
  declarations on subsequent lines are at `depth + 1`.
- **Wrapped argument lists:** when a `(` is not closed on its opening line, all
  continuation lines are indented `depth + 1` (2 more spaces than the opening
  line) — not aligned to the `(`.

  ```pascal
  procedure Erkennung(S1, S2, S3, S4, S5, S6, S7, S8: String; Ver: String;
    Nr, User, Copyjahr: String);
  ```

---

## End-comments

`{...}` comments that appear on a line beginning with `end` are reformatted:
identifiers inside are cased according to the same rules, and leading/trailing
spaces are stripped (no space after `{`, no space before `}`).

```pascal
end; {case}           { keyword → lowercase }
end; {Rahmen}         { identifier → PascalCase }
end; {UGLI2}          { brand name → ALL CAPS }
end; {for J}          { was {FOR J} }
end; {if Zahl = 10}   { was {if zahl = 10} }
```

---

## Blank lines

- No blank line immediately after `begin`.
- No blank line immediately before `end` or `until`.
- No blank line after a goto label (e.g. `100:`).
- No blank line before the `program` declaration.
- A blank line is inserted between any two top-level procedure/function
  definitions if one is not already present (detected by `end;` or `end.` at
  column 0 followed directly by `procedure`/`function`).

---

## Spacing

- One space after every comma (parameter lists, array indices, `uses` clauses).
- No space before: `)`, `]`, `,`, `;`, `:`, `.`, `..`, `[`.
- No space after: `(`, `[`, `@`, `^`, `..`.
- No space between an identifier and its opening `(` in a call: `WriteLn(...)`.
- No space before `[` in subscripts: `Sper[I, J]`.

---

## Scope

Rules apply to `UGLI_2.PAS` and `DANISOFT.PAS`. The UOS source files
(`uos.pas`, `uos_flat.pas`, `uos_portaudio.pas`) are fetched at build time
from an external repository and are not reformatted.

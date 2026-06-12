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
| Brand/product names ALL CAPS | ✓ |
| 2-space indentation | ✓ |
| `begin`/`end` on own lines | ✓ |
| `begin` after `then`/`do`/`else` indented one extra level | ✓ |
| Short single-statement `if` on one line | ✓ |
| Goto labels at column 0 | ✓ |
| One space after comma | ✓ |
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

### User-defined identifiers → PascalCase

First letter uppercase, rest unchanged: `Steine`, `Punkte`, `EscState`,
`Timeslot`, `Schutz`, `Level`, `Leben`, `Rahmen`, `Abfrage`, etc.

**Exception — two-letter abbreviations → ALL CAPS:**
`VX`, `VY`, `SX`, `SY`, `DX`, `DY`, `XX`, `YY`, `TI`, `OP`, `IZ`.

**Exception — x/y suffix form:** `LocX`, `LocY`.

**Exception — brand/product names → ALL CAPS:**
`DANISOFT`, `UGLI`, `UGLI_2`, `UGLI2`.

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
- Numeric goto labels (`100:`, `300:`, etc.) are always emitted at column 0.
  Numeric case-arm labels (`1:`, `2:`, etc.) are indented normally because the
  reformatter tracks which blocks are `case...of` blocks.
- `var`/`const`/`type`/`label` section: the keyword is at current depth;
  declarations on subsequent lines are at `depth + 1`.

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

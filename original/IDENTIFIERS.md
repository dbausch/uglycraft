# UGLI 2 — Identifier Inventory

Rename candidates for the English-identifier refactor.
Column **"English proposal"** is the suggested new name; edit freely before applying.
*(keep)* means the current name is already acceptable English.

---

## Global constants (`UGLI_2.PAS`)

| Identifier | Description | English proposal |
|---|---|---|
| `User` | License/authorship label string | *(keep)* |
| `Vers` | Version number string | `Version` |
| `Nr` | Release number string (German *Nummer*) | `Release` |
| `MaXX` | Play-field width in columns (80); cased MaXX due to XX-suffix rule | `FieldW` |
| `MaxY` | Play-field height in rows (20) | `FieldH` |
| `CurR` | Key code for cursor right | `KeyRight` |
| `CurL` | Key code for cursor left | `KeyLeft` |
| `CurO` | Key code for cursor up (*Oben* = up) | `KeyUp` |
| `CurU` | Key code for cursor down (*Unten* = down) | `KeyDown` |
| `Unbr` | Key code for pause action, ASCII 'p' (*Unterbrechung* = interruption) | `KeyPause` |
| `Lans` | Key code for slow-down (End key) (*Langsamer* = slower) | `KeySlower` |
| `Kauf` | Key code for shop menu, ASCII Space (*Kaufen* = buy) | `KeyBuy` |
| `Sped` | Key code for speed-up (Home key) | `KeyFaster` |
| `Name` | High-score filename constant (`UGLI.HSC`) | `HscName` |
| `Copy` | Full license/copyright notice string | `License` |

---

## Global variables (`UGLI_2.PAS`)

| Identifier | Description | English proposal |
|---|---|---|
| `Steine` | Block-placement budget (*Steine* = stones) | `Blocks` |
| `Langs` | Movement delay in ms; higher = slower (*Langsam* = slow) | `MoveDelay` |
| `OP` | Key-ordinal used as a termination flag in win screen | `Code` |
| `Pausen` | Remaining pause tokens (*Pausen* = pauses) | `PauseLeft` |
| `Timeslot` | Enemy-move tick counter (cycles 0–1) | `EnemyTick` |
| `TI` | Ordinal of the current key press (*Taste I* = key integer) | `KeyCode` |
| `I`, `J` | General-purpose loop indices, global reuse | *(keep)* |
| `Zahl` | Current treasure item index 1–10 (*Zahl* = number) | `ItemNo` |
| `Level` | Current level number (1–9) | *(keep)* |
| `Leben` | Lives remaining (*Leben* = lives/life) | `Lives` |
| `VX`, `VY` | Saved player position for temporary displacement (*vorig* = previous) | `SaveX`, `SaveY` |
| `SX`, `SY` | Position of last-placed stone; redrawn after player moves (*Stein* = stone) | `StoneX`, `StoneY` |
| `LocX`, `LocY` | Current treasure X/Y location | *(keep)* |
| `DX`, `DY` | Enemy–player horizontal / vertical delta used in AI | *(keep)* |
| `X`, `Y` | Player position (column, row) | *(keep)* |
| `XX`, `YY` | Enemy position (column, row) | `EX`, `EY` |
| `EscState` | Escape-sequence parser state: 0 = normal, 1 = saw 'F', 2 = saw '[' | *(keep)* |
| `Punkte` | Accumulated score (*Punkte* = points) | `Score` |
| `Sper` | Collision map; `true` = cell is blocked (*Sperrung* = blockage) | `Wall` |
| `T` | Current key character (*Taste* = key) | `Key` |
| `F` | File handle for the high-score file | *(keep; conventional)* |
| `TTY` | File handle for raw terminal escape-sequence output | *(keep)* |
| `IZ` | Player first/given name entered at game over | `FirstName` |
| `A` | Player last/family name entered at game over | `LastName` |
| `S` | Scratch string buffer (used with `Str()`, HUD writes, etc.) | `Buf` |
| `Zeile` | One line read from the high-score file (*Zeile* = line) | `Line` |
| `Schutz` | Shield active flag (*Schutz* = protection) | `Shield` |

---

## Procedures and functions (`UGLI_2.PAS`)

| Identifier | Description | English proposal |
|---|---|---|
| `MyCursorOn` | Show terminal cursor via escape sequence | *(keep)* |
| `MyCursorOff` | Hide terminal cursor via escape sequence | *(keep)* |
| `WriteXY` | Write UTF-8 string at exact screen col/row | *(keep)* |
| `WriteLevel` | Redraw "LEVEL N" label in the HUD | *(keep)* |
| `DrawHLine` | Draw a horizontal run of a repeated character | *(keep)* |
| `ReStone` | Redraw all wall tiles from the collision map (*Re-Stein* = re-stone) | `RedrawWalls` |
| `Abfrage` | High-score name-entry and display sequence (*Abfrage* = inquiry) | `HiScoreEntry` |
| `Cls` | Thin wrapper around `ClrScr` | *(keep or inline)* |
| `Verwirrung` | Animated splash/intro screen (*Verwirrung* = confusion) | `SplashScreen` |
| `PunkteZaehlen` | Award points for the just-collected treasure (*Punkte zählen* = count points) | `AwardPoints` |
| `InitL1`–`InitL9` | Set up collision map and player start for level N | `InitLevel1`–`InitLevel9` |
| `InitL` | Dispatch to the correct `InitLevelN` procedure | `InitLevel` |
| `Wertsachen` | Display treasure list + game instructions (*Wertsachen* = valuables) | `ShowInstructions` |
| `GetKey` | Read one key with Linux escape-sequence translation | *(keep)* |
| `Hilfe` | In-game help overlay (*Hilfe* = help) | `ShowHelp` |
| `LevelNeu` | Level-transition banner + wait-for-key (*Level neu* = new level) | `LevelTransition` |
| `Brumm` | Play the wall-bump sound (*Brumm* = buzz/hum) | `BumpSound` |
| `Unten` | Move player down one row (*unten* = below) | `MoveDown` |
| `Links` | Move player left one column (*links* = left) | `MoveLeft` |
| `Rechts` | Move player right one column (*rechts* = right) | `MoveRight` |
| `Oben` | Move player up one row (*oben* = above) | `MoveUp` |
| `Rahmen` | Clear screen, draw border frame, initialise level (*Rahmen* = frame) | `DrawBorder` |
| `UGLI2` | Enemy AI: one greedy-chase move step | `EnemyMove` |
| `Untbr` | Consume a pause token and wait 5 s (*Unterbrechung* = interruption) | `DoPause` |
| `Geschichte` | Game-backstory text screen (*Geschichte* = story) | `ShowStory` |
| `Langsam` | Slow down: increment `MoveDelay` (*langsam* = slow) | `SlowDown` |
| `Schnell` | Speed up: decrement `MoveDelay` (*schnell* = fast) | `SpeedUp` |
| `GameOver` | Draw game-over overlay and play sound | *(keep)* |
| `PausenZeigen` | Show remaining pause count (*Pausen zeigen* = show pauses) | `ShowPauses` |
| `Gewonnen` | Win-screen animation, then high-score entry (*gewonnen* = won) | `WinScreen` |
| `Def` | Initialise all game-state variables to starting values | `Init` |
| `Fressen` | Handle player caught: deduct life, reset position (*fressen* = devour) | `PlayerCaught` |
| `ZahlenSetzung` | Draw current treasure symbol at its location (*Zahlen-Setzung* = number placement) | `DrawTreasure` |
| `ZufalsPos` | Pick a random unblocked cell for next treasure (*Zufalls-Position*) | `RandomPos` |
| `GeheimTricks` | Show secret cheat-key hints (*Geheim-Tricks* = secret tricks) | `CheatScreen` |
| `Kaufen` | Open shop menu (*kaufen* = buy) | `ShopMenu` |
| `Taste` | Main per-tick input dispatcher (*Taste* = key) | `HandleInput` |
| `SteineSetzen` | Place a wall block at player's current cell (*Steine setzen* = place stones) | `PlaceBlock` |
| `SteineNehmen` | Remove all player-placed blocks (*Steine nehmen* = take/remove stones) | `RemoveBlocks` |

---

## Selected parameters and local variables

| Identifier | Scope | Description | English proposal |
|---|---|---|---|
| `Col`, `Row` | `WriteXY` params | Screen position target | *(keep)* |
| `S` | `WriteXY` param | String to render | *(keep; conventional)* |
| `C` | `WriteXY` local | Running screen column during render | *(keep)* |
| `N` | `WriteXY` local | Byte width of current UTF-8 character | *(keep)* |
| `Ch` | `WriteXY` / `DrawHLine` | Current character (multi-byte chunk / line fill) | *(keep)* |
| `C` | `ReStone` local | Character to display: `'█'` or `' '` | `Ch` |
| `Raw` | `GetKey` local | Raw character before escape translation | *(keep)* |
| `OldX`, `OldY` | movement procs | Player position before the move | *(keep)* |
| `OldXX`, `OldYY` | `UGLI2` | Enemy position before this move | `OldEX`, `OldEY` |
| `TryX` | `UGLI2` | Whether to attempt horizontal axis first | `TryHoriz` |
| `Tryn` | `UGLI2` | Attempt counter 1–2 for axis fallback | `Attempt` |
| `L` | `InitL` param | Level number to initialize | *(keep)* |

---

## `DANISOFT.PAS`

| Identifier | Description | English proposal |
|---|---|---|
| `UTF8Cols` | Count terminal-column width of a UTF-8 string | *(keep)* |
| `Zentriert` | Return string left-padded to be centred in 80 columns (*zentriert* = centred) | `Center` |
| `Erkennung` | Animated colour/sound intro splash (*Erkennung* = recognition/startup) | `Intro` |
| `WLn` | Write one splash line with trailing TTY erase-to-EOL | *(keep)* |
| `S1`–`S8` | Eight lines of the ASCII-art logo | `Logo1`–`Logo8` |
| `Ver` | Version string param | `Version` |
| `Nr` | Release number string param | `Release` |
| `Copyjahr` | Copyright year string (*Copyjahr* = copy-year) | `CopyYear` |
| `Laenge` | Display-column width of the string to centre (*Länge* = length) | `Width` |
| `Blanks` | Count of leading spaces needed | *(keep)* |
| `BlankZone` | The leading-spaces string | `Padding` |
| `B` | Byte value during UTF-8 width scan | *(keep)* |
| `Count` | Running column count in `UTF8Cols` | *(keep)* |

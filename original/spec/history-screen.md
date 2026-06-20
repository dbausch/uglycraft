# Replace in-game story with real history

## Status

- [x] `translations/history_en.txt` — English history text
- [x] `translations/history_de.txt` — German history text
- [x] `sStoryTitle` → `'The History of UGLI'`; `sStoryText` removed
- [x] `sKeys2` and `sHelpF2` updated to say "History" instead of "Story"
- [x] `sHistoryMissing` resourcestring for fallback when file not found
- [x] `LoadHistoryText` loads text file by locale, falls back gracefully
- [x] `ShowStory` renders multi-paragraph text (split on blank lines)
- [x] `de.po` / `de.mo` updated
- [x] UGLYCRAFT: `[S] History` on title screen, loads from file, returns to title
- [x] Packaging includes `history_*.txt`
- [x] Game compiles (`poe build-original` exits 0)
- [x] All tests pass (`poe test-original` exits 0)
- [x] Manual check: F2 shows history, fits on 80×25 screen
- [x] Manual check: German text loads with `LANG=de_DE.UTF-8`
- [x] Manual check: missing file shows placeholder, no crash
- [x] Manual check: UGLYCRAFT title screen shows [S], history displays

## Approved English text

In 1993, a kid wanted more games for his old PC. His father said: make
your own. So he did — and UGLI was born. A smiley face chasing treasures
on a text-mode screen, with the PC speaker as its only voice.

Other kids wanted it too. Floppy disks changed hands at school and around
town. He paid for an ad in the local sports club magazine from the pocket
money he earned selling copies. By 1996, version two brought more levels
and the ability to place walls.

Thirty years later, the game is back in two flavors — a faithful port and
UGLYCRAFT, a full remake. Both are free and open source (GPLv3), available
on itch.io and GitHub.

## Design

### Text file storage

Body text lives in `translations/history_<lang>.txt` alongside the `.mo`
files.  Paragraphs are separated by blank lines in the file.

### `LoadHistoryText` (Pascal)

- Derives `ExeDir` (same pattern as `LoadTranslation`)
- Gets two-letter locale code via `GetLanguageIDs`
- Tries `ExeDir + 'translations/history_' + Lang + '.txt'`
- Falls back to `ExeDir + 'translations/history_en.txt'`
- If neither exists, returns `sHistoryMissing` resourcestring
- Uses `{$I-}` / `IOResult` — never crashes on missing file

### `ShowStory` rendering (Pascal)

Splits loaded text on blank lines into paragraphs.  Calls `DrawParagraph`
for each one, advancing the row cursor by the returned line count plus one
(for the blank line between paragraphs).

### UGLYCRAFT (Python)

- Title footer: `[H] High scores   [S] History   [Q] Quit`
- `S` key → STORY state
- `_render_story` loads `history_en.txt` from base dir, word-wraps and
  renders.  Falls back to `"History text not found."` on `OSError`.
- Any key on STORY → back to TITLE (not into the game)

## Done when

- [x] History text files exist and are loaded at runtime — `6e56cbf`
- [x] F2 in original shows multi-paragraph justified history text — confirmed by user
- [x] German translation loads when locale is German — confirmed by user
- [x] Missing file shows translated placeholder, no crash — confirmed by user
- [x] UGLYCRAFT title screen has `[S]` option leading to history — `efbc2c1`
- [x] History screen in UGLYCRAFT returns to title on any key — confirmed by user
- [x] Packaging includes `history_*.txt` for both arch and itch — `6e56cbf`

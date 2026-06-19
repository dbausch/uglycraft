# Replace in-game story with real history

## Status

- [ ] `translations/history_en.txt` — English history text
- [ ] `translations/history_de.txt` — German history text
- [ ] `sStoryTitle` → `'The History of UGLI'`; `sStoryText` removed
- [ ] `sKeys2` and `sHelpF2` updated to say "History" instead of "Story"
- [ ] `sHistoryMissing` resourcestring for fallback when file not found
- [ ] `LoadHistoryText` loads text file by locale, falls back gracefully
- [ ] `ShowStory` renders multi-paragraph text (split on blank lines)
- [ ] `de.po` / `de.mo` updated
- [ ] UGLYCRAFT: `[S] History` on title screen, loads from file, returns to title
- [ ] Packaging includes `history_*.txt`
- [ ] Game compiles (`poe build-original` exits 0)
- [ ] All tests pass (`poe test-original` exits 0)
- [ ] Manual check: F2 shows history, fits on 80×25 screen
- [ ] Manual check: German text loads with `LANG=de_DE.UTF-8`
- [ ] Manual check: missing file shows placeholder, no crash
- [ ] Manual check: UGLYCRAFT title screen shows [S], history displays

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

- [ ] History text files exist and are loaded at runtime
- [ ] F2 in original shows multi-paragraph justified history text
- [ ] German translation loads when locale is German
- [ ] Missing file shows translated placeholder, no crash
- [ ] UGLYCRAFT title screen has `[S]` option leading to history
- [ ] History screen in UGLYCRAFT returns to title on any key
- [ ] Packaging includes `history_*.txt` for both arch and itch

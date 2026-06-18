# Remove spurious WaitKey from HighScoreEntry

## Status

- [x] Spurious WaitKey removed from HighScoreEntry

## Problem

`HighScoreEntry` contained a `WaitKey` call immediately after writing the
player's score to `UGLI.HSC` and before clearing the screen to display the
high-score table. This forced the player to press an extra key for no
visible reason: the screen at that point showed only the name-entry prompt
(cooked-mode `ReadLn` had just returned), so waiting there was confusing
and unnecessary. The procedure already calls `WaitKey` at the end, after
displaying the full score table, which is the correct place to pause.

## Fix

Remove the one `WaitKey;` statement that appeared between the file-write
block and the `Write(TTY, #27'[2J'#27'[H');` screen-clear.

## Done when

- [x] `HighScoreEntry` requires exactly one key press — at the end, after the
  high-score table is displayed — not two. (Commit: 0d3772e)

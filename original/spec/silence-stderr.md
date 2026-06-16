# Silence stderr to prevent library noise from corrupting the display

## Status

- [ ] `fpDup2('/dev/null', 2)` added at startup in `UGLI_2.pp`
- [ ] `poe build-original` passes
- [ ] `poe test-original` passes

---

## Root cause

The game takes exclusive control of the terminal: all output goes through
`RawTTYFd` / `WBFlush` into the off-screen buffer and is positioned precisely
with `ESC[r;cH` cursor-position sequences.

ALSA (via PortAudio and UOS) occasionally writes buffer-underrun warnings
directly to stderr (fd 2).  Since the game does not redirect stderr, these
strings land as raw characters at the current cursor position in the terminal,
corrupting whatever cell the terminal happens to be pointing at.  The string is
printed in the terminal's default foreground colour on the game's current
background colour — typically appearing as black text on a black background, so
the result looks like a patch of black cells rather than readable text.

## What changes

### `UGLI_2.pp` — main `begin` block

Redirect stderr to `/dev/null` before any sound or TTY initialisation.  The
game never uses stderr intentionally; any fd-2 output can only be unwanted
library noise.

```pascal
{ NEW local var }
var
  Tio   : Termios;
  DevNull: cint;

{ NEW — first lines of the begin block }
  DevNull := fpOpen('/dev/null', O_WRONLY);
  if DevNull >= 0 then
    begin
      fpDup2(DevNull, 2);
      fpClose(DevNull);
    end;
```

No other file is affected.

## Done when

- [ ] `poe build-original` exits 0
- [ ] `poe test-original` exits 0, all tests pass
- [ ] ALSA underrun messages no longer appear in the game window during play
      (confirmed by user after playing through several levels with sound)

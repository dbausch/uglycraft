# UGLYCRAFT

## A game thirty years in the making

In 1993, a primary school kid named Daniel sat down with Turbo Pascal on MS-DOS and wrote
a game. He called it **UGLI**. Then he copied it onto floppy disks and sold it to his
classmates.

He kept working on it. By 1996 it had grown into a proper second version — new levels, wall
placement mechanics, and features that never made it into the released build. That source
code still exists. It is preserved in this repository, three Pascal files, exactly as he
left it.

That kid grew up. The source files survived. And now, over thirty years later, UGLI is
back — rebuilt from scratch in Python, with ten levels, procedural music, and an ogre boss
that will hunt you to the ends of the map.

---

## What is it?

UGLYCRAFT is a top-down maze-chase game. You are the smiley face. The ogres want to catch
you. Between you and victory stand nine treasures per level, an increasingly complex maze,
and a growing sense of dread as the music gets faster and darker with each floor.

Collect every treasure in order. Reach the Crown on level 10. Don't get caught.

---

## Features

- **10 levels** — from an open field to a spiral fortress guarded by a boss
- **Three escalating ogre types** — friendly green, snarling orange, war-painted purple
- **A boss on level 10** — crowned, armoured, and pathfinding directly toward you
- **Interactive wall placement** — mine walls and rebuild them to cut off pursuers
- **Instant shield purchase** — buy ten seconds of safety at any moment for 250 points
- **Original music and sound** — one track per level, getting faster and darker as you descend
- **Two difficulty modes** — Easy (one enemy, greedy AI) and Hard (multiple enemies, BFS)
- **High-score table** — your best runs remembered between sessions

---

## The original (1993–1996)

UGLI began in 1993 as a DOS text-mode game — 80×25 characters, enemies as the letter O,
player as ASCII smiley face 1, sound from the PC speaker. By 1996 it had evolved into a
second version with richer mechanics including the wall placement system that carries
through to UGLYCRAFT today.

The original 1996 Pascal source is preserved in this repository, ported to run on modern
Linux with Free Pascal, and released under the GPLv3. It was, by any objective measure,
ugly. That was rather the point.

---

## Controls

| Key | Action |
|-----|--------|
| Arrow keys | Move; bump a wall 3× to mine it |
| Space | Place wall (costs 1 credit) |
| Enter | Buy shield (250 pts, 10 s) |
| P | Pause |
| F11 | Fullscreen |

---

Source code (including the original 1996 Pascal source) is available on [GitHub](https://github.com/dbausch/uglycraft).

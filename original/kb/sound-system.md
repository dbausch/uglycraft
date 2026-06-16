# Sound system — UOS + PortAudio

## Architecture

`UOSSound.pp` wraps the UOS audio library (Pascal bindings for PortAudio).
Sound is produced by synthesising a continuous square wave at a controlled
frequency and volume.  `Ton(Hz, Ms)` plays a note for a fixed duration;
`Sound(Hz)` / `NoSound` control an ongoing tone.

Initialisation is **lazy**: `UOSSound.Init` is called from `Sound()` on the
first invocation, not at program start.  `FReady := True` is set at the
beginning of `Init` so failed attempts are never retried.  `FPlaying` is set
only after `uos_PlayNoFree` succeeds and means audio is actually running.

---

## UOS sources: committed vs. fetched

The original port committed the UOS source files directly to the repository
(`original/uos/`).  Commit `b31f8fe` ("Fetch UOS source at build time instead
of committing it") removed them and switched to `curl`-fetching from GitHub on
first build.

**The two source generations behave differently at `Pa_Initialize()` time:**

| Source generation | ALSA probe messages on `Init` |
|---|---|
| Original committed sources (`2fe4698`) | Many messages — one per absent/misconfigured backend |
| Currently fetched sources | Silent — probe succeeds cleanly |

This was confirmed by building `ProbeSound` variants against each source
generation (2026-06-16) and running them in the same terminal session.  The
difference is entirely in how the two UOS versions call into PortAudio, not in
PipeWire, ALSA config, or the `SuppressStderr` wrapper.

---

## History of stderr suppression

### Phase 1 — no suppression (`2fe4698`)

The initial port had no stderr silencing.  PortAudio's `Pa_Initialize()` wrote
backend-probe failure messages (ALSA/JACK/OSS) directly to fd 2, which the
game's raw-terminal rendering did not expect.  The messages appeared as garbled
text at the current cursor position.

### Phase 2 — `SuppressStderr` in `UOSSound.Init` (`4fa6961`)

A `SuppressStderr`/`RestoreStderr` pair was wrapped around the PortAudio probe
in `UOSSound.Init`.  The probe was silenced, but `RestoreStderr` restored fd 2
to the terminal after init, so ALSA buffer-underrun messages during playback
still reached the terminal and caused display corruption.

### Phase 3 — permanent fd 2 redirect at startup (`8503f4e`)

The game's main block redirected fd 2 to `/dev/null` before any TTY or sound
setup, silencing both probe and playback messages permanently.  The
`SuppressStderr`/`RestoreStderr` in `UOSSound` became a no-op (saved
`/dev/null`, redirected to `/dev/null`, restored `/dev/null`).

### Phase 4 — unified `InitStderrSink` + `--stderr-log` (`da21e2c`)

The two suppressions were merged into `InitStderrSink(LogFile)` in
`UGLI_2_Core.inc`.  The `--stderr-log <file>` CLI option allowed routing
fd 2 to a file instead of `/dev/null` for diagnostics.  `SuppressStderr`/
`RestoreStderr` were removed from `UOSSound`.

### Phase 5 — structured log + `--log` / `-l` (`278155b`)

`InitStderrSink` renamed to `OpenLog`; `--stderr-log` renamed to `--log` with
short form `-l`.  `OpenLog` keeps the file descriptor open (`LogFd`) so
`Log()` can write structured timestamped entries alongside any fd 2 noise.
`UOSSound.Init` writes its own diagnostic line to fd 2 so it appears in the
log when `--log` is active.

---

## What to expect from `--log`

### With fetched UOS sources (current build)

The log will contain structured entries from the game (started, flags, sound
backend, gameplay events, exit) but **no ALSA probe messages** — the fetched
UOS version initialises PortAudio without generating any fd 2 output on probe.

`UOSSound.Init` explicitly writes one of:
- `UOSSound: PortAudio ready (libportaudio.so.2)` — normal case
- `UOSSound: uos_CreatePlayer failed, sound disabled` — device init failure
- `UOSSound: no PortAudio library found, sound disabled` — no libportaudio

### With original committed UOS sources (`2fe4698`)

Many ALSA probe messages appear on `Pa_Initialize()`.  Example:

```
ALSA lib pcm.c:2722: Unknown PCM cards.pcm.rear
ALSA lib pcm.c:2722: Unknown PCM cards.pcm.center_lfe
connect(2) call to /dev/shm/jack-1000/default/jack_0 failed (err=No such file or directory)
ALSA lib pcm_oss.c:404: Cannot open device /dev/dsp
...
```

These were the "many messages on each run" visible before suppression was added.

### Buffer-underrun messages

ALSA writes `snd_pcm_recover` / underrun messages to fd 2 during playback on
some hardware.  These are unrelated to the probe and appear regardless of UOS
source version.  They land in the log file when `--log` is active.

---

## Sound effects reference

| Procedure | Hz / pattern | Trigger |
|---|---|---|
| `SoundBump` | 40 Hz, 5 ms | Player walks into a wall |
| `SoundPickup` | 250 Hz, 50 ms | Treasure collected |
| `SoundCaught` | 80 Hz, 200 ms | Player caught by enemy |
| `SoundGameOver` | descending sweep 200→100 Hz + 600→0 sweep | Lives = 0 |
| `SoundWon` | 100/200/300/400 Hz, 500 ms each | All items collected |
| `Ton` (intro) | I × 150 Hz, 300 ms each, I = 0..7 | During animated intro |

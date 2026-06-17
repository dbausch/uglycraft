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

**The two source generations were initially thought to behave differently:**

| Source generation | ALSA probe messages on `Init` |
|---|---|
| Original committed sources (`2fe4698`) | Many messages — one per absent/misconfigured backend |
| Currently fetched sources | Sometimes silent, sometimes noisy |

Testing on 2026-06-16 with `ProbeSound` variants suggested the fetched sources
were always silent, but a `--log` capture on 2026-06-17 showed the full set of
probe messages appearing with the same fetched sources.  The root cause is
uncertain — it may involve PipeWire/ALSA session state or timing rather than
the UOS source version alone.

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

### ALSA probe messages

Earlier testing (2026-06-16) concluded that the currently fetched UOS sources
did **not** produce ALSA probe messages, unlike the original committed sources
(`2fe4698`).  However, a `--log` capture on 2026-06-17 showed the full set of
probe messages appearing again with the same fetched sources (dated 2026-06-09).
The cause of the discrepancy is uncertain — it may depend on PipeWire/ALSA
state, session timing, or other environmental factors rather than the UOS
source version alone.

In practice, assume that ALSA/JACK/OSS probe messages **may or may not**
appear on any given run.  The `--log` redirect captures them regardless.

`UOSSound.Init` explicitly writes one of:
- `UOSSound: PortAudio ready (libportaudio.so.2)` — normal case
- `UOSSound: uos_CreatePlayer failed, sound disabled` — device init failure
- `UOSSound: no PortAudio library found, sound disabled` — no libportaudio

### Buffer-underrun messages

ALSA writes `snd_pcm_recover` / underrun messages to fd 2 during playback on
some hardware.  These are unrelated to the probe and appear regardless of UOS
source version.  They land in the log file when `--log` is active.

---

## Sample format mismatch fix (`6ebb27b`)

Prior to this fix, the game's sound had audible distortion: a chopping
artefact and frequency sweep that made it sound nothing like the clean square
waves of the original DOS version.

**Root cause:** `uos_AddFromSynth` defaults to **Float32** sample format,
while `uos_AddIntoDevOut()` (called with no arguments) defaults to **Int16**.
UOS silently converts between the two, and that conversion introduced the
artefacts.

**Fix:** `UOSSound.Init` now passes explicit matching parameters to both
calls — stereo, Float32, 44100 Hz, 1024 frames on the synth input; stereo,
Float32, 44100 Hz on the device output.

**Diagnosis method:** a minimal `ProbeSound.pp` test program that played a
single 440 Hz tone for 3 seconds.  With mismatched formats it reproduced the
distortion; with matched Float32 on both sides it produced a clean square wave.

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

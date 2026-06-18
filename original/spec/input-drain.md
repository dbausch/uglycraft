# Input drain and direction queue

## Status

- [ ] Rename `HasTTYByte` → `KeyPressed`
- [ ] `HandleInput` drains all pending keys per tick (`while KeyPressed do`)
- [ ] Direction keys enqueue into a ring buffer (deduplicated against tail)
- [ ] `MovePlayer` pops one direction per tick; auto-run continues if queue empty
- [ ] Action keys (Speed, Space, F3, F6) fire immediately during drain
- [ ] F1, F2, F4, F5, Escape flush the queue before executing their action
- [ ] Game compiles (`poe build-original` exits 0)
- [ ] All tests pass (`poe test-original` exits 0)
- [ ] Manual check: holding End no longer blocks movement
- [ ] Manual check: quick Up→Left tap during leftward run executes both directions

## Background

The main loop sleeps `MoveDelay` ms per tick, then calls `HandleInput` which
reads at most one key.  At the default 100 ms tick with a 25 Hz key repeat
rate, holding a non-direction key (e.g. End) queues ~2–3 events per tick.
Each one consumes a full tick, blocking movement until the buffer is drained.

Additionally, quick directional taps (e.g. Up then Left within one tick) lose
the first direction if only one key is read per tick.

## Design

### Rename `HasTTYByte` → `KeyPressed`

`KeyPressed` is the established Turbo Pascal name.  `HasTTYByte` is an
implementation detail.  The function is used both as the public "is a key
available?" check and internally in `GetKey` for escape-sequence continuation
bytes; `KeyPressed` reads naturally in both roles.

### Drain loop

`HandleInput` changes from `if KeyPressed then` to `while KeyPressed do`.
Each iteration calls `GetKey` and dispatches the result:

- **Direction keys** (Right/Left/Up/Down): enqueue into the direction queue
  (see below).
- **Action keys** (Home, End, Space, F3, F6): execute immediately.  Multiple
  events of the same kind all fire — holding End applies several `SlowDown`
  calls in one tick, which is the desired behaviour.
- **Interrupt keys** (F1, F2, F4, F5, Escape): flush the direction queue,
  then execute the action (show help, show story, restart, remove blocks,
  quit).  Break out of the drain loop afterward so `KeyCode` is set correctly
  for the main loop's post-`HandleInput` checks.

### Direction queue

A ring buffer of `TDirection` values with capacity 8:

```
DirQueue: array[0..7] of TDirection;
DirHead, DirTail: Integer;  { head = next to read, tail = next to write }
```

**Enqueue rule:** only append if the new direction differs from the entry at
`(DirTail - 1) mod 8`.  This deduplicates auto-repeat (holding Left produces
one entry) while preserving deliberate direction changes (Up→Left produces
two).  If the queue is full, the oldest entry is silently dropped (advance
head).

**Dequeue:** `MovePlayer` pops one entry from the head each tick and sets
`Direction` before moving.  If the queue is empty, the current `Direction`
is used (auto-run preserved).

**Flush:** `DirHead := DirTail` (discard all entries).  Called before
interrupt-key actions.

### Example: quick Up→Left during leftward run

Player is running left.  Within one tick, the terminal buffer contains
`ESC[A ESC[D` (Up, Left).

1. Drain loop reads Up → enqueue `DirUp` (differs from tail, which was the
   previous `DirLeft` or empty).
2. Drain loop reads Left → enqueue `DirLeft` (differs from `DirUp`).
3. No more keys → drain ends.
4. `MovePlayer` pops `DirUp`, sets `Direction := DirUp`, moves up one cell.
5. Next tick: `MovePlayer` pops `DirLeft`, sets `Direction := DirLeft`,
   moves left.  Auto-run continues left.

Both keypresses are honoured across two ticks.

## Done when

- [ ] `HasTTYByte` renamed to `KeyPressed` everywhere (function + all call sites)
- [ ] `HandleInput` drains all pending keys in a `while KeyPressed do` loop
- [ ] Direction keys are enqueued, deduplicated against the tail
- [ ] `MovePlayer` pops one direction per tick from the queue
- [ ] Auto-run continues in current `Direction` when the queue is empty
- [ ] Action keys (Home, End, Space, F3, F6) fire immediately during drain
- [ ] F1, F2, F4, F5, Escape flush the direction queue before their action
- [ ] F1, F2, F4, F5, Escape break out of the drain loop
- [ ] Queue overflow drops the oldest entry
- [ ] Game compiles (`poe build-original` exits 0)
- [ ] All tests pass (`poe test-original` exits 0)
- [ ] Manual check: holding End no longer blocks movement for multiple ticks
- [ ] Manual check: quick Up→Left tap during leftward run executes both

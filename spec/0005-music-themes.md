# Level Music Themes

## Status

- [x] 10 composed melodic themes (64 MIDI pitches each) in `_LEVEL_THEMES`
- [x] Themes replace mechanical arpeggio patterns in `_make_music_track()`
- [x] L10 boss theme uses half-bar tritone arpeggio instead of a melody
- [x] Title screen theme (D minor, 80 BPM, 4 bars) in `_make_title_music()`
- [x] Win screen theme (C major, 108 BPM, 4 bars) in `_make_win_music()`

Ten composed melodic themes, one per level.  Each theme is 64 eighth-note
slots (8 bars × 8 steps) stored as absolute MIDI pitches in `_LEVEL_THEMES`
in `sounds.py`.  -1 = rest.

The lead voice synthesises the theme with FM (carrier:mod 1:1, index 4.0)
soft-clipped by tanh at drive 2.8.  A second voice doubles each bar's root
one octave lower with a brighter FM timbre (mod ratio 2.0, index 3.5).

---

## L1 — A Dorian, 96 BPM: "The Wanderer"

**Character:** Searching; rises from the tonic through the chord, swells to
the high octave, then descends gently back.  The raised-6th (F#) of Dorian
appears against the minor backdrop to keep it bittersweet rather than grim.

**Harmony:** Am – D – Em – Am | C – Em – Gm – Am

**Melody (MIDI):**
```
Bar 1 Am:  69 72 76 74  76 72 71 69   (A C E D | E C B A)
Bar 2 D:   74 78 81 79  78 76 74 -1   (D F# A G | F# E D _)
Bar 3 Em:  76 74 72 71  69 67 66 64   (E D C B | A G F# E)
Bar 4 Am:  69 71 72 76  74 72 71 69   (A B C E | D C B A)
Bar 5 C:   79 76 72 74  76 79 81 -1   (G E C D | E G A _)
Bar 6 Em:  71 69 67 66  67 69 71 72   (B A G F#| G A B C)
Bar 7 Gm:  67 70 74 72  70 67 69 -1   (G Bb D C | Bb G A _)
Bar 8 Am:  69 -1 76 74  72 71 69 64   (A _ E D | C B A E)
```

---

## L2 — D Natural Minor, 101 BPM: "The Chase"

**Character:** Driving, relentless descent.  The melody rarely rests; it
cycles through the minor scale with a sense of always being pursued.
Ends with a chromatic slide down to D3, landing hard.

**Harmony:** Dm – C – Bb – Am | Gm – Am – C – Dm

**Melody (MIDI):**
```
Bar 1 Dm:  74 77 81 79  77 76 74 72   (D F A G | F E D C)
Bar 2 C:   72 70 69 67  69 70 72 74   (C Bb A G | A Bb C D)
Bar 3 Bb:  70 72 74 72  70 69 67 65   (Bb C D C | Bb A G F)
Bar 4 Am:  69 -1 67 69  70 69 67 65   (A _ G A | Bb A G F)
Bar 5 Gm:  67 70 74 72  70 67 69 70   (G Bb D C | Bb G A Bb)
Bar 6 Am:  69 72 76 74  72 70 69 -1   (A C E D | C Bb A _)
Bar 7 C:   72 74 76 74  72 70 69 67   (C D E D | C Bb A G)
Bar 8 Dm:  74 72 70 69  67 65 64 62   (D C Bb A | G F E D)
```

---

## L3 — G Phrygian, 106 BPM: "Shadow Step"

**Character:** Ominous.  The Phrygian flat-2 (Ab over G) is the centrepiece;
the half-step G→Ab appears at the start of almost every phrase, unsettling
the ear before resolving.  Bar 3 shoots up to G5 then descends the full
scale back to G4 in one stepwise sweep.

**Harmony:** Gm – Ab – Gm – Ab (alternating throughout)

**Melody (MIDI):**
```
Bar 1 Gm:  67 68 70 67  68 70 72 70   (G Ab Bb G | Ab Bb C Bb)
Bar 2 Ab:  68 67 65 63  62 63 65 67   (Ab G F Eb | D Eb F G)
Bar 3 Gm:  79 77 75 74  72 70 68 67   (G5 F Eb D | C Bb Ab G)
Bar 4 Ab:  68 70 72 70  68 67 65 63   (Ab Bb C Bb | Ab G F Eb)
Bar 5 Gm:  67 70 74 75  74 72 70 68   (G Bb D Eb | D C Bb Ab)
Bar 6 Ab:  72 74 75 77  79 77 75 74   (C D Eb F | G F Eb D)
Bar 7 Gm:  74 72 70 68  67 68 70 72   (D C Bb Ab | G Ab Bb C)
Bar 8 Ab:  67 -1 68 67  65 63 62 67   (G _ Ab G | F Eb D G)
```

---

## L4 — A Harmonic Minor, 111 BPM: "Ancient Danger"

**Character:** Exotic and threatening.  The harmonic minor's augmented 2nd
(F→G#) creates the characteristic Middle-Eastern tension.  Bar 1 rockets
straight up the A minor arpeggio to A5; bars 5–6 land on F then use G# to
climb back, making the exotic interval unmistakable.

**Harmony:** Am – Dm – E – Am | F – Dm – E – Am

**Melody (MIDI):**
```
Bar 1 Am:  69 76 80 81  80 76 74 72   (A E G# A5| G# E D C)
Bar 2 Dm:  74 72 71 69  68 69 71 74   (D C B A | G# A B D)
Bar 3 E:   76 80 81 80  76 74 72 71   (E G# A5 G#| E D C B)
Bar 4 Am:  69 -1 76 80  81 80 76 69   (A _ E G# | A5 G# E A)
Bar 5 F:   77 76 74 72  71 69 68 65   (F E D C | B A G# F)
Bar 6 Dm:  74 71 68 69  71 74 76 -1   (D B G# A | B D E _)
Bar 7 E:   76 74 72 71  69 68 69 76   (E D C B | A G# A E)
Bar 8 Am:  69 68 69 72  76 74 72 69   (A G# A C | E D C A)
```

---

## L5 — E Natural Minor, 116 BPM: "Pursuit"

**Character:** Energetic, barely controlled.  Wide leaps (octaves and
sixths) keep the listener off-balance.  The second half climbs from A4 all
the way to G5 before crashing back down — a sense of desperate acceleration.

**Harmony:** Em – D – C – Bm | Am – D – Em – Bm

**Melody (MIDI):**
```
Bar 1 Em:  76 74 71 67  69 71 74 76   (E D B G | A B D E)
Bar 2 D:   74 72 71 69  71 72 74 -1   (D C B A | B C D _)
Bar 3 C:   72 71 69 67  66 67 69 71   (C B A G | F# G A B)
Bar 4 Bm:  71 -1 74 78  76 74 71 -1   (B _ D F# | E D B _)
Bar 5 Am:  69 67 69 71  72 74 76 78   (A G A B | C D E F#)
Bar 6 D:   74 76 78 79  78 76 74 72   (D E F# G | F# E D C)
Bar 7 Em:  76 74 72 71  69 67 66 64   (E D C B | A G F# E)
Bar 8 Bm:  71 69 67 66  64 -1 71 76   (B A G F#| E _ B E5)
```

---

## L6 — B Phrygian, 120 BPM: "Edge of Darkness"

**Character:** Tight, tense stepwise motion with chromatic inflections.
The Phrygian half-step (B→C) opens every phrase and keeps returning.
The second half builds upward to G5 before collapsing — the furthest point
from home before the loop restarts.

**Harmony:** Bm – C – Bm – Am | Bm – C – Bm(dim) – Am

**Melody (MIDI):**
```
Bar 1 Bm:  71 72 74 72  71 69 67 66   (B C D C | B A G F#)
Bar 2 C:   72 74 76 74  72 71 72 -1   (C D E D | C B C _)
Bar 3 Bm:  71 69 67 66  67 69 71 72   (B A G F#| G A B C)
Bar 4 Am:  69 67 66 64  66 67 69 71   (A G F# E| F# G A B)
Bar 5 Bm:  71 72 71 69  67 66 67 69   (B C B A | G F# G A)
Bar 6 C:   72 74 76 78  79 78 76 74   (C D E F#| G F# E D)
Bar 7 Bm:  71 74 78 76  74 72 71 -1   (B D F# E| D C B _)
Bar 8 Am:  69 -1 67 69  71 69 67 71   (A _ G A | B A G B)
```

---

## L7 — F# Natural Minor, 125 BPM: "Relentless"

**Character:** Aggressive.  The melody descends from F#5 to F#4 in bar 1,
then climbs back up and descends again, relentlessly.  No rests in bars 1–3;
the few rests later feel like gasps.  Angular leaps (tritones, sixths) keep
it uncomfortable.

**Harmony:** F#m – Bm – E – F#m | F#m(dim) – E – Bm(dim) – F#m

**Melody (MIDI):**
```
Bar 1 F#m: 78 76 74 73  71 69 68 66   (F#5 E D C#| B A G# F#)
Bar 2 Bm:  71 69 68 66  68 69 71 73   (B A G# F#| G# A B C#)
Bar 3 E:   73 74 76 74  73 71 69 68   (C# D E D | C# B A G#)
Bar 4 F#m: 66 -1 71 73  74 73 71 -1   (F# _ B C#| D C# B _)
Bar 5 dim: 78 74 71 73  74 76 78 -1   (F#5 D B C#| D E F# _)
Bar 6 E:   76 73 69 71  73 74 76 -1   (E C# A B | C# D E _)
Bar 7 dim: 74 73 71 69  68 69 71 73   (D C# B A | G# A B C#)
Bar 8 F#m: 66 -1 73 71  69 68 66 -1   (F# _ C# B| A G# F# _)
```

---

## L8 — C# Diminished, 130 BPM: "Fragmentation"

**Character:** Chaotic but purposeful.  Wide tritone leaps and fast stepwise
runs in opposite directions.  The diminished scale's symmetry means the
melody keeps arriving at the same four pitches (C# E G Bb) from unexpected
angles.  Bar 7 is the only moment of upward momentum before bar 8 closes
with a tritone snap.

**Harmony:** C#dim throughout (descending and ascending)

**Melody (MIDI):**
```
Bar 1:  73 76 79 -1  78 76 75 73   (C# E G _ | F# E D# C#)
Bar 2:  76 78 79 81  82 81 79 78   (E F# G A | Bb A G F#)
Bar 3:  79 81 82 -1  81 79 78 76   (G A Bb _ | A G F# E)
Bar 4:  73 -1 79 78  76 75 73 -1   (C# _ G F#| E D# C# _)
Bar 5:  75 76 78 79  81 82 81 79   (D# E F# G| A Bb A G)
Bar 6:  81 79 78 76  75 73 75 76   (A G F# E | D# C# D# E)
Bar 7:  78 76 75 73  75 78 79 81   (F# E D# C#| D# F# G A)
Bar 8:  79 -1 78 76  75 73 76 73   (G _ F# E | D# C# E C#)
```

---

## L9 — G# Phrygian, 135 BPM: "Terror"

**Character:** Unrelenting.  Bars 1–2 descend from G#5/A5 all the way to A4;
bars 3–4 climb back up and then rocket further.  Bar 5 begins the second
half from G#3 (very low) and rises over two bars to A5, making the full
three-octave range of the theme feel like a scream.

**Harmony:** G#m – A – G#m – G#m | G#m – A – G#m(dim) – G#m

**Melody (MIDI):**
```
Bar 1 G#m: 80 81 80 78  76 75 73 71   (G#5 A G# F#| E D# C# B)
Bar 2 A:   81 80 78 76  75 73 71 69   (A5 G# F# E | D# C# B A)
Bar 3 G#m: 71 73 75 76  78 80 81 -1   (B C# D# E | F# G# A _)
Bar 4 G#m: 80 -1 81 80  78 76 75 80   (G#5 _ A G#| F# E D# G#)
Bar 5 G#m: 68 69 71 73  75 76 78 80   (G#3 A B C#| D# E F# G#)
Bar 6 A:   81 78 75 76  78 80 81 -1   (A5 F# D# E | F# G# A _)
Bar 7 dim: 78 76 75 73  71 73 75 78   (F# E D# C#| B C# D# F#)
Bar 8 G#m: 80 -1 80 78  76 75 73 68   (G#5 _ G# F#| E D# C# G#3)
```

---

## L10 — Chromatic Diminished, 140 BPM: "Boss"

**Character:** Relentless and mechanical.  A two-note tritone arpeggio
repeats every half bar: the upper note (mel_root + 6) hits on beat 1
(locking with the kick drum), the lower note (mel_root) hits on beat 3
(locking with the snare), beats 2 and 4 are silence.  The roots follow
the descending dim7 sequence B→Ab→F→D→B→Ab then rise back, so the
interval content shifts while the rhythmic pattern stays constant.

**Harmony:** B dim – Ab dim – F dim – D dim | B dim – Ab dim – B dim – D dim

**Pattern per bar:** `HIGH  –  LOW  –  |  HIGH  –  LOW  –`
(steps 0, 2, 4, 6 only; steps 1, 3, 5, 7 are rests)

**Melody (MIDI):**
```
Bar 1 (root B4=71):   77 -1 71 -1  77 -1 71 -1   (F5 – B4 – | F5 – B4 –)
Bar 2 (root Ab4=68):  74 -1 68 -1  74 -1 68 -1   (D5 – Ab4–| D5 – Ab4–)
Bar 3 (root F4=65):   71 -1 65 -1  71 -1 65 -1   (B4 – F4 – | B4 – F4 –)
Bar 4 (root D4=62):   68 -1 62 -1  68 -1 62 -1   (Ab4– D4 – | Ab4– D4 –)
Bar 5 (root B3=59):   65 -1 59 -1  65 -1 59 -1   (F4 – B3 – | F4 – B3 –)
Bar 6 (root Ab3=56):  62 -1 56 -1  62 -1 56 -1   (D4 – Ab3– | D4 – Ab3–)
Bar 7 (root B3=59):   65 -1 59 -1  65 -1 59 -1   (F4 – B3 – | F4 – B3 –)
Bar 8 (root D4=62):   68 -1 62 -1  68 -1 62 -1   (Ab4– D4 – | Ab4– D4 –)
```

---

## Title screen — D Natural Minor, 80 BPM

**Character:** Dark, stately, epic.  A stepwise descent with upward lifts —
memorable on first listen, bearable after many loops.  Slower than any
level track to feel deliberate and dramatic.

**Orchestration:** Thick detuned strings in two octaves, low triangle bass
(root/fifth alternation), square brass pedal on bar downbeats, timpani on
bars 1 & 3, pulse-wave lead with an upper-harmonic doubling (freq × 2).

**Harmony:** Dm – F – Gm – A

**Melody (MIDI):**
```
Bar 1 Dm:  74 72 70 69  67 65 67 69   (D5 C5 Bb4 A4 | G4 F4 G4 A4)
Bar 2 F:   70 69 67 65  64 62 -1 -1   (Bb4 A4 G4 F4 | E4 D4 _ _)
Bar 3 Gm:  67 69 70 72  70 69 67 65   (G4 A4 Bb4 C5 | Bb4 A4 G4 F4)
Bar 4 A:   69 -1 74 72  69 -1 74 -1   (A4 _ D5 C5 | A4 _ D5 _)
```

---

## Win screen — C Major, 108 BPM

**Character:** Joyful but not pompous.  Opens with a rising C major arpeggio
(classic fanfare gesture), descends warmly through Am and F, then climbs
back for a satisfying G→C resolution.  Faster than the title (108 vs 80 BPM)
to feel celebratory and light.

**Orchestration:** Same as the title screen — strings in two octaves, triangle
bass, square brass pedal, timpani on bars 1 & 3, pulse-wave lead.

**Harmony:** C – Am – F – G

**Melody (MIDI):**
```
Bar 1 C:   67 72 76 79  79 76 74 72   (G4 C5 E5 G5 | G5 E5 D5 C5)
Bar 2 Am:  76 69 72 76  74 72 71 69   (E5 A4 C5 E5 | D5 C5 B4 A4)
Bar 3 F:   65 69 72 77  76 74 72 74   (F4 A4 C5 F5 | E5 D5 C5 D5)
Bar 4 G:   67 74 79 74  79 76 72 -1   (G4 D5 G5 D5 | G5 E5 C5 _)
```

---

## Done when

- [x] All 10 level themes are distinct, recognisable melodies (not mechanical arpeggios)
- [x] L10 boss theme is a tritone arpeggio pattern, not a composed melody
- [x] Title screen theme plays on the title screen
- [x] Win screen theme plays on the win screen
- [x] Music loops seamlessly without pops or gaps

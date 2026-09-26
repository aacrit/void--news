# The Argument — Weekly's audio edition

Written 2026-09-20 (rev 72). Companion to `docs/ON-AIR-RADIO.md` and
`docs/HISTORY-AUDIO.md`.

## What it replaces

Weekly audio had never been designed. On Air moved to Kokoro, a validated
rundown, a scored timeline and chapters in rev 67-68; History got its own
documentary format in rev 70. The weekly was the last thing in the product
still on the 2026-06 stack:

- ONE Gemini call writing free `A:`/`B:` dialogue into `produce_audio()`.
- Two voices, Andrew and Ava, the same pair every other edition has used.
- No voice chain, no compressor, no limiter, no loudnorm: **unmastered mono**.
- Four bookend WAVs from the 2026-05 set and a 10-second loop ducked by RMS.
- No chapters, no sidecar, not in the podcast feed, no tests, no validators.

Four things in it were **inert**, not merely dated:

| | |
|---|---|
| `_WEEKLY_TTS_PREAMBLE` | 23 lines about "magazine pace" and "a full breath beat", assigned and read only by the **parked** Gemini TTS path. Every pacing instruction was discarded. |
| `WEEKLY_VOICE_PAIR` | "The Editor" and "The Correspondent" map through `_GEMINI_TO_EDGE_VOICE` to Andrew and Ava: a label over an identical signal chain. |
| The prompt's `NO [SEGMENT] headers. Raw dialogue only.` | Its six segments existed only as instructions to the model. That one line is why no timeline, no chapters and no per-segment music were possible. |
| "a full beat of silence" | Rendered as **60 ms**. On Air: 650-900. History's `REST`: 7,500. |

It was also one good week from dropping the editorial silently. The last issue
shipped at 11,310,093 bytes, **93.7% of the 12 MB cap**, at 1,782 words — 40%
*under* its own target. At the target length the ladder's third rung amputates
the editorial and nulls `opinion_start_seconds`, with nothing to notice.

All of the above is **kept** as the fallback. A weekly that cannot be validated
still ships a show.

## The show

On Air is *what happened today*. History is *what it meant then*. **The weekly
is what we argued about, and what the argument looked like from outside.**

The generator already writes two columns on the *same* cover story, each told
in its prompt that the other exists and will be read beside it. Nothing had
ever staged them.

```
theme (Sunday cue, 10 s)
OPEN         E   the week in one image. Not a headline list.
CONTENTS     E   "Inside this week." Four lines.                 [bed]
COVER        E   the lead feature
  DATELINE   E   "Tuesday. Thirteen sources."  + a held beat     « device 2
COVER        E   the rest of it
transition
TOPIC        E   names the story once, then gets out of the way  « device 1
LEFT         L   the left column, selected, DRY — no bed
  (the spine)    2,400 ms of nothing
RIGHT        R   the right column, selected, DRY
REST             held pause
TURN         E   what each side leaves out. Both, never one.
transition
SECOND       E   feature 2
DEPARTMENT   E   Technology or Sports & Culture
break (9 s)
NUMBERS      E   The Week in Bias, read as measurement           « device 3
                 the spectrum sonified beneath it, -40 dBFS
EDITORIAL    E   the argued column                               [bed returns]
CLOSE        E   the question the week left open                 « device 4
outro (14 s, falling to TRUE silence)
```

**Why the Editor reads the editorial.** The bench voices *only ever argue*; the
Editor *only ever speaks for Void*. Giving the Editorial to a bench voice would
muddy the one line that matters. That firewall is cleaner than On Air's, not
weaker.

## The moat: W-01

The script does not paraphrase the columns, it **selects** from them, the way
History's document voice reads primary sources rather than summarising them.

> Every `L:` and `R:` line must exist in that column's published
> `opinions[].text` by word overlap (floor 70%, multiset).

Trimming for the ear is allowed; inventing is not. It is H-01 applied to
argument instead of archive, and it makes the show's core content
unfabricatable: a listener hears the same words a reader reads.

`_bench_columns` mirrors `findPair` in `Perspectives.tsx` exactly — `pair_id`,
then the `paired` flag, then a left/right match on one topic — so the programme
and the page cannot disagree about which two essays are the argument.
`tests/test_weekly_script.py` asserts it.

### W-04 was rewritten on measurement

The obvious check for "does the turn engage both columns" is overlap, and it
**does not work**: the two columns argue the same story and share most of their
vocabulary.

| turn | overlap vs L | overlap vs R | distinctive L | distinctive R |
|---|---|---|---|---|
| drawn only from the left column | 1.00 | **0.76** | 36 | **0** |
| balanced | 0.78 | **0.84** | 21 | **24** |

An 8-point overlap gap is not a signal. Words present in one column and absent
from the other separate cleanly. Same move the ranker makes when it stops
counting shared stems and starts counting *specific* ones.

## Validators

Stable IDs in their own namespace (`verify_sections`' W-01..W-09 are the served
page; these are the script).

| | |
|---|---|
| W-01 | every bench line exists in its own published column |
| W-02 | the bench speaks only inside its column; the Editor never does |
| W-03 | airtime within 1.35x between the two sides |
| W-04 | the turn engages both columns, by distinctive vocabulary |
| W-05 | the programme's shape: every required movement, no unknown marker |
| W-06 | the dateline beat exists; a rest is expected |
| W-07 | 18-22 minutes, measured per voice, not against one constant |
| W-08 | Void's own lines: no borrowed radio furniture, no podcast tells |
| W-09 | no figure read aloud that the issue does not carry |
| W-10 | the close asks rather than states |
| W-11 | the contents is four lines, not a rundown |
| W-12 | no quotation marks in spoken copy |

A rundown with any `fail` is **not rendered**, and the caller falls back to the
legacy path. That asymmetry is deliberate: an essay running forty words long is
worth shipping; a bench line the column does not contain is words put in a
columnist's mouth.

## Cast

| Role | Voice | Measured | Why |
|---|---|---|---|
| **E** Editor | `bm_lewis` | 172 wpm, 93 Hz | Gravest on the roster; British, so instantly not On Air's anchor. |
| **L** left bench | `am_michael` | 160 wpm | On Air's *previous* anchor, retired from that job. |
| **R** right bench | `af_heart` | 162 wpm | The roster's only A-grade voice. |

**The bench must be rate-matched.** Two voices at different natural rates give
one side materially more airtime for the same words, which is an editorial
fairness problem and not an aesthetic one. 160 and 162 are two apart. The
Editor is deliberately the outlier: the spine should not sound like a bench.
House pace `0.92` uniformly, against On Air's 0.95 — a decision about the
programme, which the doctrine permits. Pace is a casting decision, never a
stretch.

The Editor sits centre; the bench is panned ±0.16, because the one thing a
listener must never lose track of is *which side is speaking*, and the room
says it before the timbre does.

## Sound

`_theme_figure` is fully parameterised, so the Sunday cue family is a
**parameter set** rather than new synthesis: the same motif at **half the
tempo** (60 bpm), opening on the **suspended fourth** (G over the D root) and
resolving only at the outro, because the programme's shape is an argument that
is not settled until the editorial.

| file | length | note |
|---|---|---|
| `weekly_theme.wav` | 10.0 s | five bars, unresolved |
| `weekly_transition.wav` | 3.5 s | the cell at 60 bpm, in the clear |
| `weekly_break.wav` | 9.0 s | before the numbers |
| `weekly_bed.wav` | 24.0 s | exact seam, looped with **no** crossfade |
| `weekly_outro.wav` | 14.0 s | sus4 resolved, falling to **true** silence (asserted) |

`radio_room_tone.wav` is reused as-is: a studio floor is a studio floor.

**The argument is dry.** Beds run under OPEN, CONTENTS, NUMBERS, EDITORIAL and
CLOSE, and nowhere else. Two people disagreeing over a bed is a talk show;
naked voice with a held pause between the sides is a courtroom. The bed
*returning* for the editorial is therefore also the opinion entrance.

**The sonified spectrum** under THE NUMBERS carries the week's mean lean as
pitch (root D at centre, a fifth either way at the extremes) and its spread as
detuning width, so a balanced-but-**contested** week beats audibly while a
genuine consensus sits still. That is the distinction the Sigil's divergence
fan draws on the page, in the one medium where a fan cannot be drawn. It is
generated per issue and never written to disk.

## Reuse

Everything format-agnostic comes from `radio_producer`: synthesis, voice buses,
the per-voice ffmpeg chain, the duck (with `dark=`), `_loop_to`,
`loudnorm_two_pass`, `encode_mp3`, `write_id3_chapters`, `chapters_sidecar`.
`_as_radio_timeline` is the same shim History uses, at the same seam — the
precise boundary between what is reusable and what is this format's own.

What is **not** reused is `build_timeline`, which hard-codes the radio segment
kinds, and the gap table. A magazine has a different grammar.

## House promo (post-roll)

After the open question, under the outro, the house voice reads a two-sentence
promo for On Air, History or the site. It is a producer-level post-roll, not
a marker, so W-05's closed set is untouched, and W-07's length is measured
before it and unchanged by it. Selected by the sha256 of
`weekly:<edition>:<week_start>`; appears as a final chapter, kind `promo`.
Rules and copy: `docs/VOICE-BRAND.md`, "House Promos".

## Size

22 MiB, with On Air's rule: **the editorial is never dropped**. Twenty minutes
at 128k stereo is about 19 MB; Pages allows 25 MiB per file and History's
largest episode is 13.9 MB. The ladder steps 128k/2 → 96k/2 → 96k/1 → 64k/1 and
then ships whole rather than amputating a movement.

## Files

```
pipeline/briefing/weekly_script.py      format, parser, W-01..W-12
pipeline/briefing/weekly_rundown.py     the one Gemini call + one regeneration
pipeline/briefing/weekly_producer.py    timeline, gap table, music bus, master
pipeline/briefing/generate_assets.py    render_weekly_assets() + weekly_spectrum()
tests/test_weekly_script.py             clean fixture from the REAL issue + planted defects
tests/test_weekly_assembly.py           the spine, the dry argument, the chapters
```

## Rollback

| | |
|---|---|
| `VOID_WEEKLY_AUDIO_FORMAT=0` | keep audio, fall back to the legacy two-voice read |
| `VOID_TTS_ENGINE=edge` | keep the new format, on edge voices |
| `DISABLE_AUDIO=1` | no audio at all |

## Open

The first episode is **unheard**. `weekly-digest.yml` now carries the Kokoro
venv and the model cache, but nothing has run it. Listen for: the bench
swapping voices mid-argument, the 2.4 s spine, the dateline beat inside the
cover feature, the spectrum under the numbers, and the outro reaching true
silence.

---

## The fallback is gone (2026-09-21)

`_produce_argument` used to return `None` on any of six failures and the caller
silently shipped the legacy two-voice edge-tts read in its place. The reasoning
for refusing a bad rundown was sound and still stands: an essay forty words long
is worth shipping, but a bench line the published column does not contain is
words put in a columnist's mouth.

The flaw was that the substitution was **silent**. Every scheduled run since the
format shipped had taken that path, so a format that had never once produced a
scheduled episode looked like a format that worked. The published row said
"Three voices" and `kokoro:bm_lewis+am_michael+af_heart` over a file measuring
24000 Hz, 1 channel, 96 kb/s, 1002 s, -20.5 LUFS, while claiming 1349.7 s. A
listener was told three voices and heard two.

**Now:** if The Argument does not render, the run raises and the Weekly ships
without audio. Each of the six causes names itself in the log; an import error,
a rejected rundown and a render crash are three different problems.
`VOID_WEEKLY_AUDIO_FORMAT=0` is the only remaining route to the legacy read, and
it **parks** audio rather than substituting for it.

Two supports were removed with it. `build_weekly_row` used to fill
`audio_voice` from `voice_pair` whenever an audio_url existed and the renderer
had not named a cast, which is how a row learns to advertise voices that never
read it; a missing voice now reads as missing. And
`scripts/verify_sections.py:315` read
`report("W-09", True, "legacy two-voice read, no chapter rail (acceptable)")`,
a gate hard-coded to pass the exact defect it exists to catch.

`tests/test_weekly_audio_served.py` probes the **artifact**: duration against
the row, stereo, loudness within 1 LU of -16, a chapters sidecar, a Kokoro cast.
Every other Weekly check runs before synthesis.

## The word budget

W-07's band is the format and is not negotiable. The generator used to be told
something different from what W-07 measures: its prompt asked for
`band x 163 wpm`, while `estimated_minutes` adds `MUSIC_MINUTES` (1.4) of theme,
beds and outro that nobody speaks over. The prompt's ceiling was ~228 words past
what the band allows, so a rundown could obey the prompt exactly and still be
rejected. That is what sent 2026-09-20 to the legacy read.

`weekly_script.word_budget()` owns the conversion now, beside the constants
W-07 measures with. **The two edges take opposite rates**: runtime is words over
rate, so the ceiling assumes the slowest voice and the floor the fastest. One
blended rate puts the floor below the band whenever the Editor at 172 wpm
carries most of the programme, which he always does.

The prompt also now names the `BORROWED` list. W-08 rejected "absolutely" from
a rundown whose prompt had never mentioned it; a rule the writer cannot see is
not a rule.

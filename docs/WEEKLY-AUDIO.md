# The Argument, rev 2: Weekly's audio edition

Written 2026-11-08 (rev 2, the CEO's ask: "an enhanced version of the weekly
audio as well, it should feel similar yet should be completely a weekly style
show with a little more drama and one more anchor. Embody this in the score,
beats, and how the episode is structured"). Companion to
`docs/ON-AIR-CONVERSATION.md`, whose family this is. The rev 1 design
(2026-09-20) is kept at the bottom as the record.

On Air is *what happened today*. History is *what it meant then*. **The weekly
is what we argued about, and what the argument looked like from outside.**

The first rev 2 output is Issue 32 (week of 2026-10-26 to 2026-11-01):
`frontend/public/audio/weekly-world/2026-11-01-pm.mp3`, 15:14, 14.6 MB, nine
chapters, -16.0 LUFS integrated, -2.0 dBTP, phone margin 16.8 dB, nothing cut
by grounding. It is the only Weekly carrying audio when rev 2 landed: rev 1's
one published episode, Issue 26, was withdrawn 2026-10-02 and never
re-rendered.

| What | Where |
|---|---|
| The script: grammar, parser, W-01..W-17, the grounding pass, the band, the cast and the side rule | `pipeline/briefing/weekly_script.py` |
| The score: every cue of the weekly's music, composed on On Air's patches | `pipeline/briefing/weekly_music.py` |
| The standard it is measured against (shared with On Air; the `sting` role is the weekly's) | `pipeline/briefing/onair_score.py` |
| Production: Kokoro, the voice chain, the timeline, score placement, mix, master, chapters, the music-only reel | `pipeline/briefing/weekly_producer.py` |
| The one Gemini call, for a Sunday run | `pipeline/briefing/weekly_rundown.py`, called from `weekly_digest_generator._produce_argument` |
| The committed-script path (no Gemini, no DB) | `pipeline/briefing/render_weekly_audio.py`, `data/weekly/scripts/<week_start>.txt` |
| Gates | `tests/test_weekly_script.py` (WA-01..WA-10), `tests/test_weekly_assembly.py` (WB-00..WB-11), `tests/test_weekly_audio_served.py` (the artifact) |

## Feels similar, completely weekly

What the two programmes share is everything that makes a sound Void's: D minor
on the 84-beat grid, the seven-note hook, the FM electric piano and the felt
bell, the detuned pad, the sub bass with its octave, the soft kick with a knock,
the brush and the shaker, the same rooms, the same voice chain and mastering,
the same chapter grammar, the Void Opinion entrance note for note, and the same
anchor: `af_aoede` reads the news and Void Opinion on On Air and is the host of
The Argument.

What is weekly is the shape of everything on top of that:

| | On Air | The Argument |
|---|---|---|
| Cast | two anchors | three voices: a host and two correspondents |
| Pulse | the kick on one and three | **half-time**: the kick on one, a brush on three; felt at 42 a minute on the same grid |
| The hook | at tempo, two bars | **at half speed**, four bars, the bell an octave up |
| Cadence | i VI III VII (ends on the subtonic) | i VI iv V (Dm Bb Gm A): **ends on the dominant**, unresolved, until the outro lands on D major |
| Between movements | an 8.6 s interlude, a breath | a 12.2 s interlude that opens on a **riser into a hit**, the page turned; the tune in dotted augmentation over three chords |
| Before the argument | (none) | a **tension bed** (no drums; the dominant pedal in eighths on the sub, the pad opening and rising) and a **sting**: the verdict |
| The argument | (none) | **dry**: no music under either column, 2.4 s of nothing between them, a 6.5 s rest after, the frame closing as the turn's bed swells in |
| A date | the day in the sign-on | a **dateline** inside the cover and a **toll** (the low bell on D3) in the held beat after it; the same toll opens the theme and is the sting's bell |
| Length | about eleven minutes | fourteen to twenty-two, sized to the issue |

## The show

```
COLD        H  one or two lines in the clear over the floor: the week's single hardest image
theme       18.0 s featured. Bar 0 the toll on D3, a sub swell, a dark pad. Bars 1-4 the half-time
            drums enter and build, the hook at half speed over Dm Bb Gm A, the bell doubling its fall.
            A riser into bar 5: a hit, the pad held on Dm. The sign-on lands on that downbeat (14.3 s).
OPEN        H  "From Void News, this is The Argument. The week of <dates>." then the week in one image
                                                                       [bed: open, half-time, from the hold]
CONTENTS    H  "Inside this week." four lines
COVER       A leads, B takes passages including the last; 3-9 passages of 18-130 words
  DATELINE  H  "Tuesday. Twenty-four sources." then a held beat the toll rings in
  COVER     continues                                                  [bed: feature, under the first two
                                                                        passages, the dateline, the last]
interlude   12.2 s, the first, heard in the clear; the host speaks 10.1 s in, over the release bar
TOPIC       H  names the story the two columns argue, once; "The left column first."
                                                                       [bed: tension, rising into the sting]
sting       4.6 s: a dark riser, a hit, the toll, a held sub, cut to the floor. Then 1.4 s of nothing.
LEFT        A  the left column, selected, DRY
spine       2.4 s of nothing
RIGHT       B  the right column, selected, DRY
REST        6.5 s; 1.2 s after the right column's last word the turn's bed swells in from the floor
TURN        H  what each side leaves out. Both, never one.             [bed: turn, the slow room, rising]
interlude   the second: never the first's tune, chords or voice
SECOND      B leads, A takes passages including the last; 2-7 passages  [bed: feature]
DEPARTMENT  H  optional (both departments suspended since 2026-10-02)   [bed: feature]
WEEK        H  "The week in brief." then A and B alternate the briefs, two or three sentences each;
               after every second item a 2.4 s breath the duck lets the bed up in, and a bell answers
                                                                       [bed: week, the pushed pulse,
                                                                        throughout; it STOPS on a hit]
NUMBERS     H  The Week in Bias, ONLY when the issue carries a bias report [the spectrum drone under it]
silence     1.6 s of the -70 dBFS floor
entrance    11.4 s, "Void Opinion": On Air's cue, unchanged; H speaks 9.8 s in, on the held last note
EDITORIAL   H  "This is Void Opinion. <headline>." then Void's column, paragraph by paragraph, AS WRITTEN
                                                                       [bed: editorial, the slow room,
                                                                        never on the tonic]
CLOSE       H  the question the week leaves open; "That's The Argument, from Void News. Every source,
               every story, scored for bias."                          [bed: close, rising]
outro       18.0 s featured: the cadence with the hook at half speed and the bell above it, a riser,
            the landing on D MAJOR held on a sub with a bell arpeggio, the pad falling to silence;
            the house promo rides it
```

Chapters: `The week` (0 s, kind `open`: the cold open and the sign-on), `Inside
this week`, the cover's title (`cover`), `The Argument` (`topic`, from the first
interlude), the second feature's title (`second`, from the second interlude),
`The week in brief`, `The Week in Bias` when read, `Void Opinion` (`editorial`,
the headline as subtitle, from the entrance; `opinion_start_seconds` keeps that
meaning), `The open question`, `Also from Void`. Beats (the dateline, the two
columns, the turn, the rest) are inside their movement and are not chapters.

## Cast

| Role | Voice | Reads |
|---|---|---|
| **H** the host | `af_aoede` | Void's voice, and On Air's anchor: the cold open, the sign-on, the week in one image, the contents, the datelines, the framing, the turn, the numbers, the editorial, the close |
| **A** correspondent | `am_puck` or `bf_emma` | leads the cover, takes passages of the second feature, half the week in brief, **and the left column** |
| **B** correspondent | the other | leads the second feature, takes passages of the cover, the other half of the week, **and the right column** |

**The side rule.** `cast_for_week(week_start)` draws which voice is A and
which is B from the sha256 of `argument:<edition>:<week_start>`: even first
byte, `am_puck` reads the left column; odd, `bf_emma` does. The same week
always casts the same way, so a re-render is the same show, and over a volume
neither voice owns a political side (WA-10 asserts the split lands between 30
and 70 per cent over a year of Mondays). Issue 32: A `am_puck`, B `bf_emma`.
The row's `audio_voice` names the voices in that order: host, left reader,
right reader (`kokoro:af_aoede+am_puck+bf_emma`).

**One pace, 0.88, for all three**: On Air's calm pace (CEO 2026-11-08). No
voice is stretched on its own. Measured over the whole Issue 32 script through
the real worker, after the voice chain's trim: `af_aoede` 147 wpm, `am_puck`
154, `bf_emma` 144 (`VOICE_WPM`; the same voices read one brisk 118-word
passage at 168, 184 and 173, which is why the first estimate was two minutes
short). The two correspondents are therefore NOT rate-matched, which rev 1
required of its bench. W-03 answers that by measuring **airtime**, words over
each reader's rate, instead of words: the rule knows the rates rather than
demanding a matched pair. Three positions in the room: the host centre, A 16 %
left, B 16 % right, so the listener never loses which side is speaking.

`bf_emma` was rev 4's second anchor on On Air (heard by the CEO, not rejected);
`am_puck` is On Air's second anchor since rev 5.

## The firewall, the moat, and Rule 1

Three things hold every word to the published issue.

**The firewall (W-02).** The host never reads a column. One correspondent
reads one column: A the left, B the right, nobody else inside either. The
correspondents never speak in Void's movements (the open, the contents, the
datelines, the topic, the turn, the numbers, the editorial, the close) and the
host never reads a feature. Giving the editorial to a correspondent, or a
column to the host, would muddy the one line that matters.

**The moat (W-01).** Every line in LEFT and RIGHT exists in that column's
published `opinions[].text` by word overlap (floor 70 %, multiset). The script
SELECTS from the columns, the way History's document voice reads primary
sources; trimming for the ear is allowed, inventing is not. `_bench_columns`
mirrors `findPair` in `Perspectives.tsx`, so the programme and the page cannot
disagree about which two essays are the argument.

**Every other line, twice (W-13 and the grounding pass).** Rev 1 held the
Editor to the issue; rev 2 holds EVERY voice outside the columns: every number
read as a value ("twenty-four" is 24) and every multi-word proper name must be
in the published issue (W-13, the Weekly print rule, blocking). Then
`ground_script` runs the same deterministic pass On Air's `ground_show` runs
(`editorial/derived_grounding`) over every sentence outside the columns, with
the whole issue as the one story (the editorial's lines against the editorial
text): a number, a name, a weekday, a date, an interval or a quotation the
issue does not carry cuts the sentence, never softens it. The sign-on, the
contents opener, the Void Opinion introduction and the sign-off are Void's
formulas and are kept. The pass runs on both paths, before a word is
synthesised, and the script is re-validated after any cut; a committed script
that would lose a sentence fails WA-04 ("loses nothing to grounding"), because
a script with an unsourced sentence in it is a script with an unsourced
sentence in it. Issue 32 lost nothing.

The sign-on's dates are pinned to `week_start` and `week_end` by W-17
(`sign_on_line(issue)`, "the week of October twenty-sixth to November first,
two thousand and twenty-six"), which is why W-13 and the pass skip that one
line: it is computed from the issue, not written.

## Validators

Stable IDs in their own namespace (`verify_sections`' W-01..W-10 are the served
page; these are the script). A rundown with any `fail` is **not rendered**.

| | | |
|---|---|---|
| W-01 | every column line exists in its own published column (floor 70 %) | fail |
| W-02 | the firewall: A alone in LEFT, B alone in RIGHT, the host alone in Void's movements, no host in a feature | fail |
| W-03 | **airtime** (words over each reader's rate) within 1.35x between the two columns; warn over 1.20x | fail |
| W-04 | the turn engages both columns, by distinctive vocabulary, in at least sixty words | fail |
| W-05 | the programme's shape: COLD, OPEN, COVER, TOPIC, LEFT, RIGHT, TURN, SECOND, EDITORIAL, CLOSE in order; NUMBERS when the issue carries a bias report; no unknown marker | fail |
| W-06 | a dateline of one short beat INSIDE the cover, between two of its passages; a rest expected | fail / warn |
| W-07 | inside the issue's own band (18-22 for a full issue, floating down to 14-18), measured per voice at the measured rates plus 2.3 minutes of music | fail |
| W-08 | Void's own lines: no borrowed radio furniture, no podcast tells | fail |
| W-09 | a Week in Bias reads no figure the report does not carry, and is **dropped, never invented**, on an issue with no report | fail |
| W-10 | the close asks rather than states | warn |
| W-11 | the contents is four lines, not a rundown | warn |
| W-12 | no quotation marks in spoken copy | warn |
| W-13 | **every voice** outside the columns: every number and every multi-word proper name is in the published issue (the sign-on excepted; W-17 pins it) | fail |
| W-14 | the editorial opens on "This is Void Opinion." and its headline, and every line after it is the published editorial by 90 % overlap: read as written | fail |
| W-15 | the features are the correspondents', in passages of 18-130 words (COVER 3-9, A leads; SECOND 2-7, B leads; the other takes at least one, usually the last; no voice more than three in a row; no question marks: nobody interviews anybody) | fail |
| W-16 | the week opens on the host's "The week in brief." and the correspondents alternate 3-10 items of at most 75 words, a fact each, never more than the issue prints briefs | fail |
| W-17 | Void's fixed lines are exact: the cold open is one or two host lines naming no programme and asking nothing; the sign-on is `sign_on_line(issue)` to the letter; the contents opens on its line; the sign-off ends the close | fail |

Every rule has a planted defect in `tests/test_weekly_script.py`, built from
the newest published issue with a pair. The grounding pass has its own (a
sentence with a name and a sum the issue does not carry is cut, logged with its
reason and product `weekly:TURN`; the columns and the formulas are untouched).

## The band

Decision 6 (CEO 2026-10-02) stands: the band floats with the sourced words,
`target_minutes(issue)`, ceiling 22, floor 14, and the floor is a minimum, never
a target: padding is where unsourced sentences came from. Rev 2 changes the two
numbers under it. `MUSIC_MINUTES` is 2.3 (914 s of programme over 773 s of
speech on Issue 32: the theme, two interludes, the sting and its silences, the
spine, the rest, the stop, the entrance, the outro and the gaps), and
`VOICE_WPM` is measured per voice over a whole script at 0.88 (above). Issue
32, 1,864 sourced words, read almost whole with the editorial entire and the
columns selected, estimates at 15.2 and ran 15:14: inside 14-18 with nothing
said that the issue did not print. `word_budget` still takes the slowest voice
for the ceiling and the fastest for the floor, so the prompt's words land
inside W-07's minutes (WA-05).

## The score, cue by cue

Composed in `weekly_music.py` on `onair_music`'s patches and helpers; shaped,
levelled and measured by `onair_score` exactly as On Air's is (band shape, bed
level -31 LUFS in the voice's gaps, featured -26, interlude -27, the eased duck,
breathing, no tiled loop, calm clock and glare, the phone check). Issue 32's
seed is 3364409128 (`argument:world:2026-10-26`); every cue met the standard
on its first render, no finding.

**The theme** (18.0 s, featured, `render_theme`). Bar 0: the toll on D3 (the
felt bell with a soft electric piano under it), a sub pedal on D2 swelling over
1.2 s, a dark pad opening to 700 Hz over 2 s. Nothing moves. Bars 1-4 over the
cadence Dm Bb Gm A: the half-time drums enter and build (0.5, 0.7, 0.85, 1.0),
the half-time bass (the root held from one, the fifth on three, a pickup on the
and of four), the pendulum keys, and the hook at HALF SPEED on the electric
piano (`HOOK_HALF`: every value doubled, four bars), the bell doubling its fall
(G5 F5 D5) from bar 3; the hook's last note, the tonic, hangs over the
dominant. A 1.8 s dark riser into bar 5: a hit, the pad on Dm held under the
voice, D4 and A4 on the keys, the bass and a sub under it. The sign-on lands
on that downbeat (`THEME_DOWNBEAT_S` 14.29 s), and the open bed crossfades in
under the hold. Measured: 0.44 clock onsets a second, 0.06 % glare, 76 % of its
energy in 40-120 Hz; the downbeat IS its loudest moment (WB-11 asks within 3 dB).

**The beds** (`render_bed`, On Air's arc: pad and bass alone, the pulse
arrives, eight-bar phrases, a dip before each, an ending that thins, rises or
stops). Patterns:

- *open, feature, close*: **half-time**. The kick on one only, a brush on three,
  the shaker on the and of two and of four; the half-time bass; the
  **pendulum** in place of On Air's lilting ostinato (a chord tone on one and
  another on three, swinging left and right, the bell doubling beat one on
  alternate bars); the hook at half speed once a phrase. Progressions
  `open` Dm Bb Gm A or Dm C Bb A; `feature` Dm Bb F A, Dm Gm Bb A or Bb Gm Dm A.
  Measured against On Air's lead bed at the same seed: 0.60-0.67 clock onsets
  a second (On Air 0.6-0.7) and kicks a second at most 0.7 of On Air's (WB-11).
- *tension*: **no drums**. The dominant pedal, A1, in eighths on the sub bass
  (`style="pedal"`), rising in level across the bed; the pad alternating Dm and
  Asus and opening from 650 to 1,100 Hz across the bed; a bell on the fifth
  every other bar. Motion without a bright onset: 0.05 clock onsets a second,
  no kick. The producer ends it on `rise` into the sting (+5 dB on Issue 32,
  capped at the featured level).
- *turn, editorial*: **the slow room**, On Air's Opinion bed: two bars a chord,
  one soft kick a bar and no clock, the walking bass (root held, the fifth on
  four), a sparse bell line, the inverted hook's first three notes once a
  phrase. `turn` runs Bb Gm Dm A or Gm Bb F A; `editorial` is On Air's
  `opinion` set and never lands on i. 0.05-0.07 clock onsets a second: under
  half the open bed's.
- *week*: **the pushed pulse**: the kick on one, the and of two and three, a
  brush on four, the shaker on the and of one and of three; On Air's pulse
  bass; the pendulum; it never thins (momentum). A **breath** after every
  second item: the gap is 2.4 s, the duck releases, and a two-note bell tag
  (`onair_music._bell_tag`) lands 0.6 s after the item's last word while the
  pendulum rests. It ends on **the stop**: a hit (impact, a long bass root,
  the pad released) `STOP_RING_S` 2.6 s before its end, every tail gated, the
  ring to the floor; then 1.6 s of the floor before the entrance. Measured: the
  hit within 3 dB of the bed's loudest moment, the end 30 dB down (WB-11).
- **Accents.** A feature bed carries a **toll** 0.35 s after each dateline's
  last word, in the held 2.1 s beat after it; the pendulum rests from 0.15 s
  before to 1.6 s after. WB-11 renders the same bed with and without the tolls
  and asserts they differ only there (On Air's desk-breath test, applied).

**The interlude** (12.2 s, `render_interlude`): 0.8 s of a dark riser into a
soft hit (the page turned), then three bars of a tune in dotted augmentation
(the hook, its inversion or its answer, every value 1.5x) over a chord triple
(Dm Bb Gm / Dm Gm A; F C Bb / Bb F C; Bb Gm A / Gm Bb A) on the half-time
groove, then a release bar: a single kick and the bass on the tonic, the pad
opening on Dm, the clock gone, the tune's last note ringing. The next voice
speaks 10.1 s in (`INTERLUDE_VOICE_S`, the second beat of the release bar).
`interlude_plan` gives the second interlude the next tune, the next triple and
the other voice (electric piano against bell): Issue 32's are the inverted hook
over Bb F C on the piano, then the hook's answer over Bb Gm A on the bell,
chroma cosine under 0.9 (WB-11). Levelled to -27 LUFS short-term max, 1 dB
under the featured cues, 4 dB over a bed. The bed before it rises to meet it.

**The sting** (4.6 s, `render_sting`, a role of its own in `onair_score`):
a dark riser for 1.3 s into a hit (impact), the toll on D3 with a D4 bell over
it, the bass on D2 and a sub pedal under it, a pad stab on Dm released at once;
no delay; the last 1.4 s cut to the floor. Levelled as a featured cue (its
loudest 3 s at -26). Two rules are the sting's own: `sting-hit` (its loudest
400 ms fall inside its first 2.5 s; it hits, it does not swell) and
`sting-tail` (its last 0.3 s under -55 dBFS; it ends, and nothing fades out of
it into the voice). Both planted in WB-11. Then `GAPS["sting_to_column"]`, 1.4 s
of the floor, and the left column with no music under it.

**The frame.** The argument is dry for the reason rev 1 gave: two people
disagreeing over a bed is a talk show; naked voice with a held pause between
the sides is a courtroom. Rev 2 puts the drama around it instead of under it:
the tension bed and the sting before, and after the right column 6.5 s of rest
in which, 1.2 s after the last word, the turn's slow room swells in from the
floor (the bed's arc opens on the pad alone), so the host's reckoning begins
over music that has returned. WB-02 and WB-04 assert the dry middle and the
frame's timing.

**The entrance** is On Air's `render_entrance`, unchanged: a sub pedal on VI
out of the held silence, the hook in dotted augmentation on the bell over VI iv
V, the tonic held over the dominant, the host speaking on the last note. A
signature is a signature.

**The outro** (18.0 s, `render_outro`): the cadence Dm Bb Gm A with the hook at
half speed on the piano and the bell an octave above it, the half-time drums
(0.8 to 1.0), the pendulum, a riser into bar 5 (`OUTRO_LAND_S` 11.43 s): a hit
and the landing on **D major**, the pad on D held, D4 F#4 A4 D5 on the keys, a
bell arpeggio D5 F#5 A5 D6 ringing in over two seconds, the bass and a sub
pedal under it, the pad falling over 3.5 s to silence. The one resolution in the
programme. Measured (WB-11): the landing's pitch profile carries the major
third where the bars before carried the minor (F# 0.29 against F 0.00), and the
last half second is silence.

**The spectrum drone** (`spectrum_drone`, under NUMBERS only): rev 1's device in
the weekly's patches, a sub pedal whose pitch carries the week's mean lean (D
at the centre, a fifth either way) and whose detuning carries the spread, 6 dB
under the bed level. Issue 32 has no bias report, so it did not play.

**Where it sits.** Everything is On Air's standard (`docs/ON-AIR-CONVERSATION.md`,
"The score"): beds -31 in the gaps and 10 dB under the voice, featured cues
-26, interludes -27, the eased 1.0 s pre-roll, the stop, the held floor at -70
dBFS, the phone check (voice over music by 12 dB in 150 Hz-4 kHz in every
spoken second; Issue 32 measured 16.8), loudnorm to -16 LUFS / -1.5 dBTP. The
music-only reel (`weekly_producer.py --reel`) lays every cue out in running
order with a marks file, beds raised to -27 so they can be heard alone.

## Generation, and the committed path

**Sunday** (`weekly-digest.yml`, 18:07 UTC): `weekly_digest_generator`
builds the issue, then `_produce_argument` asks Gemini once with
`weekly_rundown.SYSTEM` (the grounding sentence, the data clause, the markers
H/A/B, the budget from `word_budget`, the banned phrases) over the published
text, each block wrapped as source data; validates; grounds; re-validates;
regenerates once naming the findings. The grounded script is what renders.
The row carries `audio_voice` host+left+right, `audio_voice_label` "Three
voices", the chapters, `opinion_start_seconds` at the entrance. No fallback:
if The Argument does not render, the Weekly ships without audio.

**Any day** (`render_weekly_audio --week <week_start>`): the committed script
at `data/weekly/scripts/<week_start>.txt` against the published issue in the
deploy tree, no Gemini, no DB; writes the MP3 named by the issue's Sunday
(`<week_end>-pm.mp3`, so a re-render replaces its own file) and the audio
fields back into `weekly.json`, `weekly-issues.json` and
`weekly-archive.json`. The rev 1 script for Issue 26 is kept as record at
`data/weekly/scripts/v1/2026-09-14.txt`; it does not parse as a rev 2
programme (E/L/R read as H/A/B, but the Editor carried the features) and is
not validated by WA-04.

## Rollback

| | |
|---|---|
| `VOID_WEEKLY_AUDIO_FORMAT=0` | parks the audio (no legacy read remains) |
| `DISABLE_AUDIO=1` | no audio at all |

## Ear-test checklist (CEO)

The cold open lands on an image before any music. The toll, the swell, the
half-time drums under the hook slowed down, the hit, and the sign-on on it.
Two correspondents trade the cover, no questions; the dateline, then the toll
in the held beat. The interlude turns the page and the host speaks over its
release. The tension under the framing: no drums, the low pulse, the pad
opening. The sting, then nothing, then a voice alone. The spine. The second
column, dry. The rest, and the slow room returning under the turn. The second
interlude is not the first. The week moves and breathes, a bell in each breath,
and stops dead; the silence; "This is Void Opinion." over the entrance's held
note; the same host reads the column over the slow room. The open question.
The cadence, the hook at half speed, the bell above it, and the one landing on
D major, falling to silence under the promo. Nothing in the score is sharp;
the sub never muddies a word on a phone. Nine chapters in the player.

---

# Rev 1 (2026-09-20 to 2026-11-08), kept as the record

## What it replaced

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

## The rev 1 show

```
theme (Sunday cue, 10 s)
OPEN         E   the week in one image. Not a headline list.
CONTENTS     E   "Inside this week." Four lines.                 [bed]
COVER        E   the lead feature
  DATELINE   E   "Tuesday. Thirteen sources."  + a held beat
COVER        E   the rest of it
transition
TOPIC        E   names the story once, then gets out of the way
LEFT         L   the left column, selected, DRY
  (the spine)    2,400 ms of nothing
RIGHT        R   the right column, selected, DRY
REST             held pause
TURN         E   what each side leaves out. Both, never one.
transition
SECOND       E   feature 2
DEPARTMENT   E   Technology or Sports & Culture
break (9 s)
NUMBERS      E   The Week in Bias, read as measurement
                 the spectrum sonified beneath it, -40 dBFS
EDITORIAL    E   the argued column                               [bed returns]
CLOSE        E   the question the week left open
outro (14 s, falling to TRUE silence)
```

Cast: **E** the Editor `bm_lewis` (172 wpm), **L** `am_michael` (160), **R**
`af_heart` (162), house pace 0.92, the bench rate-matched within two words a
minute, the Editor panned centre and the bench +-0.16. Sound: five WAVs from
`generate_assets.py` (`weekly_theme`, `weekly_transition`, `weekly_break`,
`weekly_bed`, `weekly_outro`: the On Air motif at half tempo opening on the
suspended fourth), `radio_room_tone.wav` reused, the bed looped with no
crossfade, the sonified spectrum under the numbers. Reuse of
`radio_producer` for synthesis, the ffmpeg voice chain, the RMS duck,
`loudnorm_two_pass`, `encode_mp3`, ID3 chapters and the sidecar.

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
counting shared stems and starts counting *specific* ones. Rev 2 keeps it.

## The fallback is gone (2026-09-21)

`_produce_argument` used to return `None` on any of six failures and the caller
silently shipped the legacy two-voice edge-tts read in its place. The flaw was
that the substitution was **silent**. Every scheduled run since the format
shipped had taken that path, so a format that had never once produced a
scheduled episode looked like a format that worked. The published row said
"Three voices" and `kokoro:bm_lewis+am_michael+af_heart` over a file measuring
24000 Hz, 1 channel, 96 kb/s, 1002 s, -20.5 LUFS, while claiming 1349.7 s.

**Now:** if The Argument does not render, the run raises and the Weekly ships
without audio. `VOID_WEEKLY_AUDIO_FORMAT=0` is the only remaining route, and it
**parks** audio rather than substituting for it. `tests/test_weekly_audio_served.py`
probes the **artifact**: duration against the row, stereo, loudness within 1 LU
of -16, a chapters sidecar, a Kokoro cast.

## The word budget (decision 6, 2026-10-02)

W-07's band is sized to the issue. It used to be a fixed 18-22, while
grounding and the source check shrink the material every week: the corrected
Issue 26 script ran 17.6 minutes and was refused for being short, which left
padding or withdrawal, and padding is where the unsourced sentences came from.
`weekly_script.target_minutes(issue)` takes the published issue's sourced
words, reads 55 % of them at the blended rate plus the music, and centres a
four-minute band there, clamped to a ceiling of 22 and a floor of 14.
`word_budget()` owns the minutes-to-words conversion, beside the constants
W-07 measures with, and its two edges take opposite rates: the ceiling assumes
the slowest voice and the floor the fastest. The prompt names the `BORROWED`
list, because a rule the writer cannot see is not a rule.

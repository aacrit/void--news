# On Air: the newsroom

Last updated: 2026-11-08 (rev 5, after the CEO heard rev 4: two voices in
all; the Opinion's voice, `af_aoede`, becomes the anchor and reads Void
Opinion as well as the news; the second anchor is male, `am_puck`, chosen on
a slated audition of all thirteen Kokoro men; the Opinion is introduced and
titled "Void Opinion" with an entrance of its own and a bed of its own; more
bass across the score. Rev 4, 2026-11-07, after the CEO's fourth ear test: the
question-and-answer format read as robotic, so On Air is a two-anchor
newsroom again, passages and handovers with no interviewing; `af_bella`
read as artificial and is retired, `bf_emma` is the second anchor and
`af_aoede` reads the Opinion, which is read whole and has its own time.
Rev 3: the score composed from scratch in `onair_music.py`. Rev 2: three
voices, a studio floor. Rev 1 replaced the 2026-09-18 bulletin;
`docs/ON-AIR-RADIO.md` stays as its record and `VOID_ONAIR_FORMAT=rundown`
restores it. The file keeps its name; the format is `conversation` in the
switch)

On Air is the daily programme of Void News: ten to twelve minutes, at a calm pace (rev 5b). Two
anchors trade the day's stories in passages, the way a public-radio
newsroom does: A leads the lead story and B takes its reaction and its
coverage; B leads the second story and A takes its coverage; they alternate
on the desk. Nobody asks anybody anything. Then the news stops, the Void
Opinion entrance plays, and A introduces Void Opinion and reads it as
written, passage by passage. A close. Two voices in all. Generated once a
day by the pipeline (step 7d) and served as one MP3 with chapters.

**The firewall is the music and the words, not the voice** (rev 5). Since
the same anchor reads the news and the Opinion, nothing about the voice
tells the listener the argument has begun. Three things do: the news bed
stops dead and the show holds a silence; the entrance, a cue with its own
register and rhythm, plays in the clear; and A's first words are "This is
Void Opinion." with the lens and the headline. Under the Opinion runs a bed
of its own, plainly the same show and plainly not the news. C-14 fails a
script whose Opinion does not open on Void Opinion.

This document is the positive definition of the show. The code that enforces it:

| What | Where |
|---|---|
| The script: grammar, parser, validators C-01..C-15, the grounding pass, the prompt, the template edition | `pipeline/briefing/onair_show.py` |
| The score's standard: loudness (BS.1770), band shape, levels, the rise, the duck, the checks | `pipeline/briefing/onair_score.py` |
| The music itself: patches, harmony, the hook, the arrangement of every cue, stereo | `pipeline/briefing/onair_music.py` |
| Production: Kokoro, the voice chain, the timeline, score placement, mix, master, chapters, sidecars | `pipeline/briefing/onair_producer.py` |
| Pipeline wiring (`_produce_onair_edition`), the format switch, the carry rule | `pipeline/main.py` |
| Operating it offline (`--radio-only --script-file --render-dir`, `--revoice`, `--no-opinion`) | `pipeline/refresh_brief.py` |
| Gate | `tests/test_onair_show.py` (fixtures `tests/fixtures/onair_show_2026-11-07.txt`, `onair_stories_2026-11-07.json`) |
| Served-output gates | `scripts/verify_audio.py` A-01..A-07, `tests/test_onair_sidecar.py` S-01..S-06 (unchanged) |

## Running order

```
COLD        A, one or two sentences in the clear over room tone: the lead's hardest fact
theme       14.0 s, featured: four bars into a downbeat, and the sign-on lands ON that downbeat
            (S.THEME_DOWNBEAT_S); the pad holds under the voice while the lead bed crossfades in
TITLE       A: "From Void News, this is On Air. It's <day>."  B: today, in one or two sentences
                                                                  [bed: lead, from under the framing]
LEAD        A leads; four to nine passages of 18-125 words, 380-760 words; B takes one to three,
            including the last (the coverage); no voice reads more than three in a row
                                                                  [bed under the first two passages,
                                                                   one visit in the middle of a long
                                                                   lead, back for the coverage]
interlude   8.6 s, three bars, heard in the clear (rev 5c; the 3.6 s page-turn before it): a laid-back
            groove (a soft kick on one and the "and" of two, a brush on two and four, a shaker on two
            off-beats, a round bass, a warm pad) under two bars of a tune drawn from the hook over a
            chord pair, then a release bar on the tonic. Levelled to -27 LUFS short-term max
            (S.INTERLUDE_LUFS), 1 dB under the title, 4 dB over a bed; the bed before it has risen over
            its last 10 s to meet it. B starts 6.4 s in, over the release (S.INTERLUDE_VOICE_S)
SECOND      B leads; three to seven passages, 260-520 words; A takes one or two, including the coverage
                                                                  [bed: second, the same shape, fading in
                                                                   under the interlude's release]
interlude   another melody, another chord pair, the other voice (interlude_plan: two in one episode
            never share any of the three)
DESK        A: "The rest of the desk."  ranks 3-10, two or three sentences each, alternating;
            0.9 s between items, and after items two, four and six a BREATH of 2.4 s in which the duck
            lets the bed up (0.6 s release, 1.0 s pre-roll, a second at full) and a two-note bell tag
            answers while the ostinato rests (rev 5c)
                                                                  [bed: desk, the relaxed pulse,
                                                                   throughout, and it STOPS: a hit 0.5 s
                                                                   after the desk's last word, the ring,
                                                                   2.6 s]
silence     1.6 s of the -70 dBFS floor; no music, no voice
entrance    11.4 s, featured, "Void Opinion": a sub pedal on VI swells from the silence, then the
            hook in dotted augmentation on a bell over VI iv V, the tonic held over the dominant;
            no pulse, no riser. A's introduction starts 9.8 s in, on the held last note
OPINION     A: "This is Void Opinion. Through a <lens> lens today. <headline>"  then A reads the
            Opinion's paragraphs as written: two to six passages, 150-380 words
                                                                  [bed: opinion, the slow room, from
                                                                   under A's introduction, under the
                                                                   first two passages and the last]
CLOSE       A: "That's On Air from Void News. <one fact to carry> Every source, every story, at Void News."
outro       15.0 s, featured: the cycle in full, a riser, the landing on D major (the lift), the pad
            falling to silence; the house promo rides it (unchanged)
```

Chapters: `Today` (0 s, kind `headlines`, covers the cold open and the title),
one `story` chapter per conversation (rank, cluster id, permalink when
archived; it starts at the interlude before it), `The desk` (kind `briefs`), `Void
Opinion` (kind `opinion`, its headline as the subtitle, starts at the
entrance music; `opinion_start_seconds` keeps that meaning), `Also from
Void` (the promo). The page's own labels (the `/onair` rail's "Opinion"
jump) are unchanged pending the CEO's word; the chapter list reads the
chapter title from the data. `news_start_seconds` is where
the lead's first passage begins.

**The Opinion is spoken only when it was written for this edition.** A
carried-forward opinion belongs to another day's stories, so the show ships
without the segment (no entrance, no Opinion chapter) rather than read it
as today's. When it is spoken, it is the brief's written opinion
(`opinion_text`), read whole by A: its sentences in their order, digits
spoken as words, nothing added or cut. The grounding pass reads the
Opinion's passages against that text, so the show cannot add a claim the
Opinion did not make. The first line is fixed: `This is Void Opinion.
Through a pragmatic lens today.` (the lens from `opinion_lean`), then the
headline (C-14). At
two to three hundred words it runs about a minute and a half, after its own
entrance music and under its own bed.

## The conversation

It has to sound like people talking, not a bulletin read in turns (CEO,
first ear test). The asker may open with one short bridge clause that picks up
the last answer before the question ("So the Senate flipped. What does that
mean for January?"); now and then the asker's line is a short statement from
the story that the other voice picks up, so an exchange is any asker line
followed by the other voice, and at least half of the asker's lines are
questions. Contractions where a person would use them. An asker's line is at
most 34 words; an answer is 14 to 120 words, two to five sentences, from its
own story only, never a question, and may end by handing back in a few
words. The voices are never named, never greet or thank anyone, never react. Each story ends on the coverage: A asks how the outlets
are covering it or where they sit; B answers from the Divergence points and
the Coverage line, naming outlets as the points name them.

**The Coverage line** is Void's own angle and the one number the show adds:
"Of the sixty outlets Void placed on this story, twenty-four sit left of
centre, twenty at the centre and sixteen right of it." One vote per outlet
(the card's `lean_buckets`), computed by `coverage_line`, handed to the model
as data and appended to the story's evidence so the grounding pass can
confirm it. A roster under five outlets gives no line.

| Id | Rule | Level |
|---|---|---|
| C-00 | Six segments, in order, once each; every spoken line is A or B | fail |
| C-01 | The sign-on is Void's exact line and names the day; the close is one A line, Void's prefix and tag | fail |
| C-02 | No quotation marks; reported speech only (stripped deterministically after the retry, then re-validated) | fail |
| C-03 | Numbers are words (the engine spells them anyway) | warn |
| C-04 | No a.m./p.m. clock forms, no print datelines | fail |
| C-05 | No borrowed or AI-podcast phrase, no significance word (the radio list, `BANNED_PHRASES`), no host named or thanked, no identifier spoken | fail |
| C-06 | Word budgets per segment and in all (`WORD_BUDGETS`, `TOTAL_BUDGET`), +-25 % | fail |
| C-07 | The shape: the leader opens (A in LEAD, B in SECOND), four to eight passages in LEAD and three to six in SECOND, each 18-125 words; the other anchor takes one to three (LEAD) or one or two (SECOND), usually the last; no voice reads more than three passages in a row; at most one question mark in a segment (the anchors never interview each other); the cold open is one A line and a fact; the TITLE's lineup is B's | fail |
| C-08 | The desk opens on "The rest of the desk.", six to eight items (ranks 3-10), each at most 60 words, a fact not a question, never more items than stories | fail |
| C-09 | Over the news segments, each of A and B carries 35-65 % of the words (the Opinion is A's alone and is not counted, or it would push A over) | fail |
| C-10 | Sentences under twenty-four words | warn |
| C-11 | Grounded attribution (the radio's R-14): an attributed clause keeps 0.6 of the story's words for that speaker | fail |
| C-12 | No unattributed statement of law (R-15) | fail |
| C-13 | SAY respellings are lowercase syllables | warn |
| C-14 | The Opinion opens with A on `This is Void Opinion.` and names its lens; every passage after it is A's; two to six passages of 28-140 words | fail |
| C-00 | Two voices: a line from any speaker but A or B (`C:` included) fails anywhere; B never speaks in OPINION; an OPINION segment only on a day with a written opinion, and always on such a day | fail |
| C-15 | A chapter title is at most seven words, no digits | warn |

Then the grounding pass (`ground_show`, `editorial/derived_grounding`): every
line is read against its own story (LEAD and COLD against rank 1, SECOND
against rank 2, each desk item against its rank, the Opinion's passages against the
Opinion text, the framing and the close against the day), and a sentence the
story does not carry is cut (the Opinion's passages against the Opinion text). An answer cut whole takes the asker's line that
set it up with it; an asker's line left dangling at the end goes; same-voice
neighbours left by a cut are merged, so the voices still alternate. `grounding_ran.onair` is True only when the pass completed.

Ranks are bound from the feed by position (LEAD is rank 1, SECOND rank 2,
the desk's first item rank 3); the model never copies an id.

## Generation, and what happens when no model answers

One Gemini flash request (flash-lite when flash refuses: overload, quota,
and since 2026-11-07 a 504 deadline), one repair request with the failures
named, then the deterministic repairs for C-02 and C-05. When nothing
passes, **the template edition** (`template_show`): the stories' own first
sentences, consensus and divergence points and the coverage line, in the
show's shape, with fixed questions ("What do the outlets agree on?", "Where
does the coverage split?", "How does the coverage lean?"). It is plain, it is
grounded by construction, it is TODAY'S, and it is labelled (`generator`
carries `onair:template:kokoro`). The show never falls to another engine or
to another day's script: if Kokoro does not synthesise, the previous episode
is carried, as the brief carries its audio when there is none.

## Voices

Kokoro-82M, and only Kokoro (`engines=[KokoroEngine()]`; edge-tts is not in
this chain). Casting, rev 5 (2026-11-08), overridable with
`VOID_KOKORO_VOICE_A/B` (there is no C):

| Role | Voice | Why |
|---|---|---|
| A, the anchor | `af_aoede` | the CEO's choice (rev 5): rev 4's Opinion voice becomes the anchor. Cold open, sign-on, the lead, the second story's coverage, half the desk, Void Opinion read whole, the close |
| B, the second anchor | `am_puck` | the CEO asked for a male second anchor; the best of Kokoro's men on the evidence below |

**The male audition (2026-11-08).** Every Kokoro `am_*` and `bm_*` voice
read the same B passage (the Kyiv second story's first two passages: 131
words, names, numbers, a long sentence) at 0.95 through the real voice
chain, slated, one pack (`onair-male-voice-audition.mp3`, sent to the CEO).
Grades are the Kokoro repo's own `VOICES.md` (target quality / training
duration / overall). Measured: pace; median pitch; pitch range (10th to
90th percentile, semitones; wider reads less flat); frame-to-frame pitch
motion; clicks (sample jumps far above the line's norm); share of energy
over 6 kHz after the chain (buzz).

| Voice | Grade | wpm | f0 Hz | range st | motion | clicks | >6 kHz | Verdict |
|---|---|---|---|---|---|---|---|---|
| am_adam | F+ (D, hours) | 162 | 120 | 10.9 | 0.28 | 0 | 0.2 % | lowest grade on the roster |
| am_echo | D (C, minutes) | 175 | 110 | 8.2 | 0.25 | 16 | 0.8 % | artefacts |
| am_eric | D (C, minutes) | 186 | 154 | 8.1 | 0.33 | 0 | 0.1 % | thin training |
| am_fenrir | C+ (B, hours) | 186 | 130 | 8.2 | 0.26 | 0 | 0.3 % | **heard and retired by the CEO** (rev 2) |
| am_liam | D (C, minutes) | 183 | 126 | 9.0 | 0.28 | 0 | 0.5 % | thin training |
| am_michael | C+ (B, hours) | 138 | 118 | 7.7 | 0.31 | 10 | 1.0 % | **heard and retired by the CEO** (rev 1: robotic); artefacts |
| am_onyx | D (C, minutes) | 176 | 94 | 6.4 | 0.19 | 0 | 0.1 % | thin training |
| **am_puck** | **C+ (B, hours)** | 192 | 107 | 6.6 | 0.19 | 0 | 0.3 % | **chosen**: the best grade not already retired, trained on hours, clean |
| am_santa | D- (C, minutes) | 157 | 158 | 10.9 | 0.53 | 0 | 0.3 % | a character voice |
| bm_daniel | D (C, minutes) | 179 | 121 | 5.3 | 0.28 | 0 | 0.2 % | flattest; thin training |
| bm_fable | C (B, minutes) | 173 | 119 | 8.5 | 0.25 | 2,422 | 4.9 % | buzz and clicks after the chain |
| bm_george | C (B, minutes) | 147 | 137 | 5.5 | 0.30 | 0 | 0.3 % | runner-up: clean, British, but flat and trained on minutes |
| bm_lewis | D+ (C, hours) | 142 | 113 | 8.4 | 0.41 | 0 | 0.2 % | the Weekly's voice; lower grade |
| *af_aoede (A, reference)* | C+ | 170 | 174 | 6.6 | 0.20 | 0 | 0.1 % | |

`am_puck` and `af_aoede` sit about nine semitones apart (107 against 174
Hz), so the handover is audible without a name, and share a pitch range
(6.6 st each), so neither sounds more animated than the other. Puck reads
about 13 % faster than aoede at the house pace; that is left as it is (one
house pace, CEO 2026-09-19). Honest caveat: no Kokoro man is graded above
C+, and the CEO heard the other two C+ men as synthetic. Puck was the
anchor of the 2026-09-18 bulletin and was not retired, but it has not been
heard over a full conversation episode before this one; `bm_george` is the
fallback if it does not hold up (`VOID_KOKORO_VOICE_B=bm_george`).

One house pace, on both; no voice is stretched on its own. **0.88 since
CEO 2026-11-08** ("a little longer, more space for calm paced content"), from
0.95 (CEO 2026-09-19). The audition above was read at 0.95.

**Calm pace (rev 5b, 2026-11-08).** Three things made the show longer, and
none of them is padding: the voices at 0.88; every pause about 40 % longer
(handover 1.0 s, 1.7 s under a bed; the same voice 0.65 s; desk items 0.9 s;
1.3 s between "This is Void Opinion ... <headline>" and the argument; 1.0 s
between its paragraphs); and more of what the stories carry, chiefly a desk
of eight stories in two or three sentences each instead of six in one or
two. The first calm edition ran 10:35 against rev 5's 8:54.

**The voice chain** (`voice_chain`, the film studio's A13/A38 applied per
line, in numpy at 48 kHz): trim the silence (60 ms kept), a light spectral
gate (each bin's 15th-percentile magnitude is its noise profile; a bin under
2.5 times it is lowered 14 dB, the gain smoothed over five frames; speech is
untouched, the residue between words goes down), level the line to -20 LUFS
integrated, the house warmth (+2.5 dB bell at 200 Hz, Q 1.2; -2.5 dB
high shelf with its half-gain point at 6 kHz, zero-phase), re-level, and a
soft knee over -4 dBFS that touches only a line whose crest would reach the
ceiling. Then a constant-power pan, two positions: A 7 % left, B 7 % right. The
old ffmpeg chain (80 Hz high-pass, +2.5 dB at 4 kHz, de-esser, 3:1) brightened
the voice; this does the opposite, on the founder's note that the synthetic
voices had too much treble and wanted bass.

## The score

Composed from scratch for rev 3 (`onair_music.py`), after the CEO heard rev 2
and did not like the tunes. It is written, not generated: a key, a tempo, a
chord cycle, a hook, an ostinato, patches, an arrangement per cue. The day's
seed chooses only the chord cycle per segment and which bars carry which
layers, so the bed moves every day and the hook is the same every day.

**Rev 5 (2026-11-08): the music is the firewall.** The same voice now reads
the news and the Opinion, so the move between them can no longer be a
change of voice. It is three things the ear cannot miss, each measured by
the gate: the desk STOPS (no rise, a hit, the ring, nothing); a silence is
HELD (1.6 s of the -70 dBFS floor, no music, no voice); and "Void Opinion"
ENTERS on a cue that shares the show's seven notes and nothing else of its
manner. Then the Opinion's bed is the same show in another room. And the
whole score carries more bass where a speaker can feel it.

**Rev 5c (2026-11-08, CEO: "add cool calming beats and tunes between
stories; ensure score is also soothing").** Two things, both measured.

*Soothing, in numbers.* Two measures, each aimed at something the ear hears
as harsh, both gated on every cue (`check_cue`, `calm-clock` and
`calm-glare`). The CLOCK is counted (`clock_density`: short, bright onsets a
second in 2-6 kHz, where ticks, rims and clicks live; since rev 5c an onset
must lift the band 6 dB over the 150 ms before it and have fallen as far
again within 200 ms, so a bell or a key that rings on is not a clock and a
room's floor is not one either). The GLARE band is weighed (`glare_share`:
the share of the energy over 100 Hz that lies above 3 kHz, where the ticks
lived and the keys and bells do not reach). Ceilings: a bed or an interlude
at most 1.0 clock onsets a second (`CALM_CLOCK_MAX`; a shaker on two
off-beats a bar is 0.7 at 84 bpm), a featured cue 1.4; glare at most 0.6 %
for a bed, 1.5 % for an interlude (a bell melody is allowed), 2 % for a
featured cue (`CALM_GLARE_MAX_SHARE`). Rev 5 could not have passed them: its
lead, second and desk beds measured 1.0 to 1.3 clock onsets a second (the
close 0.8) and its beds 0.45 to 1.4 % glare (the lead and the desk over the
ceiling), its theme 1.1 a second. Rev 5c, same seed: the news beds 0.6 to
0.7 a second and 0.08 to 0.19 %, the theme 0.4, the outro 0.4, the
Opinion's bed 0.03 a second and 0.03 %, the interludes 0.0 to 0.5 and 0.07
to 0.15 %. The spectral centroid fell with
them (beds 117 to 175 Hz against 167 to 212; the theme 336 against 402; the
outro 394 against 439) and the breathing and the bass share held (beds 14
to 23 dB, 83 to 92 % in 40-120 Hz). The music's level in the phone band
(150 Hz to 4 kHz) fell 0.1 to 2.6 dB on four beds and rose 0.2 dB under the
Opinion, so the phone margin is as wide or wider everywhere. The gate
plants rev 5's tick train on a calm bed (caught on both counts) and a pair
of bright open hats on two off-beats (the count passes, the glare catches
it), so the second measure is not redundant.

What was softened to get there, every patch and pattern: the kick is a 110
to 44 Hz sweep with a 6 ms rise and a 700-2200 Hz KNOCK at a tenth of its
body in place of the 4 ms click (a phone still hears the beat; nothing of it
reaches the clock's band); the tick is gone and the clock is a SHAKER, noise
in 1.3-3.0 kHz with a 12 ms rise, an octave under the tick and slower, on
two off-beats a bar instead of four; the rim is gone and the backbeat is a
BRUSH, noise in 400-1800 Hz with an 8 ms rise; the bass pluck is rounder
(the saw's sweep 260 to 100 Hz and a third quieter) and the eighth-note
pulse under the news is a held root on one and three with a short pickup
on the "and" of four; the desk's four-on-the-floor is a relaxed PULSE (kick
on one and three, a soft pickup on the "and" of four, the brush, the shaker
on two off-beats; the bass walks root, root, root, fifth and carries the
motion the ticks used to); the ostinato has a LILT, five notes a bar on the
beats and the "and" of three instead of eight, and rests one more under a
conversation half the time; the electric piano is lowpassed at 2.6 kHz with
a softer, slower bark (3 kHz and a brighter 30 ms attack before); the bell
is struck with felt, a 24 dB/oct lowpass at 2.4 kHz and a smaller index;
the pad opens to 900 Hz under the news (1100 before) over a 1.0 s attack
(0.6) and breathes at 0.06 Hz; the sidechain leans 3 dB over 340 ms instead
of ducking 5 dB over 220; the rooms are longer and darker (keys 2.4 s, pads
3.0 s, the tails lowpassed at 2.8 kHz); the riser is dark (200 Hz to 2.2
kHz) and at half its level; the off-beats swing at 58 %; fills come less
often (0.35 a phrase against 0.6). Nothing of the identity moved: D minor,
84 beats a minute
(`S.THEME_DOWNBEAT_S` and every bar length unchanged), the hook, the cycle,
the entrance and the stop as rev 5 wrote them.

*The interlude* (`render_interlude`, `INTERLUDE_S` 8.6 s, three bars; the
page-turn was 3.6 s of riser, downbeat and three notes, deliberately never
louder than the bed; this is heard for itself), bar by bar:

1. The groove is there from the downbeat (the bed before it has risen to
   meet it, so nothing is cut off): a soft kick on one and the "and" of
   two, a brush on two and four, a shaker on the "and" of two and of four, a
   round bass on the root and the fifth, a warm pad (filter to 800 Hz)
   swelling in over the first beat; and the melody's first bar on the day's
   voice.
2. The chord pair's second chord; the melody's second bar.
3. The release: a single kick and the bass land on the tonic, the pad opens
   on Dm and holds, the shaker and the brush are gone, the melody's last
   note rings into the delay. The next anchor speaks over this bar, 6.4 s
   in (`INTERLUDE_VOICE_S`, the second beat), once the landing has been
   heard, and the next bed fades in under it.

A breath, not a jingle: no riser, no impact, no ostinato, nothing bright.
The melody is one of three fragments drawn from the hook, each carrying the
chord pairs it is written over (`INTERLUDE_FRAGMENTS`): the hook itself over
Dm Bb or Dm Gm; the inverted hook over F C or Bb C; the hook's answer
(`HOOK_ANSWER`, the same fall from the top of the hook's range, landing on
the fifth) over Bb F or Gm F. The day's seed picks the first interlude's
fragment, pair and voice (electric piano or bell); the second interlude
takes the next of each (`interlude_plan`), so two in one episode never
share a melody, a chord pair or a voice, and their pitch-class profiles
differ (chroma cosine 0.43 to 0.69 on the seeds tried; the gate asks for
under 0.9). Level: a role of its own, `INTERLUDE_LUFS` -27 short-term max,
1 dB under the featured ceiling so the title and the outro stay the loudest
music in the show, 4 dB over the bed's resting level so it surfaces; never
silent (integrated within 6 dB of that, `interlude-silent`). The bed before
it rises as before, now capped at the interlude's level plus 1 dB (the rise
into the outro keeps the featured cap). The page-turn's own rule, never
louder than the bed it led into, is retired with it.

*The desk's breaths.* Eight items at 0.9 s apart never let the duck up
(it holds across any gap under 1.2 s), so rev 5's desk bed was never heard
between items. After every second item that is not the last (items two,
four and six of eight; `DESK_BREATH_EVERY`), the gap is `desk_breath` 2.4 s:
the duck releases over 0.6 s, is fully up for a second, and eases back
down over the 1.0 s pre-roll. The producer hands the desk bed those moments
as `accents` (0.6 s after the item's last word, `DESK_BREATH_TAG_S`), and
in each the ostinato rests (0.15 s before to 1.2 s after, `BREATH_REST`)
and a two-note bell tag from the bar's chord answers. The breath draws
nothing from the day's generator, so the same seed rendered with and
without its breaths differs only there (that is how the gate tests it). An
accent that would fall after the stop's hit is not played. The other desk
gaps stay 0.9 s and keep the duck down: the desk still moves.

*What it costs.* Against rev 5b's timeline, each interlude puts the next
voice 3.15 s later than the page-turn did (6.4 s in against 3.25 s), and
each breath adds 1.5 s: about 10.8 s on an eight-item episode, so the
10:35 calm edition would run about 10:46. A-04's ceiling is 14 minutes.

**The writing.** D minor at 84 beats a minute. The cycle is i VI III VII
(Dm Bb F C), the cinematic cadence, with alternates per segment (i VI iv V).
The hook is two bars on electric piano that fall to the tonic: D5 C5 A4 F4,
G4 F4 D4. Under it an ostinato of chord tones in the fourth and fifth
octaves with a lilt (five notes a bar since rev 5c), a round bass on the
chord root in the sub, and a pad voiced from the third octave up. The outro
lands on D major, the bell doubling the hook's second statement an octave
up on the way.

**The Opinion's harmony** (`PROGRESSIONS["opinion"]`) never lands on i: it
starts on VI and moves VI iv III V, VI III iv V or iv VI III V, two bars a
chord (`OPINION_BARS_PER_CHORD`), so the harmonic rhythm is half the news's.
The news is home; the Opinion is the argument; the tonic is only ever the
hook's hanging note.

**The entrance, bar by bar** (`render_entrance`, 11.4 s, `ENTRANCE_S`,
four bars; `ENTRANCE_HARMONY` Bb Bb Gm Asus):

1. Out of the held silence a sub pedal on Bb (VI) swells in over 1.5 s, its
   octave with it, under a warm Bb pad (filter to 800 Hz, a 2 s attack).
   Nothing else: the ground returns alone.
2. The hook begins on the bell, in dotted augmentation (`HOOK_AUGMENTED`,
   every value 1.5x: D5 held three beats, C5, A4, F4), over VI, where the
   tonic is the third of the chord: a new colour on the same note.
3. The pedal moves to G (iv); the hook continues (G4, F4).
4. The pedal moves to A (V) under a sus pad, and the hook's last note, the
   tonic D, is held over the dominant: unresolved. A speaks here
   (`ENTRANCE_VOICE_S`, 9.8 s in, once the note has landed), and the Opinion's
   bed enters under the voice on VI: a deceptive resolution, not where the
   news goes.

What it is not: no kick, no tick, no rim, no riser, no impact, no ostinato,
the hook not at tempo. Those are the news. Measured (`tests/test_onair_show.py`,
`score_rev5`): it swells from silence (its first second at least 6 dB under
its loudest 400 ms); it carries under half the theme's clock onsets; its
third-octave spectrum is far from the theme's (cosine 0.77 against rev 4's
0.96) and the page-turn's (0.57).

**The stop** (`render_bed(..., ending="stop")`, `STOP_RING_S` 2.6 s). The
desk bed's last downbeat is a hit (impact, a long bass root, the pad
released); every other tail is gated at that beat; the ring decays to the
floor by the bed's end; the exit fade is the ring itself. The composition is
shifted so the hit falls exactly 2.6 s before the end (the first part bar is
pad alone, under the entry fade). The producer's `bed_ending` reads it from
the timeline: a bed the entrance follows within 3 s stops; one a page-turn
or the outro follows within 2.5 s rises; the rest go out. Measured: the hit
within 3 dB of the bed's loudest moment, 5 dB down 1.5 s later, 30 dB down
at the end, and nothing after the ring.

**The Opinion's bed** (`segment == "opinion"`): one soft kick a bar and NO
clock (no ticks, no rims); the bass walks root and fifth in half notes
(`_bassline(walk=True)`, the fifth placed in the sub, 40 to 90 Hz) instead
of eighths; a sparse bell line, one note in two beats, in place of the
ostinato, with the inverted hook's first three notes on the bell once a
phrase; the pad warmer and slower (filter to 800 Hz, a 1.1 s attack);
longer rooms. Measured against the news beds of the same day: under 60 % of
their clock onsets a second (0.5 to 0.7 against 1.5 or more, on every seed
and render order tried), and a pitch-class profile further from their
centroid than they are from each other (0.80 against 0.99).

**The patches**, all synthesised (rev 5c values): `ep` is a two-operator FM
electric piano (a 1:1 modulator whose index falls with the note, a 14:1
modulator for a soft 12 ms attack, a 2.6 kHz lowpass, a 1.6 s release)
through a dotted-eighth ping-pong delay; `bell` is a 3.5:1 FM glass with a
second carrier 4 cents off, a 24 dB/oct lowpass at 2.4 kHz and a 2.8 s
release, the Opinion's register, the outro's upper voice, the desk's breath
and one interlude's melody in two; `pad` is six detuned saws, three a side,
through a 24 dB/oct lowpass that opens from 400 to 900 Hz over the attack
(800 under the Opinion and the interlude), breathing slowly, and opening 100
Hz further in each later phrase of a news bed; `bass` is a sub sine with its
octave at -9 dB (rev 5) under a round plucked saw whose cutoff falls 260 to
100 Hz; `sub_pedal` (rev 5) is the held sub with its octave, the entrance's
floor; `kick` is a 110 to 44 Hz sweep with a 6 ms rise and a 700-2200 Hz
knock a tenth of its body, so a phone hears the beat and nothing in it is
sharp; `shaker` (1.3-3.0 kHz, a 12 ms rise) and `brush` (400-1800 Hz, an 8
ms rise) are the clock and the backbeat; `riser` is dark noise rising into
a downbeat, at half its old level; `impact` is the downbeat it lands on.
Pads and bass lean 2 to 3 dB on every kick (`sidechain`, recovering over 340
ms). Two decorrelated rooms, one a side (`reverb`), their tails lowpassed at
2.8 kHz. Stereo throughout: keys alternate left and right by note, the pad
is wide, kick and bass centred.

**The bass** (rev 5, CEO: "a little more bass"). It is in the sub and bass
register, not the low-mids: the roots sit at 49 to 87 Hz and their octaves
at 98 to 175 Hz, and the band shape's low-pass moved from 100 to 130 Hz
(`SUB_BASS_HZ`) so a bass note keeps the octave a small speaker can
reproduce of it. The bass bus is up (0.72 to 0.82 under the conversations,
0.85 to 0.95 on the desk), the kick decays longer and sweeps to 42 Hz, and
the outro holds a sub pedal under its landing. In numbers, at the production
level: the share of a bed's energy in 40 to 120 Hz rose from 0.72-0.80 to
0.83-0.86, the theme's from 0.51 to 0.60, the entrance's from 0.66 to 0.82;
the 150-400 Hz share stayed at 0.02-0.03 (limit 0.10); the music's level in
the phone band (150 Hz-4 kHz) FELL 1.0 to 2.4 dB on every bed, so the phone
margin widened by that much. 130 to 400 Hz is still a hole by design: the
voice's fundamentals live there.

**The drums** (rev 5c). A slow backbeat under the conversations, the theme
and the outro (kick on one and three, a brush on two and four, the shaker
on the "and" of two and of four, open on the last), the relaxed pulse on
the desk (kick on one and three with a soft pickup on the "and" of four,
the same brush and shaker; the bass carries the motion), the groove in an
interlude (kick on one and the "and" of two, brush, shaker), one soft kick
a bar and no clock under the Opinion, a bar dropped now and then so the
pulse breathes. Off-beats swing (58 %), every hit and note carries a few
milliseconds of human jitter and a little velocity variance, so no two bars
land alike.

**The arc** (`_arc`, CEO: "extremely dynamic and natural"). A bed enters on
pad and bass alone; the pulse arrives in the second bar and builds across
the eight-bar phrase; the pad swells across the phrase and opens further in
each later phrase; from the second phrase a bell answers the ostinato; a dip
and a shaker fill come before some new phrases (half as often since rev
5c); the ostinato and the hook come and go by the seed. A bed ends one of
three ways: `out` (the drums leave two bars early and the keys sit back:
the conversation takes over), `rise` (a fill and everything leaning in, for
the interlude or the outro it hands over to) or `stop` (the desk before the
Opinion, above); the producer picks the ending from the timeline
(`bed_ending`). The desk never thins: momentum.

**Where it sits.** Lighter than rev 2 (CEO: it overpowered): -31 LUFS in the
voice's gaps, 10 dB down under the voice, and it RISES: a bed that leads into
an interlude or the outro climbs up to +6 dB over its last ten seconds
(capped so its loudest three seconds never pass the cue it hands over to:
the interlude's -27, the outro's -26), so the music arrives at the
transition instead of being cut off under it. The bed before the entrance
does not rise: it stops. The theme is heard for itself; the sign-on lands on
its downbeat. The interlude is heard for itself too, at -27.

| | Standard | Check |
|---|---|---|
| Dialogue | -20 LUFS integrated, per line | the voice chain |
| Bed under speech | -31 LUFS in the voice's gaps (rev 1 -32, rev 2 -28 overpowered); levelled on the gaps when they total 4 s | `level_bed`, `bed-level` |
| The rise | +6 dB over the last 10 s into an interlude or the outro, eased; capped at the level of the cue it hands over to (the interlude's -27, the featured -26); never into the entrance | `rise_into`, `bed_ending` |
| The stop | the bed the entrance follows ends on a hit 2.6 s before its end, within 3 dB of its loudest moment, 5 dB down 1.5 s later, at the floor by the end; then 1.6 s of floor with no music and no voice before the entrance | `render_bed(ending="stop")`, `bed_ending`, `score_rev5`, `timeline_rev5` |
| Duck | -10 dB under voice, a 1.0 s eased pre-roll at full depth on the onset, held across gaps under 1.2 s, 0.6 s release; never over 2 dB in any 100 ms. The desk's 2.4 s breaths are the one place on the desk it comes fully up (`desk_breath`; the 0.9 s gaps keep it down) | `duck_envelope`, `duck-slope`, `timeline_rev5c` |
| Featured (theme, entrance, outro) | loudest 3 s window at -26 LUFS, never louder | `level_featured`, `featured-level` |
| Interlude (rev 5c) | 8.6 s, three bars; loudest 3 s window at -27 LUFS (`INTERLUDE_LUFS`), never louder, and integrated within 6 dB of it (never silent); the next anchor speaks 6.4 s in; two in one episode share no melody, chord pair or voice, chroma cosine under 0.9; it arrives on its downbeat (its first second within 3 dB of its loudest moment) | `level_interlude`, `interlude-level`, `interlude-silent`, `interlude_plan`, `score_rev5c`, `timeline_rev5c` |
| Calm (rev 5c), every cue | at most 1.0 clock onsets a second (short, bright events in 2-6 kHz) for a bed or an interlude, 1.4 for a featured cue; at most 0.6 % of the energy over 100 Hz above 3 kHz for a bed, 1.5 % for an interlude, 2 % for a featured cue. Planted: rev 5's tick train (caught on both), bright open hats on two off-beats (caught on the glare alone) | `clock_density`, `glare_share`, `calm-clock`, `calm-glare`, `score_rev5c` |
| The desk's breath (rev 5c) | the desk bed carries one accent 0.6 s after every second item's last word; the ostinato rests through it and a two-note bell tag lands; the same seed with and without its breaths differs only there; an accent after the stop's hit is not played | `render_bed(accents=...)`, `_bell_tag`, `score_rev5c`, `timeline_rev5c` |
| The entrance | 11.4 s; swells from silence (first second 6 dB under its loudest 400 ms); under half the theme's clock onsets; third-octave cosine to the theme at most 0.9 (0.85 before rev 5c: the calm theme shares the entrance's warmth, so the cosine sits near 0.84 and the clock, the swell and the harmony carry the distinction), to either interlude at most 0.92; the anchor speaks after the hook's last note has landed | `score_rev5` |
| The Opinion's bed | under 60 % of the news beds' clock onsets a second (and the news beds carry at least 0.4, so the test is never vacuous); its chroma cosine to the news beds' centroid at least 0.03 under theirs; its progressions never hold the tonic chord | `clock_density`, `chroma_profile`, `score_rev5` |
| Band shape (beds) | bass under 130 Hz kept (24 dB/oct low-pass; 100 Hz before rev 5, moved so a bass note keeps its octave) + everything over 400 Hz (24 dB/oct high-pass), -3 dB shelf at 5 kHz; at most 10 % of the energy over 100 Hz in 150-400 Hz; at most 2 % above 5 kHz; at least 75 % of a bed's energy in 40-120 Hz | `shape_bed`, `bed-low-end`, `music-treble`, `score_rev5` |
| Breathing | a bed's 100 ms level spread (p90 - p10) at least 6 dB | `bed-breathing` |
| Repetition | no 4 s stretch heard near-identically three times in a row (chroma 0.97, third-octave spectrum 0.95, rhythm r 0.90) | `score-repetition` |
| Fades | an entry from silence 1.5 s or more, an exit as long (a stopped bed's exit is its ring) | the renderers |
| Phone check | the mix as a small speaker plays it: inside spoken windows (within 10 dB of the line's mean), the voice over the music in 150 Hz to 4 kHz by at least 12 dB; where a window fails, the music dips by the shortfall in THAT window only, eased over 0.6 s, so the bed keeps its level everywhere else; only if that is not enough does the whole bus come down | `phone_check`, `phone_fix` |
| Master | -16 LUFS integrated, -1.5 dBTP, linear loudnorm with the limiter anchored | `loudnorm_two_pass` |

A bed that fails breathing, low-end or repetition is drawn once more from a
second seed; the better render ships and the finding is logged with the
cue (`[onair][score]`). Against the film's A29 block the radio is louder by
design where the CEO asked for it (a bed at -28 against -32, a 10 dB duck
against 9 with a 0.6 s release against 0.25) and no laxer anywhere else.

Where the music goes is in the running order above: beds enter under the
framing, leave after the third answer (the facts get dense; "silent when it
deserves"), visit once in the middle of a long conversation, and return for
the coverage, rising into the interlude; the interlude is heard in the
clear for two bars and the next anchor starts over its release while the
next bed fades in under it; the desk bed runs throughout, surfaces in the
breaths after items two, four and six, and stops; the Opinion's bed enters
under A's introduction, never before it; while a bed plays, the gap between
a handover is 1.7 s instead of 1.0, so the music gets a breath. A studio
floor at -70 dBFS sits under everything
so a silence is never digital zero (it is all that plays in the 1.6 s before
the entrance); the -57 dBFS room tone of rev 1 read as noise and is gone.

## Operating it

- Daily: step 7d of `pipeline/main.py`. `[onair:world]` lines carry the
  script's words and label, the voice chain's gains, the timeline, every
  score cue with its gain and findings, the phone margin, loudness and
  chapters.
- Regenerate today's show without the pipeline: `refresh-brief.yml` (mode
  `radio`), or offline:
  `python pipeline/refresh_brief.py --radio-only --script-file tests/fixtures/onair_show_2026-11-07.txt --render-dir /tmp/onair`
  renders a written script to a folder with no Gemini and no database;
  without `--render-dir` it renders to the site and the DB. `--no-opinion`
  leaves the Opinion out; `--revoice` re-renders the script the current brief
  carries.
- `VOID_ONAIR_FORMAT=rundown` restores the 2026-09-18 bulletin;
  `VOID_ONAIR_FORMAT=legacy` (or `VOID_RADIO_FORMAT=0`) the edge-tts path.
- Gemini budget: one flash request per day, plus one on a repair.

## Ear-test checklist (CEO)

The cold open lands before any music. The sign-on starts over the theme's
release, never under its first bars. The bed is under the framing and the
first two answers, gone for the third, back for the coverage; it breathes
between exchanges. Both voices within the first sixty seconds; the questions
sound like questions. No names, no thanks, no reactions. The interlude is
heard for itself: a calm groove and a tune, a breath between the stories
and not a jingle, and the next voice arrives over its release while the
bed comes in under it; the second interlude is not the first. The desk
moves, and after every second item it breathes: the bed comes up and a bell
answers before the next item. Nothing in the score is sharp: no tick, no
click, no bright hit; the beat is felt, not heard as a clock. The news bed stops and the
show holds its breath; the entrance is heard as a new section before a word
of it; "This is Void Opinion." and the same anchor reads the argument over a
bed that is the show's but not the news's. The outro resolves to
the low D and falls to silence under the promo. No treble on the music; the
sub never muddies a word on a phone. Chapters show in the player and the
podcast app.

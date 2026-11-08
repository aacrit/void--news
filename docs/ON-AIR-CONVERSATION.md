# On Air: the conversation

Last updated: 2026-11-07 (rev 3, after the CEO's second ear test: the score
composed from scratch in `onair_music.py`, stereo, lighter under the voice
and rising into every transition. Rev 2 the same day: three anchors, the
Opinion as a conversation, a studio floor. Rev 1 replaced the 2026-09-18
bulletin as the daily programme; `docs/ON-AIR-RADIO.md` stays as the
bulletin's record and `VOID_ONAIR_FORMAT=rundown` restores it)

On Air is the daily programme of Void News: eight to eleven minutes, in the
manner of a serious daily news podcast. Three anchors. Two of them talk the
day's lead through, one asking and one answering; they change places for the
second story; the rest of the desk goes quickly; the third makes the day's
Opinion as an argument drawn out by the anchor's questions, and speaks
nowhere else; a close. It is generated once a day by the
pipeline (step 7d) and served as one MP3 with chapters.

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
TITLE       A: "From Void News, this is On Air. It's <day>."  A: today, in one or two sentences
                                                                  [bed: lead, from under the framing]
LEAD        A asks, B answers; five to nine exchanges, 380-580 words, the last exchange is the coverage
                                                                  [bed out after the second answer;
                                                                   one visit in the middle of a long
                                                                   conversation; back for the coverage]
page-turn   3.6 s: a riser, one downbeat, the hook's first three notes; never louder than the bed
            it leads into, which has risen +6 dB over its last 10 s to meet it
SECOND      B asks (one clause of bridge first), A answers; three to six exchanges, 230-400 words
                                                                  [bed: second, the same shape]
page-turn
DESK        A: "The rest of the desk."  ranks 3-8, one or two sentences each, alternating
                                                                  [bed: desk, the pulse, throughout]
entrance    6.8 s, featured: i to iv, a dotted pulse, the hook inverted and left on the dominant
            (a question); A's opening starts 1.6 s before it ends
OPINION     A: "Now, the Opinion. Through a <lens> lens today. <question>"  C argues, A draws it out;
            two to five exchanges                                 [bed: opinion under the first and the last exchange]
CLOSE       A: "That's On Air from Void News. <one fact to carry> Every source, every story, at Void News."
outro       15.0 s, featured: the cycle in full, a riser, the landing on D major (the lift), the pad
            falling to silence; the house promo rides it (unchanged)
```

Chapters: `Today` (0 s, kind `headlines`, covers the cold open and the title),
one `story` chapter per conversation (rank, cluster id, permalink when
archived; it starts at the page-turn), `The desk` (kind `briefs`), `Opinion`
(kind `opinion`, starts at the entrance music; `opinion_start_seconds` keeps
that meaning), `Also from Void` (the promo). `news_start_seconds` is where
the lead's first question begins.

**The Opinion is spoken only when it was written for this edition.** A
carried-forward opinion belongs to another day's stories, so the show ships
without the segment (two voices, no entrance, no Opinion chapter) rather than
read it as today's. When it is spoken, it is the brief's written opinion
(`opinion_text`) rendered as a conversation: C's lines are read against that
text by the grounding pass, so the show adds no claim the Opinion did not
make; A's questions draw the argument out and never argue back. The first
line is fixed: `Now, the Opinion. Through a pragmatic lens today.` (the lens
from `opinion_lean`), then the headline as a question (C-14).

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
| C-07 | The shape: the asker opens, asker and answerer alternate, the asker's lines under the cap and at least half of them questions, answers inside their budget and never questions; five to ten exchanges in LEAD, three to seven in SECOND, two to five in OPINION (A asks, C answers); the cold open is one A line and a fact | fail |
| C-08 | The desk opens on "The rest of the desk.", five to seven items, each at most 34 words, a fact not a question, never more items than stories | fail |
| C-09 | Over the news segments, each of A and B carries 35-65 % of the words | fail |
| C-10 | Sentences under twenty-four words | warn |
| C-11 | Grounded attribution (the radio's R-14): an attributed clause keeps 0.6 of the story's words for that speaker | fail |
| C-12 | No unattributed statement of law (R-15) | fail |
| C-13 | SAY respellings are lowercase syllables | warn |
| C-14 | The Opinion opens on `Now, the Opinion.` and names its lens | fail |
| C-00 | C speaks only in OPINION, B never there; an OPINION segment only on a day with a written opinion, and always on such a day | fail |
| C-15 | A chapter title is at most seven words, no digits | warn |

Then the grounding pass (`ground_show`, `editorial/derived_grounding`): every
line is read against its own story (LEAD and COLD against rank 1, SECOND
against rank 2, each desk item against its rank, C's lines against the
Opinion text, the framing and the close against the day), and a sentence the
story does not carry is cut. An answer cut whole takes the asker's line that
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
this chain). Casting, 2026-11-07, overridable with `VOID_KOKORO_VOICE_A/B/C`:

| Role | Voice | Why |
|---|---|---|
| A, the anchor | `af_heart` | the roster's A-grade voice goes to the voice heard most |
| B, the desk | `af_bella` | the A- grade; same register as heart, so the two are panned 14 % apart |
| C, the Opinion | `bf_emma` | the best British voice (B-), and it reads nothing else: the accent makes the firewall audible the moment it starts |

All three female (CEO, 2026-11-07, third ear test): Kokoro's male voices
were trained on minutes where heart and bella had hours, and it shows; the
men read as synthetic however they are cast (`am_michael`, then `am_fenrir`,
were heard and retired). The audition pack of every voice, slated, is the
record. A male desk returns when a model that can do one is in the chain.

One house pace, 0.95, on all three (CEO 2026-09-19); no voice is stretched.

**The voice chain** (`voice_chain`, the film studio's A13/A38 applied per
line, in numpy at 48 kHz): trim the silence (60 ms kept), a light spectral
gate (each bin's 15th-percentile magnitude is its noise profile; a bin under
2.5 times it is lowered 14 dB, the gain smoothed over five frames; speech is
untouched, the residue between words goes down), level the line to -20 LUFS
integrated, the house warmth (+2.5 dB bell at 200 Hz, Q 1.2; -2.5 dB
high shelf with its half-gain point at 6 kHz, zero-phase), re-level, and a
soft knee over -4 dBFS that touches only a line whose crest would reach the
ceiling. Then a constant-power pan: A 7 % left, B 7 % right, C centred. The
old ffmpeg chain (80 Hz high-pass, +2.5 dB at 4 kHz, de-esser, 3:1) brightened
the voice; this does the opposite, on the founder's note that the synthetic
voices had too much treble and wanted bass.

## The score

Composed from scratch for rev 3 (`onair_music.py`), after the CEO heard rev 2
and did not like the tunes. It is written, not generated: a key, a tempo, a
chord cycle, a hook, an ostinato, patches, an arrangement per cue. The day's
seed chooses only the chord cycle per segment and which bars carry which
layers, so the bed moves every day and the hook is the same every day.

**The writing.** D minor at 84 beats a minute. The cycle is i VI III VII
(Dm Bb F C), the cinematic cadence, with alternates per segment (i VI iv V;
the Opinion on i iv VI V, left unresolved). The hook is two bars on electric
piano that fall to the tonic: D5 C5 A4 F4, G4 F4 D4; inverted (rising, left
on the dominant) for the Opinion's entrance. Under it an eighth-note
ostinato of chord tones in the fourth and fifth octaves, a pulse bass on the
chord root in the sub (every bass note under 100 Hz, so the band shape keeps
it whole), and a pad voiced from the third octave up. The outro lands on D
major.

**The patches**, all synthesised: `ep` is a two-operator FM electric piano
(a 1:1 modulator whose index falls with the note, a 14:1 modulator for the
30 ms attack, a 3 kHz lowpass, a 1.4 s release) through a dotted-eighth
ping-pong delay; `pad` is six detuned saws, three a side, through a 24 dB/oct
lowpass that opens from 400 to 1100 Hz over the attack, breathing slowly;
`bass` is a sub sine under a plucked saw whose cutoff falls 320 to 110 Hz;
`kick` is a 150 to 45 Hz sweep with a 4 ms click so a phone hears it; `tick`
and `rim` are the clock, in 2.5 to 5 kHz and at 760 Hz; `riser` is noise
rising into a downbeat; `impact` is the downbeat it lands on. Pads and bass
pump 3 to 5 dB on every kick (`sidechain`). Two decorrelated rooms, one a
side (`reverb`). Stereo throughout: keys alternate left and right by note,
the pad is wide, kick and bass centred.

**The drums.** Half-time under the conversations (kick on one and three,
rims on two and four, a tick on every off-beat), four on the floor on the
desk with an open tick on the last off-beat, a dotted figure under the
Opinion, a bar dropped now and then so the pulse breathes. Off-beats swing
(56 %), every hit and note carries a few milliseconds of human jitter and a
little velocity variance, so no two bars land alike.

**The arc** (`_arc`, CEO: "extremely dynamic and natural"). A bed enters on
pad and bass alone; the pulse arrives in the second bar and builds across
the eight-bar phrase; the pad swells across the phrase; a dip and a tick
fill come before each new phrase; the ostinato and the hook come and go by
the seed. A bed ends one of two ways: `out` (the drums leave two bars early
and the keys sit back: the conversation takes over) or `rise` (a fill and
everything leaning in, for the page-turn, the entrance or the outro it hands
over to; the producer picks the ending from the timeline). The desk never
thins: momentum.

**Where it sits.** Lighter than rev 2 (CEO: it overpowered): -31 LUFS in the
voice's gaps, 10 dB down under the voice, and it RISES: a bed that leads into
a page-turn, the entrance or the outro climbs up to +6 dB over its last ten
seconds (capped so its loudest three seconds never pass the featured cue it
hands over to), so the music arrives at the transition instead of being cut
off under it. The theme is heard for itself; the sign-on lands on its
downbeat.

| | Standard | Check |
|---|---|---|
| Dialogue | -20 LUFS integrated, per line | the voice chain |
| Bed under speech | -31 LUFS in the voice's gaps (rev 1 -32, rev 2 -28 overpowered); levelled on the gaps when they total 4 s | `level_bed`, `bed-level` |
| The rise | +6 dB over the last 10 s into a page-turn, the entrance or the outro, eased; capped at the featured level | `rise_into` |
| Duck | -10 dB under voice, a 1.0 s eased pre-roll at full depth on the onset, held across gaps under 1.2 s, 0.6 s release; never over 2 dB in any 100 ms | `duck_envelope`, `duck-slope` |
| Featured (theme, entrance, outro) | loudest 3 s window at -26 LUFS, never louder | `level_featured`, `featured-level` |
| Page-turn | never louder than the bed it leads into (+0.5 dB on the loudest 400 ms) | `level_transition`, `transition-ceiling` |
| Band shape (beds) | sub-bass under 100 Hz kept (24 dB/oct low-pass) + everything over 400 Hz (24 dB/oct high-pass), -3 dB shelf at 5 kHz; at most 10 % of the energy over 100 Hz in 150-400 Hz; at most 2 % above 5 kHz | `shape_bed`, `bed-low-end`, `music-treble` |
| Breathing | a bed's 100 ms level spread (p90 - p10) at least 6 dB | `bed-breathing` |
| Repetition | no 4 s stretch heard near-identically three times in a row (chroma 0.97, third-octave spectrum 0.95, rhythm r 0.90) | `score-repetition` |
| Fades | an entry from silence 1.5 s or more, an exit as long | the renderers |
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
the coverage, rising into the page-turn; while a bed plays, the gap between
an answer and the next question is 1.4 s instead of 0.55, so the music gets
a breath. A studio floor at -70 dBFS sits under everything so a silence is
never digital zero; the -57 dBFS room tone of rev 1 read as noise and is gone.

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
sound like questions. No names, no thanks, no reactions. The page-turn reads
as a page turned, not a jingle. The desk moves. The entrance announces the
Opinion with no spoken throw; a third voice reads it. The outro resolves to
the low D and falls to silence under the promo. No treble on the music; the
sub never muddies a word on a phone. Chapters show in the player and the
podcast app.

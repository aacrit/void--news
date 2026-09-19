# History: the audio edition

Status: PLAN, 2026-09-19. Nothing here is built yet.

Every one of the 78 History events becomes an 8-12 minute produced audio piece:
written for the ear, cast by the event's own mood, scored per scene, and
mastered to the same standard as On Air.

This is a ONE-TIME build. It does not run on a cron and it is not a pipeline
stage. The scripts are authored in-session and committed as data; the renderer
reads them. That is not a shortcut, it is the only workable design (see
"Why the scripts are not generated").

## The reference

The CEO named seven: NPR, NYT, Conflicted, Ken Burns, MKBHD, Veritasium,
Vsauce, plus "Screenplay". Averaged together these produce mush, because they
disagree: Vsauce digresses, MKBHD does not; Ken Burns is solemn, MKBHD is
breezy. So each one is assigned a STRUCTURAL ROLE and is allowed to own that
role and nothing else.

| reference | contribution | where it is allowed |
|---|---|---|
| Veritasium | the misconception hook: you think you know this; you do not | COLD OPEN only |
| Screenplay | arrive late, leave early. Scene, not summary | every SCENE |
| Ken Burns | present tense, accumulative particulars, and PRIMARY SOURCES READ ALOUD | the spine |
| MKBHD | crisp direct address: "here is what that actually meant" | the ASIDE after a scene |
| Conflicted | moral seriousness without solemnity; the wry, human aside | register, throughout |
| Vsauce | the zoom-out that reframes the whole thing | THE TURN, once, late |
| NPR / NYT | restraint, attribution before claim, scoring | sound design + CLOSE |

The one that matters mechanically is Ken Burns: **a different voice reads the
documents.** That is a dramatic device, not a style coat, and it is the reason
the format is two voices rather than one.

## The format

Derived from the data that actually exists in every `data/history/events/*.yaml`
(verified across all 78: 5 perspectives each, 3-6 primary source excerpts each,
none missing, median 3,181 words of source prose against the ~1,450 a ten-minute
episode needs — so every script is SELECTION, never padding).

```
theme (era motif)
COLD OPEN    N   the misconception, from `subtitle` + `summary`. 2-4 sentences, no names yet
TITLE        N   "<title>. <date_display>."                                  [ident]
SCENE 1      N   arrive late: one moment, one place, one person. From key_figures + summary
DOCUMENT     D   a primary_source_excerpt, attribution spoken by N BEFORE the read
ASIDE        N   what that meant. Direct, short, MKBHD register
SCENE 2-4    N   the event proceeds. Each scene ends on a fact, not a conclusion
DOCUMENT     D   (2-4 per episode, always attributed first)
THE TURN     N   the perspectives: same event, five accounts, and what each OMITS
CLOSE        N   from legacy_points. Ends on a particular, never on a moral
outro (fading to silence)
```

**Every side gets its own case. This is the moat, and it is enforced.**

The first draft of the Partition script got this wrong in a way worth
recording, because it is the failure this format will keep drifting toward.
It summarised all five perspectives in about 280 words and characterised each
one BY WHAT IT OMITS. That is a debunking format wearing a balance costume:
every account is introduced only to be undercut, and the strongest fact in the
Pakistani case (the Muslim League winning 446 of 495 Muslim seats in 1946) was
left out entirely while the account was still called incomplete.

So a `PERSPECTIVE` segment now gives each account its own hearing: its argument
in its own terms, its strongest fact, and its own witness quoted by the
document voice. Only after all five have spoken does a closing TURN name what
each leaves out, and it names one for every side including the most recent and
most sympathetic.

`H-09` makes this structural rather than editorial: the event data names the
sides, so an episode that quietly drops one does not render. The gate is
verified against a script with the Pakistani account cut out.

An episode that ends "here are five accounts, each true, each with a hole, and
the holes are not random" is a history programme nobody else is making. An
episode that ends "here is what everyone gets wrong" is one that many people
make badly.

**Attribution before the claim**, exactly as On Air does it: the narrator says
who wrote it, where and when, and THEN the document voice reads. The listener
always knows whose words they are hearing before they hear them.

## Casting: 5-6 voices, chosen by the data

Every casting input already exists as a structured field, so the choice is
DETERMINISTIC and testable rather than a per-episode judgement: `severity`
(catastrophic 49 / critical 15 / major 14), `category` (9 values), `era`
(6 values), `region`.

The shortlist and the mapping are finalised after the ear test (a 10-voice
audition on a Ken Burns-register passage is rendered; grades from hexgrad's
table are a training-data measure, not a naturalness score, so they inform but
do not decide). The shape:

| role | used for | selection |
|---|---|---|
| Narrator | the whole episode | cast per event from `severity` + `category` |
| Document | primary sources and perspective witnesses ONLY | fixed per narrator, chosen to contrast (sex, register, accent) |

The document voice is a READER OF RECORD, not an impersonator. It does not
change per speaker and it is not accent-matched to the event's region: casting
an Indian voice for Partition and a Russian one for Chernobyl is a short road
to caricature, and one voice would still be reading Nehru, Gandhi and Jinnah
regardless. Attribution before every read is what removes the ambiguity, so
the voice never has to act.

Constraints the mapping must satisfy:
- A narrator and its document voice must never be confusable. The voice change
  is load-bearing: it is what tells the listener "these are real words".
- No voice is stretched. Pace is a casting decision (the On Air rule): a voice
  whose natural rate is wrong for a grave episode is not slowed, it is not cast.
- Every voice must hold 10 minutes. Auditions are judged on a full paragraph,
  not a line, because thinner-trained voices fall apart over distance.

## Sound

The same principles as On Air, which are now proven: one motif family, music
with an ARC per scene (enter, hold, leave), every fade-out landing UNDER a
sentence, beds darker as well as quieter under speech.

What differs: History gets **era motifs**. One family, six variations selected
by the `era` field, so a classical episode and a contemporary one are audibly
the same programme in different light. All synthesised in-repo by
`generate_assets`, no licensed material, per the originality rule.

## Why the scripts are not generated

`gemini-2.5-flash` is capped at **20 requests per day** on the free tier. 78
premium scripts is four days of budget, and flash-lite is not good enough for
this writing. More importantly, a generated script would need the same
validator-and-retry apparatus On Air needs, to police a model that cannot see
the whole catalogue and cannot keep 78 episodes from converging on one shape.

So the scripts are authored in-session and committed as
`data/history/scripts/<slug>.txt` in a marked-up format the renderer parses
(the same discipline as the radio rundown: segment markers, speaker prefixes,
`## SAY` respellings). This costs zero Gemini budget, produces better prose,
and makes every script reviewable and re-renderable forever.

## Pipeline

| piece | reuse or build |
|---|---|
| Synthesis, voice buses, ffmpeg chain, loudnorm, encode, ID3 chapters, sidecars | REUSE from `radio_producer` (format-agnostic) |
| `apply_duck`, `_loop_to`, `weave_end`, the arc logic | REUSE |
| `build_timeline` / `render_music_bus` | PARALLEL implementation: they hard-code the radio segment kinds |
| Script parser + validators | NEW, modelled on `radio_script_generator` |
| Era motifs | NEW in `generate_assets` |
| Storage | **Cloudflare R2** (CEO decision) |

**R2, not git.** 78 episodes at On Air quality is ~750 MB against a repo whose
entire history is 167 MB. Git binaries cannot be un-committed cleanly, so this
is the one decision in the build that is expensive to reverse. R2 was already
the flagged follow-up in CLAUDE.md for exactly this reason, and it lets the
catalogue keep full 128k stereo instead of being degraded to fit a repo.

## Staging

Each stage answers a different question and must be signed off before the next.

| stage | count | the question it answers |
|---|---|---|
| 1 | Partition of India | Does the format work at all, end to end? |
| 2 | 5 episodes | Does mood-casting hold across registers, and do five scripts sound like five stories or one formula? |
| 3 | 10 episodes | Does the pipeline hold: render throughput, R2 upload, player, chapters? |
| 4 | 62 remaining | Execution. |

Stage 2's question is the one most likely to fail, and it cannot be answered by
stage 1: a single good episode proves nothing about whether the format has
enough range. The five are deliberately chosen to span severity, era and
category (e.g. a genocide, a cultural moment, an ancient empire, a disaster, a
revolution).

**Throughput is the binding constraint, not Gemini.** 78 x 10 min is ~13 hours
of audio; at the measured Kokoro rtf (~1.1 with two workers) that is ~14 hours
of CPU. Options, to be decided at stage 3 when the real per-episode cost is
known: an overnight local run, or a GitHub Actions matrix rendering in parallel
shards. Stage 3 exists to measure this.

## Verification

- Script gates (`pipeline/history/script_format.py`), each verified against a
  planted defect rather than merely written:
  - `H-01` every quote exists in the event's own `primary_source_excerpts` or
    `notable_quotes`, by word overlap so trimming for the ear is allowed and
    inventing is not. A fabricated quotation is the one unrecoverable failure
    in a history programme.
  - `H-04` the narration NAMES THE SPEAKER before the voice reads. Checking
    that some narration came first is not enough: a perspective argues before
    it quotes, so that weaker test passes even when nobody is named. The
    speaker is looked up from the data by matching the quote, which also
    catches crediting the wrong person.
  - `H-09` every perspective in the data is given its own case.
  - `H-02` the document voice speaks only where a quote belongs.
  - `H-06` the episode carries a TURN. `H-07` length inside 8-15 minutes.
- Render gates: reuse the On Air assertions (gaps, arcs, fades landing under
  speech, loudness within tolerance, TP and LRA, chapters exact).
- Served: episodes reachable from R2, chapters render, player resumes.
- Ear test per stage, by the CEO, before the next stage starts.
